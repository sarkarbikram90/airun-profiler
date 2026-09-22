"""Unit tests for airun built-in HTTP server and REST API."""

import io
from unittest.mock import MagicMock

from airun.server import AirunServerHandler


def test_server_health_endpoint():
    """Verify /healthz returns 200 OK and version info."""
    handler = AirunServerHandler.__new__(AirunServerHandler)
    handler.path = "/healthz"
    handler.rfile = io.BytesIO()
    handler.wfile = io.BytesIO()
    handler.headers = {}
    handler.command = "GET"

    # Mock send_response, send_header, end_headers
    handler.send_response = MagicMock()
    handler.send_header = MagicMock()
    handler.end_headers = MagicMock()

    handler.do_GET()

    handler.send_response.assert_called_with(200)
    output = handler.wfile.getvalue().decode("utf-8")
    assert "ok" in output
    assert "version" in output


def test_server_api_summary_endpoint():
    """Verify /api/summary returns KPI data."""
    handler = AirunServerHandler.__new__(AirunServerHandler)
    handler.path = "/api/summary"
    handler.rfile = io.BytesIO()
    handler.wfile = io.BytesIO()
    handler.headers = {}
    handler.command = "GET"

    handler.send_response = MagicMock()
    handler.send_header = MagicMock()
    handler.end_headers = MagicMock()

    handler.do_GET()

    handler.send_response.assert_called_with(200)
    output = handler.wfile.getvalue().decode("utf-8")
    assert "total_traces" in output
    assert "total_cost_usd" in output


def test_server_html_dashboard_endpoint():
    """Verify root / returns HTML dashboard."""
    handler = AirunServerHandler.__new__(AirunServerHandler)
    handler.path = "/"
    handler.rfile = io.BytesIO()
    handler.wfile = io.BytesIO()
    handler.headers = {}
    handler.command = "GET"

    handler.send_response = MagicMock()
    handler.send_header = MagicMock()
    handler.end_headers = MagicMock()

    handler.do_GET()

    handler.send_response.assert_called_with(200)
    output = handler.wfile.getvalue().decode("utf-8")
    assert "<!DOCTYPE html>" in output
    assert "AI Infrastructure Command Center" in output


def test_server_executive_metrics_endpoint():
    """Verify /api/metrics/executive returns command center metrics."""
    handler = AirunServerHandler.__new__(AirunServerHandler)
    handler.path = "/api/metrics/executive"
    handler.rfile = io.BytesIO()
    handler.wfile = io.BytesIO()
    handler.headers = {}
    handler.command = "GET"

    handler.send_response = MagicMock()
    handler.send_header = MagicMock()
    handler.end_headers = MagicMock()

    handler.do_GET()

    handler.send_response.assert_called_with(200)
    output = handler.wfile.getvalue().decode("utf-8")
    assert "compute_cost_usd" in output
    assert "energy_cost_usd" in output
    assert "gpu_utilization_pct" in output
    assert "top_problem" in output


def test_server_frontier_and_resilience_endpoints():
    """Verify /api/routing/frontier, /api/resilience/breaker, and /api/incidents/graph."""
    for ep in ("/api/routing/frontier", "/api/resilience/breaker", "/api/incidents/graph"):
        handler = AirunServerHandler.__new__(AirunServerHandler)
        handler.path = ep
        handler.rfile = io.BytesIO()
        handler.wfile = io.BytesIO()
        handler.headers = {}
        handler.command = "GET"

        handler.send_response = MagicMock()
        handler.send_header = MagicMock()
        handler.end_headers = MagicMock()

        handler.do_GET()
        handler.send_response.assert_called_with(200)
        output = handler.wfile.getvalue().decode("utf-8")
        assert len(output) > 10


def test_server_prometheus_metrics_endpoint():
    """Verify /metrics returns standard Prometheus plain text metrics."""
    handler = AirunServerHandler.__new__(AirunServerHandler)
    handler.path = "/metrics"
    handler.rfile = io.BytesIO()
    handler.wfile = io.BytesIO()
    handler.headers = {}
    handler.command = "GET"

    handler.send_response = MagicMock()
    handler.send_header = MagicMock()
    handler.end_headers = MagicMock()

    handler.do_GET()

    handler.send_response.assert_called_with(200)
    output = handler.wfile.getvalue().decode("utf-8")
    assert "# HELP airun_traces_total" in output
    assert "# TYPE airun_traces_total counter" in output
    assert "airun_cost_usd_total" in output
    assert "airun_tokens_total" in output
    assert "airun_circuit_breaker_state" in output


def test_server_otlp_ingestion_endpoint():
    """Verify POST /v1/traces parses OTLP payload and saves to store."""
    import json

    payload = {
        "resourceSpans": [
            {
                "scopeSpans": [
                    {
                        "spans": [
                            {
                                "traceId": "tr-otlp-server-test",
                                "spanId": "span-1",
                                "name": "llm_query",
                                "startTimeUnixNano": "1710000000000000000",
                                "endTimeUnixNano": "1710000000100000000",
                                "attributes": [
                                    {"key": "model", "value": {"stringValue": "gpt-4o-mini"}},
                                    {"key": "tokens.input", "value": {"intValue": 500}},
                                    {"key": "tokens.output", "value": {"intValue": 100}},
                                ],
                            }
                        ]
                    }
                ]
            }
        ]
    }

    body = json.dumps(payload).encode("utf-8")
    handler = AirunServerHandler.__new__(AirunServerHandler)
    handler.path = "/v1/traces"
    handler.rfile = io.BytesIO(body)
    handler.wfile = io.BytesIO()
    handler.headers = {"Content-Length": str(len(body))}
    handler.command = "POST"

    handler.send_response = MagicMock()
    handler.send_header = MagicMock()
    handler.end_headers = MagicMock()

    handler.do_POST()

    handler.send_response.assert_called_with(200)
    output = json.loads(handler.wfile.getvalue().decode("utf-8"))
    assert output["status"] == "success"
    assert "tr-otlp-server-test" in output["ingested"]


def test_server_live_sse_stream_endpoint():
    """Verify GET /api/live/stream returns SSE telemetry format."""
    handler = AirunServerHandler.__new__(AirunServerHandler)
    handler.path = "/api/live/stream"
    handler.rfile = io.BytesIO()
    handler.wfile = io.BytesIO()
    handler.headers = {}
    handler.command = "GET"

    handler.send_response = MagicMock()
    handler.send_header = MagicMock()
    handler.end_headers = MagicMock()

    handler.do_GET()

    handler.send_response.assert_called_with(200)
    output = handler.wfile.getvalue().decode("utf-8")
    assert output.startswith("data: ")
    assert "heartbeat" in output


def test_server_demo_seeding_endpoint():
    """Verify POST /api/demo seeds realistic example AI workloads."""
    import json

    handler = AirunServerHandler.__new__(AirunServerHandler)
    handler.path = "/api/demo"
    handler.rfile = io.BytesIO()
    handler.wfile = io.BytesIO()
    handler.headers = {}
    handler.command = "POST"

    handler.send_response = MagicMock()
    handler.send_header = MagicMock()
    handler.end_headers = MagicMock()

    handler.do_POST()

    handler.send_response.assert_called_with(200)
    output = json.loads(handler.wfile.getvalue().decode("utf-8"))
    assert output["status"] == "success"
    assert output["count"] == 4
    assert len(output["trace_ids"]) == 4
