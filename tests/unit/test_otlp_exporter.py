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


def test_otlp_payload_to_trace_records_roundtrip() -> None:
    from airun.exporters.otlp import otlp_payload_to_trace_records

    raw_payload = {
        "resourceSpans": [
            {
                "resource": {
                    "attributes": [
                        {"key": "service.name", "value": {"stringValue": "external-llm-service"}},
                        {"key": "airun.trace_id", "value": {"stringValue": "tr-otlp-999"}},
                    ]
                },
                "scopeSpans": [
                    {
                        "spans": [
                            {
                                "traceId": "tr-otlp-999",
                                "spanId": "span-root-01",
                                "name": "chat_completion",
                                "startTimeUnixNano": "1710000000000000000",
                                "endTimeUnixNano": "1710000000250000000",
                                "attributes": [
                                    {"key": "model", "value": {"stringValue": "gpt-4o"}},
                                    {"key": "provider", "value": {"stringValue": "openai"}},
                                    {"key": "tokens.input", "value": {"intValue": 1500}},
                                    {"key": "tokens.output", "value": {"intValue": 350}},
                                    {"key": "cost.usd", "value": {"doubleValue": 0.00725}},
                                ],
                                "status": {"code": 1},
                            }
                        ]
                    }
                ],
            }
        ]
    }

    records = otlp_payload_to_trace_records(raw_payload)
    assert len(records) == 1
    rec = records[0]
    assert rec.trace_id == "tr-otlp-999"
    assert len(rec.spans) == 1
    span = rec.spans[0]
    assert span.name == "chat_completion"
    assert span.model == "gpt-4o"
    assert span.tokens_input == 1500
    assert span.tokens_output == 350
    assert span.cost_usd == 0.00725
    assert span.duration_ms == 250.0
    assert rec.summary is not None
    assert rec.summary.total_cost_usd == 0.00725
