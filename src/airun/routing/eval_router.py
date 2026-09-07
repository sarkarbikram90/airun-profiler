"""Eval-Driven Routing Engine for AI Workloads.

Implements the specification from spec.md:
"The Solution: Eval-Driven Routing
airun cannot just be Datadog; it must integrate with LLMOps evaluation frameworks.
1. The Baseline: The customer defines a 'Quality Score' (e.g., 95% pass rate on an eval dataset).
2. The Shadow Test: airun continuously routes a small percentage of live traffic to cheaper/faster models in the background, grading the output against the eval harness.
3. The Optimization: Shows the Efficient Frontier of AI.
4. The Action: airun allows setting policy: 'Never drop below 95% quality for Tier 1 customers, but route Tier 2 free-tier users to Model B.'"
"""

from __future__ import annotations

import random
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field

from airun.routing.frontier import (
    ModelProfile,
    find_optimal_model,
    get_efficient_frontier,
)


class RoutingTier(str, Enum):
    """Customer / Workload criticality tiers."""

    TIER_1_CRITICAL = (
        "tier_1_critical"  # Mission-critical, legal, medical, security (Quality >= 0.95)
    )
    TIER_2_STANDARD = (
        "tier_2_standard"  # General production, conversational agents (Quality >= 0.88)
    )
    TIER_3_ECONOMY = (
        "tier_3_economy"  # Batch processing, internal tools, free-tier (Cost-optimized)
    )


class RouteDecision(BaseModel):
    """Routing policy execution outcome."""

    selected_model: str
    provider: str
    tier: RoutingTier
    min_quality_sla: float
    expected_quality: float
    expected_cost_per_1m: float
    expected_latency_ms: float
    is_shadow_test: bool = False
    rationale: str
    fallback_models: List[str] = Field(default_factory=list)


class RoutingPolicy(BaseModel):
    """Configurable routing rules for an application or tenant."""

    tier: RoutingTier = RoutingTier.TIER_2_STANDARD
    min_quality_threshold: Optional[float] = None
    max_latency_ms: Optional[float] = None
    max_cost_per_1m: Optional[float] = None
    shadow_testing_enabled: bool = True
    shadow_traffic_rate: float = 0.10  # 10% of calls evaluated on cheaper candidates
    candidate_pool: Optional[List[str]] = None


class EvalRouter:
    """Eval-Driven Model Router and Shadow Testing Orchestrator."""

    def __init__(self, catalog: Optional[List[ModelProfile]] = None):
        self._profiles = catalog or get_efficient_frontier()
        self._profile_map = {p.model_id: p for p in self._profiles}
        self._empirical_scores: Dict[str, List[float]] = {}
        self._shadow_test_history: List[Dict[str, Any]] = []

    def route(
        self, policy: Optional[RoutingPolicy] = None, task_id: Optional[str] = None
    ) -> RouteDecision:
        """
        Determines the optimal model for the incoming request based on tier policy
        and dynamically assigns shadow tests to explore cheaper Pareto options.
        """
        if policy is None:
            policy = RoutingPolicy()

        # Define minimum quality threshold based on tier
        if policy.min_quality_threshold is not None:
            min_q = policy.min_quality_threshold
        elif policy.tier == RoutingTier.TIER_1_CRITICAL:
            min_q = 0.95
        elif policy.tier == RoutingTier.TIER_2_STANDARD:
            min_q = 0.88
        else:
            min_q = 0.80

        # Primary optimal model selection
        primary_model = find_optimal_model(
            min_quality=min_q,
            max_latency_ms=policy.max_latency_ms,
            max_cost_per_1m=policy.max_cost_per_1m,
            priority="cost",  # Lowest cost satisfying quality SLA
            candidates=self._profiles,
        )

        if not primary_model:
            primary_model = self._profiles[0]

        # Check for shadow test exploration
        is_shadow = False
        routed_model = primary_model

        if policy.shadow_testing_enabled and random.random() < policy.shadow_traffic_rate:
            # Find a cheaper candidate model with promising quality to benchmark
            cheaper_candidates = [
                p
                for p in self._profiles
                if p.blended_cost_per_1m < primary_model.blended_cost_per_1m
                and p.quality_score >= min_q * 0.92  # within striking distance
                and p.model_id != primary_model.model_id
            ]
            if cheaper_candidates:
                routed_model = random.choice(cheaper_candidates)
                is_shadow = True

        # Build fallback model chain
        fallbacks = [
            p.model_id
            for p in sorted(self._profiles, key=lambda x: x.quality_score, reverse=True)
            if p.model_id != routed_model.model_id
        ][:3]

        rationale = (
            f"Shadow test candidate ({routed_model.model_id}) for baseline {primary_model.model_id}"
            if is_shadow
            else f"Optimal Pareto model for {policy.tier.value} with quality SLA >= {min_q:.2f}"
        )

        decision = RouteDecision(
            selected_model=routed_model.model_id,
            provider=routed_model.provider,
            tier=policy.tier,
            min_quality_sla=min_q,
            expected_quality=routed_model.quality_score,
            expected_cost_per_1m=routed_model.blended_cost_per_1m,
            expected_latency_ms=routed_model.typical_latency_ms,
            is_shadow_test=is_shadow,
            rationale=rationale,
            fallback_models=fallbacks,
        )

        return decision

    def record_eval_outcome(
        self,
        model_id: str,
        evaluated_quality: float,
        latency_ms: float,
        cost_usd: float,
        passed_sla: bool,
    ) -> None:
        """Records the ground-truth evaluation result of a model execution."""
        if model_id not in self._empirical_scores:
            self._empirical_scores[model_id] = []

        self._empirical_scores[model_id].append(evaluated_quality)

        self._shadow_test_history.append(
            {
                "model_id": model_id,
                "quality": evaluated_quality,
                "latency_ms": latency_ms,
                "cost_usd": cost_usd,
                "passed_sla": passed_sla,
            }
        )

        # Update running quality score profile dynamically
        if model_id in self._profile_map and len(self._empirical_scores[model_id]) >= 3:
            avg_q = sum(self._empirical_scores[model_id]) / len(self._empirical_scores[model_id])
            self._profile_map[model_id].quality_score = round(avg_q, 4)

    def get_shadow_insights(self) -> List[Dict[str, Any]]:
        """Summarize shadow testing observations across tested models."""
        insights = []
        for model_id, scores in self._empirical_scores.items():
            if not scores:
                continue
            avg_quality = sum(scores) / len(scores)
            profile = self._profile_map.get(model_id)
            insights.append(
                {
                    "model_id": model_id,
                    "provider": profile.provider if profile else "unknown",
                    "sample_count": len(scores),
                    "measured_quality": round(avg_quality, 4),
                    "blended_cost_1m": profile.blended_cost_per_1m if profile else 0.0,
                }
            )
        return sorted(insights, key=lambda x: x["measured_quality"], reverse=True)


# Global default router
_DEFAULT_ROUTER: Optional[EvalRouter] = None


def get_eval_router() -> EvalRouter:
    global _DEFAULT_ROUTER
    if _DEFAULT_ROUTER is None:
        _DEFAULT_ROUTER = EvalRouter()
    return _DEFAULT_ROUTER
