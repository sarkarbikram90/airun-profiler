"""Unit tests for AI Breaker Box, Semantic Mapping, and Disaster Recovery drills."""

from airun.resilience.breaker import (
    AIBreaker,
    BreakerConfig,
    CircuitState,
    ResilienceManager,
)
from airun.resilience.dr_drills import run_disaster_recovery_drill
from airun.resilience.semantic_mapper import (
    map_messages,
    map_parameters,
    map_tool_schema,
)


def test_breaker_circuit_state_transitions():
    """Verify circuit breaker transitions: CLOSED -> OPEN -> HALF_OPEN -> CLOSED."""
    config = BreakerConfig(
        failure_threshold=2, recovery_timeout_sec=0.05, half_open_success_needed=2
    )
    breaker = AIBreaker("openai", config)

    assert breaker.state == CircuitState.CLOSED
    assert breaker.can_execute() is True

    # 1 failure: stays closed
    breaker.record_failure("HTTP 500")
    assert breaker.state == CircuitState.CLOSED

    # 2 failures: trips to OPEN
    breaker.record_failure("HTTP 503")
    assert breaker.state == CircuitState.OPEN
    assert breaker.trip_count == 1
    assert breaker.can_execute() is False

    # Wait for recovery timeout
    import time

    time.sleep(0.06)

    # Now can_execute should transition to HALF_OPEN
    assert breaker.can_execute() is True
    assert breaker.state == CircuitState.HALF_OPEN

    # 2 successes in half_open restore to CLOSED
    breaker.record_success(latency_ms=100.0, quality_score=0.95)
    breaker.record_success(latency_ms=120.0, quality_score=0.96)
    assert breaker.state == CircuitState.CLOSED


def test_breaker_quality_degradation_trip():
    """Verify breaker trips if semantic quality drops below threshold."""
    config = BreakerConfig(quality_threshold=0.70)
    breaker = AIBreaker("openai", config)

    breaker.record_success(latency_ms=200.0, quality_score=0.45)
    assert breaker.state == CircuitState.OPEN
    assert "quality degradation" in breaker.last_trip_reason.lower()


def test_resilience_manager_failover():
    """Verify priority continuity chain failover."""
    mgr = ResilienceManager()
    # Trip primary provider
    openai_b = mgr.get_breaker("openai")
    openai_b.trip("Outage simulated")

    # Should failover to anthropic
    selected = mgr.select_healthy_provider(primary="openai", secondary="anthropic")
    assert selected == "anthropic"


def test_semantic_mapping():
    """Verify prompt and tool schema conversions across dialects."""
    msgs = [
        {"role": "system", "content": "You are an assistant."},
        {"role": "user", "content": "Hello world."},
    ]

    # Map to Anthropic
    anth_msgs, anth_sys = map_messages(msgs, "anthropic")
    assert anth_sys == "You are an assistant."
    assert len(anth_msgs) == 1
    assert anth_msgs[0]["role"] == "user"

    # Map tool schema to Anthropic
    tool_spec = {
        "type": "function",
        "function": {
            "name": "lookup_stock",
            "description": "Stock price lookup",
            "parameters": {"type": "object", "properties": {"ticker": {"type": "string"}}},
        },
    }
    converted = map_tool_schema(tool_spec, "anthropic")
    assert "input_schema" in converted
    assert converted["name"] == "lookup_stock"

    # Map parameters
    params = map_parameters("anthropic", temperature=1.5, max_tokens=500)
    assert params["temperature"] == 1.0  # clamped for Anthropic


def test_run_disaster_recovery_drill():
    """Verify automated DR drill execution and report structure."""
    report = run_disaster_recovery_drill(
        primary_provider="openai",
        fallback_provider="anthropic",
        fault_type="outage_500",
    )

    assert report.circuit_tripped is True
    assert report.business_continuity_preserved is True
    assert report.tool_conversion_success is True
    assert report.quality_retention_pct >= 90.0
    assert len(report.actionable_recommendations) > 0
