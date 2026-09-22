"""Tests for Trace -> GPU -> Root Cause Diagnostic engine."""

from airun.analysis.diagnose import run_trace_diagnostic
from airun.events.models import SpanKind, SpanStatus, TraceRecord, TraceSpan, TraceSummary
from airun.exporters.html_report import generate_diagnostic_html
from airun.utils.time_utils import now_utc_iso


def _create_sample_trace(workflow_name: str = "coding-agent") -> TraceRecord:
    trace_id = "test_diag_trace_001"
    spans = [
        TraceSpan(
            trace_id=trace_id,
            span_id="root",
            parent_id=None,
            name=workflow_name,
            kind=SpanKind.WORKFLOW,
            start_time=now_utc_iso(),
            end_time=now_utc_iso(),
            duration_ms=18420.0,
        ),
        TraceSpan(
            trace_id=trace_id,
            span_id="planner",
            parent_id="root",
            name="planner_step",
            kind=SpanKind.LLM,
            start_time=now_utc_iso(),
            end_time=now_utc_iso(),
            duration_ms=4500.0,
            tokens_input=1200,
            tokens_output=300,
            cost_usd=0.034,
        ),
        TraceSpan(
            trace_id=trace_id,
            span_id="tool1",
            parent_id="root",
            name="code_search_tool",
            kind=SpanKind.TOOL,
            start_time=now_utc_iso(),
            end_time=now_utc_iso(),
            duration_ms=2500.0,
        ),
        TraceSpan(
            trace_id=trace_id,
            span_id="tool2",
            parent_id="root",
            name="test_runner_tool",
            kind=SpanKind.TOOL,
            start_time=now_utc_iso(),
            end_time=now_utc_iso(),
            duration_ms=3100.0,
        ),
    ]
    summary = TraceSummary(
        trace_id=trace_id,
        name=workflow_name,
        outcome=SpanStatus.SUCCESS,
        start_time=now_utc_iso(),
        end_time=now_utc_iso(),
        total_duration_ms=18420.0,
        total_cost_usd=0.084,
        total_tokens=1500,
        span_count=len(spans),
    )
    return TraceRecord(trace_id=trace_id, created_at=now_utc_iso(), spans=spans, summary=summary)


def test_run_trace_diagnostic_dataloader_starvation():
    record = _create_sample_trace()
    diagnostic = run_trace_diagnostic(
        record=record,
        accelerator="h100",
        num_gpus=8,
        monthly_requests=600_000,
    )

    assert diagnostic.workflow_name == "coding-agent"
    assert diagnostic.duration_sec == 18.42
    assert diagnostic.cost_per_request_usd == 0.084
    assert diagnostic.accelerator == "H100 SXM"
    assert diagnostic.root_cause == "DataLoader starvation"
    assert len(diagnostic.evidence) >= 3
    assert diagnostic.estimated_waste_per_request_usd > 0.0
    assert diagnostic.monthly_waste_usd > 10_000.0
    assert len(diagnostic.recommendations) >= 2
    assert "gpu_utilization" in diagnostic.expected_result


def test_generate_diagnostic_html():
    record = _create_sample_trace()
    diagnostic = run_trace_diagnostic(record=record, accelerator="h100")
    html = generate_diagnostic_html(diagnostic)

    assert "<!DOCTYPE html>" in html
    assert "AIRUN DIAGNOSTIC" in html
    assert diagnostic.workflow_name in html
    assert diagnostic.root_cause in html
    assert f"${diagnostic.cost_per_request_usd:.4f}" in html
