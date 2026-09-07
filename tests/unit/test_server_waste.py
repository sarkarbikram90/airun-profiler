"""Unit tests for the server waste and golden-signals REST API endpoints."""

import io
from unittest.mock import MagicMock

from airun.server import AirunServerHandler


def _setup_mock_handler(path: str) -> AirunServerHandler:
    handler = AirunServerHandler.__new__(AirunServerHandler)
    handler.path = path
    handler.rfile = io.BytesIO()
    handler.wfile = io.BytesIO()
    handler.headers = {}
    handler.command = "GET"
    handler.send_response = MagicMock()
    handler.send_header = MagicMock()
    handler.end_headers = MagicMock()
    return handler


def test_server_api_waste_endpoint():
    """Verify /api/waste returns waste breakdown and financial bleed."""
    handler = _setup_mock_handler("/api/waste?accelerator=h100&gpus=8")
    handler.do_GET()

    handler.send_response.assert_called_with(200)
    output = handler.wfile.getvalue().decode("utf-8")
    assert "hourly_financial_bleed_usd" in output
    assert "waste_components" in output
    assert "top_bottleneck" in output


def test_server_api_golden_signals_endpoint():
    """Verify /api/golden-signals returns 4-layer signals."""
    handler = _setup_mock_handler("/api/golden-signals")
    handler.do_GET()

    handler.send_response.assert_called_with(200)
    output = handler.wfile.getvalue().decode("utf-8")
    assert "economics" in output
    assert "efficiency" in output
    assert "reliability" in output
    assert "infrastructure" in output


def test_server_api_recommendations_endpoint():
    """Verify /api/recommendations returns actionable FinOps list."""
    handler = _setup_mock_handler("/api/recommendations")
    handler.do_GET()

    handler.send_response.assert_called_with(200)
    output = handler.wfile.getvalue().decode("utf-8")
    assert "potential_weekly_savings_usd" in output


def test_server_api_daemonset_manifest_endpoint():
    """Verify /api/manifests/daemonset returns Kubernetes YAML."""
    handler = _setup_mock_handler("/api/manifests/daemonset")
    handler.do_GET()

    handler.send_response.assert_called_with(200)
    output = handler.wfile.getvalue().decode("utf-8")
    assert "daemonset-agent.yaml" in output
    assert "DaemonSet" in output
