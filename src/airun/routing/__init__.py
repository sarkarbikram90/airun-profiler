"""airun routing package: Eval-Driven Routing & The Efficient Frontier of AI."""

from airun.routing.eval_router import (
    EvalRouter,
    RouteDecision,
    RoutingPolicy,
    RoutingTier,
    get_eval_router,
)
from airun.routing.frontier import (
    STANDARD_MODEL_CATALOG,
    ModelProfile,
    compute_pareto_frontier,
    find_optimal_model,
    get_efficient_frontier,
)

__all__ = [
    "STANDARD_MODEL_CATALOG",
    "ModelProfile",
    "compute_pareto_frontier",
    "find_optimal_model",
    "get_efficient_frontier",
    "EvalRouter",
    "RouteDecision",
    "RoutingPolicy",
    "RoutingTier",
    "get_eval_router",
]
