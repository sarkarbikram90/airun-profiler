"""OpenTelemetry (OTLP) Span Exporter for airun.

Enables streaming logical @trace spans directly to the Rust Real-Time Data Plane
(crates/airun-collector) or any standard OTLP collector.
"""

from __future__ import annotations

import datetime
import json
import logging
import os
import urllib.error
import urllib.request
import uuid
from typing import Any

from airun.events.models import (
    SpanKind,
    SpanStatus,
    TraceRecord,
    TraceSpan,
    TraceSummary,
)
from airun.pricing import calculate_cost

logger = logging.getLogger("airun.exporters.otlp")


def _parse_to_ns(ts_val: Any) -> int:
    """Safely converts string or float timestamp to Unix nanoseconds."""
    if not ts_val:
        return 0
    try:
        return int(float(ts_val) * 1_000_000_000)
    except (ValueError, TypeError):
        try:
            dt = datetime.datetime.fromisoformat(str(ts_val))
            return int(dt.timestamp() * 1_000_000_000)
        except Exception:
            return 0


class OTLPSpanExporter:
    """Exports airun execution spans to an OTLP-compatible HTTP collector."""

    def __init__(self, endpoint: str | None = None, timeout: float = 2.0) -> None:
        self.endpoint = (
            endpoint or os.getenv("AIRUN_OTLP_ENDPOINT") or "http://localhost:4318/v1/traces"
        )
        self.timeout = timeout
        self.is_enabled = bool(os.getenv("AIRUN_OTLP_ENDPOINT") or endpoint)

    def span_to_otlp_dict(self, span: TraceSpan, trace_id: str) -> dict[str, Any]:
        """Convert an airun TraceSpan to standard OTLP JSON format."""
        start_ns = _parse_to_ns(span.start_time)
        end_ns = _parse_to_ns(span.end_time) or (
            start_ns + int((span.duration_ms or 0.0) * 1_000_000)
        )

        attributes = [
            {
                "key": "span.kind",
                "value": {
                    "stringValue": span.kind.value
                    if hasattr(span.kind, "value")
                    else str(span.kind)
                },
            },
            {"key": "cost.usd", "value": {"doubleValue": span.cost_usd or 0.0}},
            {"key": "tokens.input", "value": {"intValue": span.tokens_input or 0}},
            {"key": "tokens.output", "value": {"intValue": span.tokens_output or 0}},
        ]

        if span.model:
            attributes.append({"key": "model", "value": {"stringValue": span.model}})
        if span.provider:
            attributes.append({"key": "provider", "value": {"stringValue": span.provider}})
        if span.error:
            attributes.append({"key": "error", "value": {"stringValue": str(span.error)}})

        return {
            "traceId": trace_id,
            "spanId": span.span_id,
            "parentSpanId": span.parent_id or "",
            "name": span.name,
            "kind": 1,  # SPAN_KIND_INTERNAL
            "startTimeUnixNano": str(start_ns),
            "endTimeUnixNano": str(end_ns),
            "attributes": attributes,
            "status": {"code": 2 if span.error else 1},
        }

    def trace_to_otlp_payload(self, trace: TraceRecord) -> dict[str, Any]:
        """Encapsulate an airun TraceRecord into an OTLP ResourceSpans payload."""
        spans_json = [self.span_to_otlp_dict(s, trace.trace_id) for s in trace.spans]

        service_name = (
            (trace.summary.name if trace.summary and trace.summary.name else None)
            or (trace.spans[0].name if trace.spans else None)
            or "airun-service"
        )

        return {
            "resourceSpans": [
                {
                    "resource": {
                        "attributes": [
                            {"key": "service.name", "value": {"stringValue": service_name}},
                            {"key": "airun.trace_id", "value": {"stringValue": trace.trace_id}},
                        ]
                    },
                    "scopeSpans": [
                        {
                            "scope": {"name": "airun-sdk", "version": "0.1.7"},
                            "spans": spans_json,
                        }
                    ],
                }
            ]
        }

    def export(self, trace: TraceRecord) -> bool:
        """Export a trace to the configured OTLP endpoint."""
        payload = self.trace_to_otlp_payload(trace)
        data = json.dumps(payload).encode("utf-8")

        req = urllib.request.Request(
            self.endpoint,
            data=data,
            headers={"Content-Type": "application/json"},
            method="POST",
        )

        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                return resp.status in (200, 202)
        except (urllib.error.URLError, TimeoutError, OSError) as e:
            logger.debug(
                "OTLP export to %s failed (collector likely offline): %s", self.endpoint, e
            )
            return False

    # Alias for API compatibility
    export_trace = export


def _extract_attr_value(val: Any) -> Any:
    if isinstance(val, dict):
        for key in ("stringValue", "intValue", "doubleValue", "boolValue"):
            if key in val:
                return val[key]
    return val


def otlp_payload_to_trace_records(payload: dict[str, Any]) -> list[TraceRecord]:
    """Parse standard OpenTelemetry (OTLP) ResourceSpans JSON payload into native TraceRecords.

    Enables zero-code ingestion from external libraries (LangChain, vLLM, LiteLLM, OpenLLMetry).
    """
    resource_spans = payload.get("resourceSpans")
    if resource_spans is None and "spans" in payload:
        # Support flat span arrays for convenience
        resource_spans = [{"scopeSpans": [{"spans": payload["spans"]}]}]
    elif not resource_spans:
        return []

    spans_by_trace: dict[str, list[TraceSpan]] = {}

    for rs in resource_spans:
        res_attrs: dict[str, Any] = {}
        for attr in rs.get("resource", {}).get("attributes", []):
            if "key" in attr:
                res_attrs[attr["key"]] = _extract_attr_value(attr.get("value"))

        res_service_name = res_attrs.get("service.name", "ai-service")
        res_trace_id = res_attrs.get("airun.trace_id")

        for ss in rs.get("scopeSpans", []):
            for s in ss.get("spans", []):
                t_id = s.get("traceId") or res_trace_id or uuid.uuid4().hex
                span_id = s.get("spanId") or uuid.uuid4().hex[:16]
                parent_id = s.get("parentSpanId") or None
                name = s.get("name") or "unnamed_span"

                # Parse Unix nanoseconds
                start_ns = int(s.get("startTimeUnixNano") or 0)
                end_ns = int(s.get("endTimeUnixNano") or 0)
                if start_ns > 0 and end_ns >= start_ns:
                    duration_ms = (end_ns - start_ns) / 1_000_000.0
                    start_iso = datetime.datetime.fromtimestamp(
                        start_ns / 1e9, tz=datetime.timezone.utc
                    ).isoformat()
                    end_iso = datetime.datetime.fromtimestamp(
                        end_ns / 1e9, tz=datetime.timezone.utc
                    ).isoformat()
                else:
                    duration_ms = 0.0
                    start_iso = datetime.datetime.now(datetime.timezone.utc).isoformat()
                    end_iso = start_iso

                # Extract attributes
                span_attrs: dict[str, Any] = {}
                for attr in s.get("attributes", []):
                    if "key" in attr:
                        span_attrs[attr["key"]] = _extract_attr_value(attr.get("value"))

                model = (
                    span_attrs.get("model")
                    or span_attrs.get("gen_ai.request.model")
                    or span_attrs.get("llm.model_name")
                )
                provider = span_attrs.get("provider") or span_attrs.get("gen_ai.system") or "openai"
                tok_in = int(
                    span_attrs.get("tokens.input")
                    or span_attrs.get("gen_ai.usage.prompt_tokens")
                    or span_attrs.get("gen_ai.usage.input_tokens")
                    or 0
                )
                tok_out = int(
                    span_attrs.get("tokens.output")
                    or span_attrs.get("gen_ai.usage.completion_tokens")
                    or span_attrs.get("gen_ai.usage.output_tokens")
                    or 0
                )
                cost_usd = float(span_attrs.get("cost.usd") or span_attrs.get("cost") or 0.0)

                # If cost was not supplied by exporter, calculate via pricing registry
                if cost_usd == 0.0 and model and (tok_in > 0 or tok_out > 0):
                    cost_usd = calculate_cost(model, tok_in, tok_out) or 0.0

                raw_kind = str(span_attrs.get("span.kind", "internal")).lower()
                if "llm" in raw_kind or "model" in name.lower() or model:
                    kind = SpanKind.LLM
                elif "tool" in raw_kind or "tool" in name.lower():
                    kind = SpanKind.TOOL
                elif "db" in raw_kind or "query" in name.lower():
                    kind = SpanKind.DB
                elif "workflow" in raw_kind or not parent_id:
                    kind = SpanKind.WORKFLOW
                else:
                    kind = SpanKind.AGENT_STEP

                status_code = s.get("status", {}).get("code", 1)
                status = SpanStatus.FAILURE if status_code == 2 else SpanStatus.SUCCESS

                trace_span = TraceSpan(
                    trace_id=t_id,
                    span_id=span_id,
                    parent_id=parent_id,
                    name=name,
                    kind=kind,
                    status=status,
                    start_time=start_iso,
                    end_time=end_iso,
                    duration_ms=round(duration_ms, 2),
                    tokens_input=tok_in,
                    tokens_output=tok_out,
                    model=model,
                    provider=provider,
                    cost_usd=round(cost_usd, 6),
                    attributes=span_attrs,
                )

                if t_id not in spans_by_trace:
                    spans_by_trace[t_id] = []
                spans_by_trace[t_id].append(trace_span)

    records: list[TraceRecord] = []
    for t_id, spans in spans_by_trace.items():
        total_duration = max((s.duration_ms or 0.0) for s in spans) if spans else 0.0
        total_tokens = sum((s.tokens_input or 0) + (s.tokens_output or 0) for s in spans)
        total_cost = sum(s.cost_usd or 0.0 for s in spans)
        has_error = any(s.status == SpanStatus.FAILURE for s in spans)
        workflow_name = spans[0].name if spans else res_service_name

        summary = TraceSummary(
            trace_id=t_id,
            name=workflow_name,
            start_time=spans[0].start_time
            if spans
            else datetime.datetime.now(datetime.timezone.utc).isoformat(),
            end_time=spans[-1].end_time if spans else None,
            total_duration_ms=round(total_duration, 2),
            total_tokens=total_tokens,
            total_cost_usd=round(total_cost, 6),
            outcome=SpanStatus.FAILURE if has_error else SpanStatus.SUCCESS,
            span_count=len(spans),
        )

        records.append(
            TraceRecord(
                trace_id=t_id,
                created_at=summary.start_time,
                spans=spans,
                summary=summary,
            )
        )

    return records
