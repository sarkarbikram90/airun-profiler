"""Tests for Agent Efficiency Analyzer and MCP tracking."""

from airun.analysis.agent_efficiency import analyze_agent_efficiency
from airun.events.models import SpanKind, TraceRecord, TraceSpan
from airun.utils.time_utils import now_utc_iso


def test_analyze_agent_efficiency_redundancy():
    trace_id = "test_agent_trace"
    spans = [
        TraceSpan(
            trace_id=trace_id,
            span_id="s1",
            name="query_vector_store",
            kind=SpanKind.DB,
            start_time=now_utc_iso(),
            end_time=now_utc_iso(),
            duration_ms=450.0,
        ),
        TraceSpan(
            trace_id=trace_id,
            span_id="s2",
            name="query_vector_store",
            kind=SpanKind.DB,
            start_time=now_utc_iso(),
            end_time=now_utc_iso(),
            duration_ms=450.0,
        ),
        TraceSpan(
            trace_id=trace_id,
            span_id="s3",
            name="github_search",
            kind=SpanKind.TOOL,
            start_time=now_utc_iso(),
            end_time=now_utc_iso(),
            duration_ms=800.0,
        ),
        TraceSpan(
            trace_id=trace_id,
            span_id="s4",
            name="reasoning_step",
            kind=SpanKind.LLM,
            model="gpt-4o",
            tokens_input=8100,
            tokens_output=500,
            cost_usd=0.045,
            start_time=now_utc_iso(),
            end_time=now_utc_iso(),
            duration_ms=1200.0,
        ),
        TraceSpan(
            trace_id=trace_id,
            span_id="s5",
            name="final_synthesis",
            kind=SpanKind.LLM,
            model="claude-3-5-sonnet",
            tokens_input=31700,
            tokens_output=800,
            cost_usd=0.095,
            start_time=now_utc_iso(),
            end_time=now_utc_iso(),
            duration_ms=1900.0,
        ),
    ]
    record = TraceRecord(trace_id=trace_id, created_at=now_utc_iso(), spans=spans)
    report = analyze_agent_efficiency(record)

    assert report.trace_id == trace_id
    assert report.redundant_cost_pct > 0.0
    assert len(report.findings) >= 2

    categories = [f.category for f in report.findings]
    assert "model_escalation" in categories
    assert "serializable_parallelism" in categories
    assert len(report.mcp_servers) >= 1
