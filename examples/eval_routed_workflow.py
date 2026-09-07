"""Example: Eval-Driven Routing and Efficient Frontier Optimization.

Demonstrates the implementation of spec.md:
"The Solution: Eval-Driven Routing
1. The Baseline: The customer defines a 'Quality Score' (e.g. 95% pass rate).
2. The Shadow Test: airun continuously routes a small percentage of live traffic
   to cheaper/faster models in the background, grading the output against the eval harness.
3. The Optimization: Shows the Efficient Frontier of AI.
4. The Action: airun allows setting a policy: 'Never drop below 95% quality for Tier 1 customers,
   but route Tier 2 free-tier users to Model B.'"
"""

import time

from airun import SpanKind, set_span_metadata, set_span_quality, set_span_tokens, trace
from airun.routing import EvalRouter, RoutingPolicy, RoutingTier, get_efficient_frontier


def main():
    print("=" * 65)
    print("  [airun] Eval-Driven Routing & Efficient Frontier Demo")
    print("=" * 65)

    router = EvalRouter()
    frontier = get_efficient_frontier()

    print(f"\n>> Loaded {len(frontier)} models on the Efficient Frontier:")
    for m in frontier:
        pareto_tag = "[PARETO OPTIMAL]" if m.is_pareto_optimal else "[DOMINATED]"
        print(
            f"  * {m.display_name:<28} Quality: {m.quality_score * 100:.1f}% | Cost: ${m.blended_cost_per_1m:>5.2f}/1M | {pareto_tag}"
        )

    # Case 1: Tier 1 Mission-Critical Customer (Quality SLA >= 0.95)
    tier1_policy = RoutingPolicy(
        tier=RoutingTier.TIER_1_CRITICAL,
        min_quality_threshold=0.95,
        shadow_testing_enabled=False,
    )
    decision_1 = router.route(tier1_policy)
    print(f"\n[Tier 1 Route Decision]: {decision_1.selected_model} ({decision_1.provider})")
    print(f"  Rationale: {decision_1.rationale}")

    # Profile the Tier 1 execution
    with trace("tier1_legal_analysis", kind=SpanKind.WORKFLOW):
        with trace(
            "reasoning_step",
            kind=SpanKind.LLM,
            model=decision_1.selected_model,
            provider=decision_1.provider,
        ):
            time.sleep(0.08)
            set_span_tokens(input_tokens=2500, output_tokens=800)
            set_span_quality(0.97, {"eval_harness": "legal_contract_pass_rate", "accuracy": 0.98})
            set_span_metadata({"client_tier": "enterprise_tier_1"})

    # Case 2: Tier 2 Standard Production (Quality SLA >= 0.88, Cost-Optimized)
    tier2_policy = RoutingPolicy(
        tier=RoutingTier.TIER_2_STANDARD,
        min_quality_threshold=0.88,
        shadow_traffic_rate=0.50,  # simulate active shadow testing
    )
    decision_2 = router.route(tier2_policy)
    print(f"\n[Tier 2 Route Decision]: {decision_2.selected_model} ({decision_2.provider})")
    print(f"  Rationale: {decision_2.rationale}")
    if decision_2.is_shadow_test:
        print(
            "  * [SHADOW TEST ACTIVE]: Exploring cheaper candidate model for live evaluation benchmark"
        )

    with trace("tier2_agent_chat", kind=SpanKind.WORKFLOW):
        with trace(
            "chat_response_step",
            kind=SpanKind.LLM,
            model=decision_2.selected_model,
            provider=decision_2.provider,
        ):
            time.sleep(0.04)
            set_span_tokens(input_tokens=850, output_tokens=220)
            set_span_quality(0.91, {"eval_harness": "standard_qa_accuracy"})
            set_span_metadata(
                {"client_tier": "standard_tier_2", "is_shadow": decision_2.is_shadow_test}
            )

    # Record evaluation outcome back to router
    router.record_eval_outcome(
        model_id=decision_2.selected_model,
        evaluated_quality=0.91,
        latency_ms=decision_2.expected_latency_ms,
        cost_usd=0.0003,
        passed_sla=True,
    )

    print("\n>> Shadow Testing Empirical Insights:")
    for insight in router.get_shadow_insights():
        print(
            f"  * Model: {insight['model_id']} | Tested Quality: {insight['measured_quality'] * 100:.1f}% | Samples: {insight['sample_count']}"
        )

    print(
        "\n[OK] Eval-driven routing workflow completed. View trace details with 'airun report latest' or 'airun frontier'."
    )


if __name__ == "__main__":
    main()
