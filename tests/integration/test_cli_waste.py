"""Integration tests for the waste detection and golden-signals CLI commands."""

from __future__ import annotations

from typer.testing import CliRunner

from airun.cli.main import app

runner = CliRunner()


def test_cli_waste_command():
    """Verify 'airun waste' command runs and renders report."""
    # Ensure at least one trace exists
    runner.invoke(app, ["demo"])

    result = runner.invoke(app, ["waste", "latest", "--accelerator", "h100", "--gpus", "8"])
    assert result.exit_code == 0
    assert "Physics of AI Waste" in result.output
    assert "Hourly Financial Bleed" in result.output
    assert "FinOps Remediation" in result.output


def test_cli_golden_signals_command():
    """Verify 'airun golden-signals' command runs and renders 4 layers."""
    runner.invoke(app, ["demo"])

    result = runner.invoke(app, ["golden-signals", "latest"])
    assert result.exit_code == 0
    assert "Golden Signals Hierarchy" in result.output
    assert "Economics (CFO View)" in result.output
    assert "Efficiency (ML Engineer View)" in result.output
    assert "Reliability (Platform View)" in result.output
    assert "Infrastructure (Physical Layer)" in result.output


def test_cli_profiler_trace_command():
    """Verify 'airun profiler trace --pid <pid>' runs and displays GTM upsell."""
    result = runner.invoke(
        app,
        [
            "profiler",
            "trace",
            "--pid",
            "12345",
            "--duration",
            "2.5",
            "--accelerator",
            "h100",
            "--gpus",
            "8",
        ],
    )
    assert result.exit_code == 0
    assert "Airun Open-Source Profiler Trace Output" in result.output
    assert "PID 12345" in result.output
    assert "Airun Cloud ROI Assessment" in result.output
    assert "https://airun.dev/cloud" in result.output
