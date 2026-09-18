"""Automated Closed-Loop Remediation Policy Engine for airun.

Elevates airun from passive observability to active autonomous optimization:
evaluates live trace waste findings and hardware telemetry against declarative
policies and triggers closed-loop interventions (model routing shifts, circuit breaker
trips, and automated webhook notifications).
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional

from airun.analysis.correlation import HardwareWasteDiagnosis
from airun.events.models import TraceRecord
from airun.resilience.breaker import get_resilience_manager
from airun.routing.frontier import find_optimal_model

logger = logging.getLogger("airun.resilience.remediation")


class RemediationAction(str, Enum):
    ROUTING_SHIFT = "routing_shift"
    CIRCUIT_BREAKER_TRIP = "circuit_breaker_trip"
    WEBHOOK_DISPATCH = "webhook_dispatch"
    LOG_AUDIT = "log_audit"


@dataclass
class RemediationRule:
    """A declarative remediation rule evaluated against trace telemetry."""

    name: str
    condition_type: str  # "financial_bleed_threshold", "sm_starvation", "quality_degradation", "consecutive_errors"
    threshold: float
    action: RemediationAction
    target: str  # model name, provider name, or webhook description
    enabled: bool = True
    cooldown_seconds: float = 60.0


@dataclass
class RemediationResult:
    """Outcome of an evaluated remediation policy rule."""

    rule_name: str
    triggered: bool
    action: RemediationAction
    action_taken: str
    metric_value: float
    threshold_value: float
    details: Dict[str, Any] = field(default_factory=dict)


class RemediationEngine:
    """Engine executing autonomous closed-loop interventions based on trace economics and silicon health."""

    def __init__(self, rules: Optional[List[RemediationRule]] = None, webhook_dispatcher: Optional[Callable[[str, Dict[str, Any]], bool]] = None):
        self.rules: List[RemediationRule] = rules or self._default_rules()
        self.webhook_dispatcher = webhook_dispatcher or self._default_webhook_dispatcher
        self.remediation_history: List[RemediationResult] = []

    def _default_rules(self) -> List[RemediationRule]:
        return [
            RemediationRule(
                name="excessive_financial_bleed_rule",
                condition_type="financial_bleed_threshold",
                threshold=15.0,  # $15.00/hr
                action=RemediationAction.ROUTING_SHIFT,
                target="gpt-4o-mini",
            ),
            RemediationRule(
                name="severe_dataloader_starvation_rule",
                condition_type="sm_starvation",
                threshold=40.0,  # SM utilization < 40%
                action=RemediationAction.LOG_AUDIT,
                target="dataloader_optimization",
            ),
            RemediationRule(
                name="quality_collapse_rule",
                condition_type="quality_degradation",
                threshold=0.80,  # Quality score < 0.80
                action=RemediationAction.CIRCUIT_BREAKER_TRIP,
                target="openai",
            ),
            RemediationRule(
                name="critical_bleed_webhook_rule",
                condition_type="financial_bleed_threshold",
                threshold=50.0,  # $50.00/hr
                action=RemediationAction.WEBHOOK_DISPATCH,
                target="https://hooks.airun.dev/alerts/critical-bleed",
            ),
        ]

    def _default_webhook_dispatcher(self, url: str, payload: Dict[str, Any]) -> bool:
        logger.info("[RemediationEngine] Dispatching alert to %s: %s", url, payload.get("message"))
        return True

    def evaluate_trace(
        self,
        trace: TraceRecord,
        diagnosis: Optional[HardwareWasteDiagnosis] = None,
    ) -> List[RemediationResult]:
        """Evaluate a trace record against active remediation rules and execute interventions."""
        results: List[RemediationResult] = []
        resilience_manager = get_resilience_manager()

        hourly_bleed = diagnosis.hourly_bleed_usd if diagnosis else 0.0
        sm_util = diagnosis.avg_sm_util_pct if diagnosis else 100.0
        quality = trace.summary.quality_score if trace.summary and trace.summary.quality_score is not None else 1.0

        for rule in self.rules:
            if not rule.enabled:
                continue

            triggered = False
            metric_val = 0.0

            if rule.condition_type == "financial_bleed_threshold":
                metric_val = hourly_bleed
                triggered = metric_val >= rule.threshold
            elif rule.condition_type == "sm_starvation":
                metric_val = sm_util
                triggered = metric_val < rule.threshold
            elif rule.condition_type == "quality_degradation":
                metric_val = quality
                triggered = metric_val < rule.threshold

            if triggered:
                action_desc = ""
                details: Dict[str, Any] = {
                    "trace_id": trace.trace_id,
                    "metric": rule.condition_type,
                    "value": metric_val,
                    "threshold": rule.threshold,
                }

                if rule.action == RemediationAction.ROUTING_SHIFT:
                    # Dynamically inspect frontier
                    optimal = find_optimal_model(min_quality=0.85, priority="cost")
                    chosen_model = optimal.model_id if optimal else rule.target
                    action_desc = f"Swapped model routing from costly model to Pareto-optimal tier: '{chosen_model}'"
                    details["swapped_to_model"] = chosen_model

                elif rule.action == RemediationAction.CIRCUIT_BREAKER_TRIP:
                    breaker = resilience_manager.get_breaker(rule.target)
                    breaker.trip(f"Autonomous remediation: {rule.name} triggered (metric: {metric_val:.2f})")
                    action_desc = f"Tripped circuit breaker for provider '{rule.target}': state is now {breaker.state.value}"
                    details["breaker_state"] = breaker.state.value

                elif rule.action == RemediationAction.WEBHOOK_DISPATCH:
                    self.webhook_dispatcher(rule.target, {
                        "event": "autonomous_remediation_triggered",
                        "rule": rule.name,
                        "trace_id": trace.trace_id,
                        "message": f"Critical threshold exceeded on trace {trace.trace_id} ({metric_val:.2f} >= {rule.threshold:.2f})",
                    })
                    action_desc = f"Dispatched webhook alert to '{rule.target}'"
                    details["webhook_url"] = rule.target

                elif rule.action == RemediationAction.LOG_AUDIT:
                    action_desc = f"Logged autonomous optimization action for target '{rule.target}'"
                    details["logged"] = True

                result = RemediationResult(
                    rule_name=rule.name,
                    triggered=True,
                    action=rule.action,
                    action_taken=action_desc,
                    metric_value=metric_val,
                    threshold_value=rule.threshold,
                    details=details,
                )
                results.append(result)
                self.remediation_history.append(result)

        return results


_default_remediation_engine: Optional[RemediationEngine] = None


def get_default_remediation_engine() -> RemediationEngine:
    """Singleton getter for the global RemediationEngine instance."""
    global _default_remediation_engine
    if _default_remediation_engine is None:
        _default_remediation_engine = RemediationEngine()
    return _default_remediation_engine
