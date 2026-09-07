"""The Efficient Frontier of AI.

Computes the Pareto-optimal frontier of AI models balancing:
1. Quality Score (Eval pass-rate, reasoning accuracy: 0.0 - 1.0)
2. Cost (Blended USD per 1M tokens)
3. Latency (Typical end-to-end response time in ms)

Implements the spec.md requirement:
"The dashboard doesn't just show cost; it shows the Efficient Frontier of AI:
- Model A: $10/M tokens, 99% Quality
- Model B: $2/M tokens, 96% Quality
- Model C: $0.50/M tokens, 82% Quality"
"""

from __future__ import annotations

from typing import Dict, List, Optional

from pydantic import BaseModel, Field


class ModelProfile(BaseModel):
    """Specification and empirical benchmark profile of an AI model."""

    model_id: str
    display_name: str
    provider: str
    input_cost_per_1m: float
    output_cost_per_1m: float
    blended_cost_per_1m: float
    typical_latency_ms: float
    quality_score: float = Field(ge=0.0, le=1.0)
    context_window: int = 128000
    is_pareto_optimal: bool = False
    notes: str = ""


# Default catalog of contemporary frontier, enterprise, fast, and local models
STANDARD_MODEL_CATALOG: Dict[str, ModelProfile] = {
    "claude-3-5-sonnet": ModelProfile(
        model_id="claude-3-5-sonnet",
        display_name="Claude 3.5 Sonnet",
        provider="anthropic",
        input_cost_per_1m=3.00,
        output_cost_per_1m=15.00,
        blended_cost_per_1m=6.00,
        typical_latency_ms=420.0,
        quality_score=0.965,
        context_window=200000,
        notes="Frontier reasoning, coding, and tool-use leader",
    ),
    "gpt-4o": ModelProfile(
        model_id="gpt-4o",
        display_name="GPT-4o",
        provider="openai",
        input_cost_per_1m=2.50,
        output_cost_per_1m=10.00,
        blended_cost_per_1m=4.375,
        typical_latency_ms=390.0,
        quality_score=0.955,
        context_window=128000,
        notes="General-purpose high-performance multimodal model",
    ),
    "gemini-1-5-pro": ModelProfile(
        model_id="gemini-1-5-pro",
        display_name="Gemini 1.5 Pro",
        provider="google",
        input_cost_per_1m=1.25,
        output_cost_per_1m=5.00,
        blended_cost_per_1m=2.1875,
        typical_latency_ms=450.0,
        quality_score=0.940,
        context_window=2000000,
        notes="Extremely large 2M context window with strong reasoning",
    ),
    "claude-3-5-haiku": ModelProfile(
        model_id="claude-3-5-haiku",
        display_name="Claude 3.5 Haiku",
        provider="anthropic",
        input_cost_per_1m=0.80,
        output_cost_per_1m=4.00,
        blended_cost_per_1m=1.60,
        typical_latency_ms=210.0,
        quality_score=0.905,
        context_window=200000,
        notes="High speed and quality at balanced cost",
    ),
    "gpt-4o-mini": ModelProfile(
        model_id="gpt-4o-mini",
        display_name="GPT-4o mini",
        provider="openai",
        input_cost_per_1m=0.15,
        output_cost_per_1m=0.60,
        blended_cost_per_1m=0.2625,
        typical_latency_ms=180.0,
        quality_score=0.885,
        context_window=128000,
        notes="Industry benchmark for cost-efficient intelligence",
    ),
    "gemini-1-5-flash": ModelProfile(
        model_id="gemini-1-5-flash",
        display_name="Gemini 1.5 Flash",
        provider="google",
        input_cost_per_1m=0.075,
        output_cost_per_1m=0.30,
        blended_cost_per_1m=0.13125,
        typical_latency_ms=140.0,
        quality_score=0.865,
        context_window=1000000,
        notes="Ultra-low latency and budget multi-modal processor",
    ),
    "llama-3-3-70b": ModelProfile(
        model_id="llama-3-3-70b",
        display_name="Llama 3.3 70B (Groq/vLLM)",
        provider="meta/open",
        input_cost_per_1m=0.59,
        output_cost_per_1m=0.79,
        blended_cost_per_1m=0.64,
        typical_latency_ms=160.0,
        quality_score=0.910,
        context_window=128000,
        notes="Open-weights flagship rivaling proprietary models",
    ),
    "llama-3-1-8b": ModelProfile(
        model_id="llama-3-1-8b",
        display_name="Llama 3.1 8B (Local)",
        provider="local",
        input_cost_per_1m=0.05,
        output_cost_per_1m=0.05,
        blended_cost_per_1m=0.05,
        typical_latency_ms=85.0,
        quality_score=0.810,
        context_window=128000,
        notes="Zero token cost on private hardware, edge deployment",
    ),
}


def compute_pareto_frontier(profiles: List[ModelProfile]) -> List[ModelProfile]:
    """
    Computes the Pareto-optimal Efficient Frontier across (Quality, Cost, Latency).

    A model P is Pareto-optimal if there is no other model Q such that:
    - Q.quality >= P.quality
    - Q.cost <= P.cost
    - Q.latency <= P.latency
    with at least one strict inequality.
    """
    results: List[ModelProfile] = []

    for candidate in profiles:
        is_dominated = False
        for other in profiles:
            if other.model_id == candidate.model_id:
                continue

            # Check if 'other' strictly dominates 'candidate'
            other_is_not_worse = (
                other.quality_score >= candidate.quality_score
                and other.blended_cost_per_1m <= candidate.blended_cost_per_1m
                and other.typical_latency_ms <= candidate.typical_latency_ms
            )
            other_is_strictly_better = (
                other.quality_score > candidate.quality_score
                or other.blended_cost_per_1m < candidate.blended_cost_per_1m
                or other.typical_latency_ms < candidate.typical_latency_ms
            )

            if other_is_not_worse and other_is_strictly_better:
                is_dominated = True
                break

        copy_prof = candidate.model_copy()
        copy_prof.is_pareto_optimal = not is_dominated
        results.append(copy_prof)

    return results


def get_efficient_frontier() -> List[ModelProfile]:
    """Returns the standard catalog profiles with Pareto optimality tags computed."""
    return compute_pareto_frontier(list(STANDARD_MODEL_CATALOG.values()))


def find_optimal_model(
    min_quality: float = 0.85,
    max_latency_ms: Optional[float] = None,
    max_cost_per_1m: Optional[float] = None,
    priority: str = "cost",  # 'cost', 'quality', 'latency', 'balanced'
    candidates: Optional[List[ModelProfile]] = None,
) -> Optional[ModelProfile]:
    """
    Finds the optimal model matching SLA constraints using the Efficient Frontier.
    """
    if candidates is None:
        candidates = get_efficient_frontier()

    # Filter candidates meeting minimum SLA
    viable = [
        c
        for c in candidates
        if c.quality_score >= min_quality
        and (max_latency_ms is None or c.typical_latency_ms <= max_latency_ms)
        and (max_cost_per_1m is None or c.blended_cost_per_1m <= max_cost_per_1m)
    ]

    if not viable:
        # Fallback to closest matching quality
        return max(candidates, key=lambda c: c.quality_score)

    if priority == "cost":
        # Cheapest model meeting quality and latency SLA
        return min(viable, key=lambda c: c.blended_cost_per_1m)
    elif priority == "quality":
        # Highest quality model within cost and latency SLA
        return max(viable, key=lambda c: c.quality_score)
    elif priority == "latency":
        # Fastest model meeting quality and cost SLA
        return min(viable, key=lambda c: c.typical_latency_ms)
    else:  # 'balanced' -> maximizes (quality / cost)
        return max(
            viable,
            key=lambda c: (
                (c.quality_score**2)
                / (max(0.01, c.blended_cost_per_1m) * (c.typical_latency_ms / 100.0))
            ),
        )
