"""Unit tests for OpenTelemetry (OTLP) Span Exporter."""

from __future__ import annotations

import pytest

from airun.events.models import SpanKind, TraceRecord, TraceSpan
from airun.exporters.otlp import OTLPSpanExporter


def test_span_to_otlp_dict() -> None:
    exporter = OTLPSpanExporter(endpoint="http://localhost:4318/v1/traces")
    span = TraceSpan(
        trace_id="trace-123",
        span_id="span-456",
        name="research_step",
        kind=SpanKind.AGENT_STEP,
        start_time="1700000000.0",
        end_time="1700000001.0",
        duration_ms=1000.0,
        cost_usd=0.0042,
        tokens_input=100,
        tokens_output=50,
        model="gpt-4o",
    )

    d = exporter.span_to_otlp_dict(span, trace_id="trace-123")
    assert d["traceId"] == "trace-123"
    assert d["spanId"] == "span-456"
    assert d["name"] == "research_step"
    assert int(d["startTimeUnixNano"]) > 0
    assert int(d["endTimeUnixNano"]) >= int(d["startTimeUnixNano"])


def test_trace_to_otlp_payload() -> None:
    exporter = OTLPSpanExporter(endpoint="http://localhost:4318/v1/traces")
    spans = [
        TraceSpan(
            trace_id="trace-abc",
            span_id="span-1",
            name="workflow_root",
            kind=SpanKind.WORKFLOW,
            start_time="1700000000.0",
        )
    ]
    record = TraceRecord(trace_id="trace-abc", created_at="2026-09-07T00:00:00Z", spans=spans)

    payload = exporter.trace_to_otlp_payload(record)
    assert "resourceSpans" in payload
    assert len(payload["resourceSpans"]) == 1
    assert payload["resourceSpans"][0]["scopeSpans"][0]["spans"][0]["name"] == "workflow_root"


def test_trace_auto_exports_otlp(monkeypatch: pytest.MonkeyPatch) -> None:
    exported_records = []

    def mock_export(self: OTLPSpanExporter, record: TraceRecord) -> bool:
        exported_records.append(record)
        return True

    monkeypatch.setattr(OTLPSpanExporter, "export", mock_export)
    monkeypatch.setenv("AIRUN_OTLP_ENDPOINT", "http://localhost:4318/v1/traces")

    from airun.sdk.tracer import trace

    @trace(name="otlp_test_step")
    def run_step() -> int:
        return 42

    result = run_step()
    assert result == 42
    assert len(exported_records) == 1
    assert exported_records[0].spans[0].name == "otlp_test_step"
