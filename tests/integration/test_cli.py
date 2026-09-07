"""Integration tests for CLI commands."""

from pathlib import Path

import pytest
from typer.testing import CliRunner

from airun.cli.main import app
from airun.events.models import SpanKind
from airun.sdk.tracer import trace

runner = CliRunner()


def test_cli_init_command(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.chdir(tmp_path)
    result = runner.invoke(app, ["init"])
    assert result.exit_code == 0
    assert "airun initialized successfully" in result.stdout
    assert (tmp_path / ".airun" / "config.yaml").exists()
    assert (tmp_path / ".airun" / "pricing.yaml").exists()


def test_cli_demo_command(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.chdir(tmp_path)
    result = runner.invoke(app, ["demo"])
    assert result.exit_code == 0
    assert "Demo workflow completed successfully" in result.stdout
    assert "AI Workflow Runtime Summary" in result.stdout


def test_cli_doctor_command(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.chdir(tmp_path)
    result = runner.invoke(app, ["doctor"])
    assert result.exit_code == 0
    assert "airun System Doctor" in result.stdout
    assert "Trace Store" in result.stdout
    assert "SDK Micro-Overhead" in result.stdout


def test_cli_trace_commands_and_report(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.chdir(tmp_path)
    # Generate a trace
    with trace("cli_test_workflow", kind=SpanKind.WORKFLOW) as root:
        with trace("step_one", kind=SpanKind.LLM, model="gpt-4o-mini"):
            pass

    trace_id = root.trace_id

    # Test trace list
    res_list = runner.invoke(app, ["trace", "list"])
    assert res_list.exit_code == 0
    assert (trace_id[:8] in res_list.stdout) or ("cli_test" in res_list.stdout)

    # Test trace show
    res_show = runner.invoke(app, ["trace", "show", trace_id])
    assert res_show.exit_code == 0
    assert "step_one" in res_show.stdout

    # Test report with exact ID
    res_rep = runner.invoke(app, ["report", trace_id])
    assert res_rep.exit_code == 0
    assert "AI Workflow Runtime Summary" in res_rep.stdout

    # Test report with 'latest' alias
    res_latest = runner.invoke(app, ["report", "latest"])
    assert res_latest.exit_code == 0
    assert "AI Workflow Runtime Summary" in res_latest.stdout

    # Test export JSON
    res_exp_json = runner.invoke(app, ["export", trace_id, "--format", "json"])
    assert res_exp_json.exit_code == 0
    assert trace_id in res_exp_json.stdout

    # Test export OTel JSON
    res_exp_otel = runner.invoke(app, ["export", trace_id, "--format", "otel-json"])
    assert res_exp_otel.exit_code == 0
    assert "resourceSpans" in res_exp_otel.stdout


def test_cli_compare_command(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.chdir(tmp_path)
    with trace("workflow_run_a", kind=SpanKind.WORKFLOW):
        with trace("step", kind=SpanKind.LLM, model="gpt-4"):
            pass

    with trace("workflow_run_b", kind=SpanKind.WORKFLOW):
        with trace("step", kind=SpanKind.LLM, model="gpt-4o-mini"):
            pass

    # Test comparison using previous and latest aliases
    res_comp = runner.invoke(app, ["compare", "previous", "latest"])
    assert res_comp.exit_code == 0
    assert "Trace Comparison" in res_comp.stdout
    assert "Total Cost" in res_comp.stdout


def test_cli_run_with_trace_id_file(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.chdir(tmp_path)
    # Create a small script that runs a traced workflow
    script_path = tmp_path / "mock_job.py"
    script_path.write_text(
        "from airun import trace, SpanKind\n"
        "with trace('cli_mock_job', kind=SpanKind.WORKFLOW):\n"
        "    pass\n",
        encoding="utf-8",
    )
    trace_id_file = tmp_path / "trace_id.txt"

    res_run = runner.invoke(app, ["run", str(script_path), "--trace-id-file", str(trace_id_file)])
    assert res_run.exit_code == 0
    assert trace_id_file.exists()
    saved_id = trace_id_file.read_text(encoding="utf-8").strip()
    assert len(saved_id) == 32
