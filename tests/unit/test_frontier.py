"""Unit tests for the Efficient Frontier of AI and Eval-Driven Routing."""

from airun.routing.eval_router import (
    EvalRouter,
    RoutingPolicy,
    RoutingTier,
)
from airun.routing.frontier import (
    find_optimal_model,
    get_efficient_frontier,
)


def test_efficient_frontier_pareto_optimality():
    """Verify Pareto frontier computation."""
    frontier = get_efficient_frontier()
    assert len(frontier) > 0

    # Ensure frontier models have pareto status computed
    pareto_models = [m for m in frontier if m.is_pareto_optimal]
    assert len(pareto_models) >= 3

    # Check that Sonnet and Flash are Pareto optimal
    sonnet = next(m for m in frontier if m.model_id == "claude-3-5-sonnet")
    flash = next(m for m in frontier if m.model_id == "gemini-1-5-flash")
    assert sonnet.is_pareto_optimal is True
    assert flash.is_pareto_optimal is True


def test_find_optimal_model_by_sla():
    """Verify model selection matching SLA constraints."""
    # Strict Tier 1 SLA: Quality >= 0.95
    model_t1 = find_optimal_model(min_quality=0.95, priority="cost")
    assert model_t1 is not None
    assert model_t1.quality_score >= 0.95

    # Budget Tier 3 SLA: Quality >= 0.80
    model_t3 = find_optimal_model(min_quality=0.80, priority="cost")
    assert model_t3 is not None
    assert model_t3.blended_cost_per_1m < 1.0


def test_eval_router_tier_dispatch():
    """Verify EvalRouter tier-based policies."""
    router = EvalRouter()

    # Tier 1 Critical
    decision_t1 = router.route(
        RoutingPolicy(tier=RoutingTier.TIER_1_CRITICAL, shadow_testing_enabled=False)
    )
    assert decision_t1.min_quality_sla == 0.95
    assert decision_t1.expected_quality >= 0.95
    assert len(decision_t1.fallback_models) > 0

    # Tier 2 Standard
    decision_t2 = router.route(
        RoutingPolicy(tier=RoutingTier.TIER_2_STANDARD, shadow_testing_enabled=False)
    )
    assert decision_t2.min_quality_sla == 0.88

    # Tier 3 Economy
    decision_t3 = router.route(
        RoutingPolicy(tier=RoutingTier.TIER_3_ECONOMY, shadow_testing_enabled=False)
    )
    assert decision_t3.min_quality_sla == 0.80


def test_eval_router_shadow_testing_and_feedback():
    """Verify shadow testing feedback loop."""
    router = EvalRouter()
    # Force shadow testing
    policy = RoutingPolicy(
        tier=RoutingTier.TIER_1_CRITICAL,
        shadow_testing_enabled=True,
        shadow_traffic_rate=1.0,
    )
    decision = router.route(policy)
    assert decision.is_shadow_test is True

    # Record eval outcome
    router.record_eval_outcome(
        model_id=decision.selected_model,
        evaluated_quality=0.92,
        latency_ms=200.0,
        cost_usd=0.0005,
        passed_sla=True,
    )

    insights = router.get_shadow_insights()
    assert len(insights) > 0
    assert any(i["model_id"] == decision.selected_model for i in insights)
