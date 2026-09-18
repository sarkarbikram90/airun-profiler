from datetime import datetime, timezone
from typing import Any, Dict

from airun.analysis.correlation import HardwareWasteDiagnosis
from airun.events.models import SpanStatus, TraceRecord, TraceSummary
from airun.resilience.breaker import CircuitState, get_resilience_manager
from airun.resilience.remediation_engine import (
    RemediationAction,
    RemediationEngine,
    RemediationRule,
)


def _make_sample_trace(trace_id: str = "tr_test_rem_1", quality_score: float = 0.95) -> TraceRecord:
    now_str = datetime.now(timezone.utc).isoformat()
    summary = TraceSummary(
        trace_id=trace_id,
        name="test_agent_run",
        outcome=SpanStatus.SUCCESS,
        start_time=now_str,
        end_time=now_str,
        total_duration_ms=250.0,
        total_tokens=1500,
        total_cost_usd=0.045,
        quality_score=quality_score,
    )
    return TraceRecord(
        trace_id=trace_id,
        created_at=now_str,
        spans=[],
        summary=summary,
    )


def test_remediation_financial_bleed_routing_shift():
    """Verify financial bleed triggers automatic Pareto-optimal routing shift."""
    trace = _make_sample_trace(trace_id="tr_bleed_1", quality_score=0.90)
    diagnosis = HardwareWasteDiagnosis(
        workload_name="training_loop",
        trace_id="tr_bleed_1",
        accelerator="H100-SXM-80GB",
        num_gpus=8,
        primary_bottleneck="DataLoader Stall",
        bottleneck_category="i_o_bottleneck",
        symptom="Low SM utilization",
        root_cause="Host CPU pre-processing bottleneck",
        remediation_action="Pin memory and increase num_workers",
        hourly_rate_per_gpu=3.50,
        hourly_bleed_usd=22.50,  # > default threshold 15.0
        weekly_bleed_usd=3780.0,
        monthly_bleed_usd=16200.0,
        avg_sm_util_pct=65.0,
        avg_power_watts=450.0,
    )

    engine = RemediationEngine()
    results = engine.evaluate_trace(trace, diagnosis)

    # excessive_financial_bleed_rule should have triggered ROUTING_SHIFT
    shift_results = [r for r in results if r.action == RemediationAction.ROUTING_SHIFT]
    assert len(shift_results) == 1
    res = shift_results[0]
    assert res.triggered is True
    assert "swapped_to_model" in res.details
    assert "Pareto-optimal" in res.action_taken


def test_remediation_quality_collapse_circuit_breaker():
    """Verify quality degradation autonomously trips provider circuit breaker."""
    trace = _make_sample_trace(trace_id="tr_quality_collapse", quality_score=0.45)
    resilience_mgr = get_resilience_manager()
    breaker = resilience_mgr.get_breaker("openai")
    breaker.state = CircuitState.CLOSED  # ensure closed initially

    engine = RemediationEngine()
    results = engine.evaluate_trace(trace)

    trip_results = [r for r in results if r.action == RemediationAction.CIRCUIT_BREAKER_TRIP]
    assert len(trip_results) == 1
    assert trip_results[0].triggered is True
    assert breaker.state == CircuitState.OPEN
    assert breaker.trip_count >= 1


def test_remediation_critical_bleed_webhook_dispatch():
    """Verify critical financial bleed fires webhook dispatch."""
    dispatched_payloads = []

    def mock_dispatcher(url: str, payload: Dict[str, Any]) -> bool:
        dispatched_payloads.append((url, payload))
        return True

    engine = RemediationEngine(webhook_dispatcher=mock_dispatcher)
    trace = _make_sample_trace(trace_id="tr_crit_bleed", quality_score=0.92)
    diagnosis = HardwareWasteDiagnosis(
        workload_name="bad_workload",
        trace_id="tr_crit_bleed",
        accelerator="H100-SXM-80GB",
        num_gpus=8,
        primary_bottleneck="Kernel Stall",
        bottleneck_category="compute_bottleneck",
        symptom="Severe bleed",
        root_cause="Infinite loop in custom CUDA kernel",
        remediation_action="Recompile with fast-math",
        hourly_rate_per_gpu=4.00,
        hourly_bleed_usd=55.0,  # > critical bleed threshold 50.0
        weekly_bleed_usd=9240.0,
        monthly_bleed_usd=39600.0,
        avg_sm_util_pct=15.0,  # < 40% SM starvation threshold
        avg_power_watts=200.0,
    )

    results = engine.evaluate_trace(trace, diagnosis)
    assert len(dispatched_payloads) == 1
    url, payload = dispatched_payloads[0]
    assert "alerts/critical-bleed" in url
    assert payload["event"] == "autonomous_remediation_triggered"
    assert payload["trace_id"] == "tr_crit_bleed"

    # Also sm_starvation should trigger LOG_AUDIT
    audit_results = [r for r in results if r.action == RemediationAction.LOG_AUDIT]
    assert len(audit_results) == 1
    assert audit_results[0].triggered is True


def test_remediation_healthy_trace_no_action():
    """Verify perfectly healthy traces trigger no remediation actions."""
    engine = RemediationEngine()
    trace = _make_sample_trace(trace_id="tr_healthy", quality_score=0.98)
    diagnosis = HardwareWasteDiagnosis(
        workload_name="healthy_workload",
        trace_id="tr_healthy",
        accelerator="H100-SXM-80GB",
        num_gpus=8,
        primary_bottleneck="None",
        bottleneck_category="optimal",
        symptom="Optimal",
        root_cause="None",
        remediation_action="None",
        hourly_rate_per_gpu=3.50,
        hourly_bleed_usd=1.20,
        weekly_bleed_usd=200.0,
        monthly_bleed_usd=864.0,
        avg_sm_util_pct=88.5,
        avg_power_watts=600.0,
    )

    results = engine.evaluate_trace(trace, diagnosis)
    assert len(results) == 0


def test_custom_rule_evaluation():
    """Verify custom RemediationRule configuration works as expected."""
    custom_rule = RemediationRule(
        name="strict_financial_guardrail",
        condition_type="financial_bleed_threshold",
        threshold=5.0,
        action=RemediationAction.LOG_AUDIT,
        target="audit_system",
    )
    engine = RemediationEngine(rules=[custom_rule])
    trace = _make_sample_trace()
    diagnosis = HardwareWasteDiagnosis(
        workload_name="job",
        trace_id="tr_cust",
        accelerator="A100",
        num_gpus=1,
        primary_bottleneck="None",
        bottleneck_category="optimal",
        symptom="None",
        root_cause="None",
        remediation_action="None",
        hourly_rate_per_gpu=2.0,
        hourly_bleed_usd=7.5,  # > 5.0
        weekly_bleed_usd=100.0,
        monthly_bleed_usd=400.0,
        avg_sm_util_pct=90.0,
        avg_power_watts=300.0,
    )
    results = engine.evaluate_trace(trace, diagnosis)
    assert len(results) == 1
    assert results[0].rule_name == "strict_financial_guardrail"
    assert results[0].metric_value == 7.5
