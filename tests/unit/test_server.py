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
