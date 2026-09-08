"""Integration tests for CLI hardware waste and workload economics commands."""

from __future__ import annotations

from typer.testing import CliRunner

from airun.cli.main import app
from airun.events.models import SpanKind, TraceRecord, TraceSpan
from airun.store import get_trace_store

runner = CliRunner()


def test_cli_waste_workload() -> None:
    result = runner.invoke(app, ["waste", "--workload", "customer-support-agent"])
    assert result.exit_code == 0
    assert "Airun Workload Economics & Optimization Report" in result.stdout
    assert "customer-support-agent" in result.stdout
    assert "Monthly Spend" in result.stdout
    assert "Potential Waste" in result.stdout
    assert "Route 73% of requests to cheaper model" in result.stdout


def test_cli_waste_hardware() -> None:
    store = get_trace_store()
    spans = [
        TraceSpan(
            trace_id="trace-hw-test",
            span_id="s1",
            name="dataloader_fetch",
            kind=SpanKind.AGENT_STEP,
            start_time="1700000000.0",
            end_time="1700000001.0",
            duration_ms=1000.0,
            cost_usd=0.01,
        )
    ]
    record = TraceRecord(trace_id="trace-hw-test", created_at="2026-09-07T00:00:00Z", spans=spans)
    store.save_trace(record)

    result = runner.invoke(app, ["waste", "trace-hw-test", "--hardware", "--accelerator", "h100", "--gpus", "8"])
    assert result.exit_code == 0
    assert "HARDWARE WASTE DETECTED IN TRACE" in result.stdout
    assert "Financial Bleed" in result.stdout
    assert "Actionable Fix" in result.stdout
