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
from typing import Any

from airun.events.models import TraceRecord, TraceSpan

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
            endpoint
            or os.getenv("AIRUN_OTLP_ENDPOINT")
            or "http://localhost:4318/v1/traces"
        )
        self.timeout = timeout
        self.is_enabled = bool(os.getenv("AIRUN_OTLP_ENDPOINT") or endpoint)

    def span_to_otlp_dict(self, span: TraceSpan, trace_id: str) -> dict[str, Any]:
        """Convert an airun TraceSpan to standard OTLP JSON format."""
        start_ns = _parse_to_ns(span.start_time)
        end_ns = _parse_to_ns(span.end_time) or (start_ns + int((span.duration_ms or 0.0) * 1_000_000))

        attributes = [
            {"key": "span.kind", "value": {"stringValue": span.kind.value if hasattr(span.kind, "value") else str(span.kind)}},
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
                            "scope": {"name": "airun-sdk", "version": "0.1.3"},
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
            logger.debug("OTLP export to %s failed (collector likely offline): %s", self.endpoint, e)
            return False
