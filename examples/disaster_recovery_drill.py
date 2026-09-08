"""Example: AI Disaster Recovery (DR) Drill and Business Continuity Failover.

Demonstrates the implementation of SPECIFICATION.md:
"Multi-model / multi-provider AI business continuity:
Can workload X run on provider Y?
What capabilities are lost? What's the quality delta? What's the cost? What's the latency?
What tools break? What prompts must change?
Then periodically runs automated disaster-recovery drills."
"""

from airun import SpanKind, set_span_metadata, set_span_quality, trace
from airun.resilience import (
    AIBreaker,
    BreakerConfig,
    map_messages,
    map_parameters,
    map_tool_schema,
    run_disaster_recovery_drill,
)


def main():
    print("=" * 65)
    print("  [airun] AI Disaster Recovery (DR) & Resilience Drill Demo")
    print("=" * 65)

    # 1. Setup multi-provider circuit breaker
    openai_breaker = AIBreaker(
        "openai", BreakerConfig(failure_threshold=2, latency_threshold_ms=1500.0)
    )
    print(f"\n>> Initial OpenAI Breaker State: {openai_breaker.state.value.upper()}")

    # 2. Simulate mission-critical multi-turn task definition
    messages = [
        {"role": "system", "content": "You are a mission-critical AI financial risk analyzer."},
        {"role": "user", "content": "Analyze portfolio exposure across sovereign bonds."},
    ]
    tool_spec = {
        "type": "function",
        "function": {
            "name": "calc_var",
            "description": "Calculate Value-at-Risk",
            "parameters": {
                "type": "object",
                "properties": {"confidence": {"type": "number"}},
            },
        },
    }

    # 3. Simulate Primary Provider Outage (HTTP 500 errors)
    print("\n>> Ingesting simulated outage on primary provider (OpenAI):")
    with trace("primary_workload_attempt", kind=SpanKind.WORKFLOW):
        with trace("openai_api_call", kind=SpanKind.LLM, model="gpt-4o", provider="openai") as span:
            openai_breaker.record_failure("HTTP 500: Internal Server Error")
            span.status = "failure"
            print("  * Attempt 1: Failed (HTTP 500)")

        with trace(
            "openai_api_retry", kind=SpanKind.LLM, model="gpt-4o", provider="openai"
        ) as span2:
            openai_breaker.record_failure("HTTP 500: Rate limit / upstream failure")
            span2.status = "failure"
            print("  * Attempt 2: Failed (HTTP 500)")

    # 4. Breaker trips
    print(
        f"\n>> Circuit Breaker Status: {openai_breaker.state.value.upper()} (Trips: {openai_breaker.trip_count})"
    )
    print(f"  Reason: {openai_breaker.last_trip_reason}")

    # 5. Semantic Equivalence Mapping to Promote Fallback (Anthropic)
    print("\n>> Executing Semantic Equivalence Mapping for Anthropic failover:")
    converted_msgs, sys_prompt = map_messages(messages, "anthropic")
    converted_tool = map_tool_schema(tool_spec, "anthropic")
    converted_params = map_parameters("anthropic", temperature=0.7, max_tokens=2048)

    print(f"  * Extracted Anthropic system prompt: '{sys_prompt[:35]}...'")
    print(
        f"  * Converted tool schema format: input_schema present? {'input_schema' in converted_tool}"
    )
    print(f"  * Clamped temperature: {converted_params['temperature']}")

    # 6. Execute Promoted Fallback Workload
    print("\n>> Dispatching workload to Promoted Fallback (Anthropic / Claude 3.5 Sonnet):")
    with trace("failover_dr_workload", kind=SpanKind.WORKFLOW):
        with trace(
            "claude_fallback_step",
            kind=SpanKind.LLM,
            model="claude-3-5-sonnet",
            provider="anthropic",
        ):
            set_span_quality(0.96, {"eval_provenance": "synthetic_dr_benchmark"})
            set_span_metadata(
                {
                    "failover": True,
                    "original_provider": "openai",
                    "promoted_provider": "anthropic",
                }
            )
            print("  * [OK] Fallback execution succeeded with 96% quality retention!")

    # 7. Execute automated comprehensive DR Drill Audit
    print("\n>> Generating Comprehensive DR Drill Report:")
    report = run_disaster_recovery_drill(
        primary_provider="openai",
        fallback_provider="anthropic",
        fault_type="outage_500",
    )
    print(f"  * Drill ID: {report.drill_id}")
    print(
        f"  * Continuity Status: {'PRESERVED' if report.business_continuity_preserved else 'DEGRADED'}"
    )
    print(f"  * Cost Delta: {report.cost_delta_pct:+.1f}%")
    print(f"  * Latency Delta: {report.latency_delta_ms:+.1f}ms")
    print(f"  * Quality Retained: {report.quality_retention_pct:.1f}%")
    print(f"  * Schema Mapped: {report.tool_conversion_success}")

    print("\n[OK] Disaster recovery drill demonstration complete.")


if __name__ == "__main__":
    main()
