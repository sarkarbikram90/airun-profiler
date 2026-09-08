"""
airun: AI Runtime Profiler
Observe execution paths, latency, tool calls, and token cost of AI workflows.
"""

from airun.events.models import (
    DiagnosticFinding,
    FindingSeverity,
    SpanKind,
    SpanStatus,
    TraceRecord,
    TraceSpan,
    TraceSummary,
)
from airun.incident.graph import build_sample_incident_graph
from airun.pricing.energy import (
    calculate_energy,
    calculate_intelligence_per_dollar,
    calculate_intelligence_per_watt,
)
from airun.pricing.engine import calculate_cost, get_cost_engine
from airun.resilience import (
    AIBreaker,
    ResilienceManager,
    get_resilience_manager,
    run_disaster_recovery_drill,
)
from airun.routing import (
    EvalRouter,
    RoutingPolicy,
    RoutingTier,
    get_efficient_frontier,
    get_eval_router,
)
from airun.sdk.context import (
    get_collected_spans,
    get_current_span,
    get_current_span_id,
    get_current_trace_id,
    reset_trace_context,
)
from airun.sdk.redaction import redact_data
from airun.sdk.tracer import (
    TraceContext,
    record_retry,
    set_span_cost,
    set_span_metadata,
    set_span_model,
    set_span_quality,
    set_span_status,
    set_span_tokens,
    trace,
)
from airun.sdk.wrappers import wrap_openai_client
from airun.store import get_trace_store

__version__ = "0.1.3"

__all__ = [
    "trace",
    "TraceContext",
    "SpanKind",
    "SpanStatus",
    "FindingSeverity",
    "DiagnosticFinding",
    "TraceSpan",
    "TraceSummary",
    "TraceRecord",
    "set_span_tokens",
    "set_span_cost",
    "set_span_model",
    "set_span_status",
    "set_span_metadata",
    "set_span_quality",
    "record_retry",
    "get_current_trace_id",
    "get_current_span_id",
    "get_current_span",
    "get_collected_spans",
    "reset_trace_context",
    "calculate_cost",
    "calculate_energy",
    "calculate_intelligence_per_dollar",
    "calculate_intelligence_per_watt",
    "get_cost_engine",
    "get_trace_store",
    "redact_data",
    "wrap_openai_client",
    "get_efficient_frontier",
    "EvalRouter",
    "RoutingPolicy",
    "RoutingTier",
    "get_eval_router",
    "AIBreaker",
    "ResilienceManager",
    "get_resilience_manager",
    "run_disaster_recovery_drill",
    "build_sample_incident_graph",
]
