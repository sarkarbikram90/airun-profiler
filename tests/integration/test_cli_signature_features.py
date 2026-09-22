"""Integration tests for signature CLI commands: diagnose, money-leak, bench, and agent analyze."""

from typer.testing import CliRunner

from airun.cli.main import app

runner = CliRunner()


def test_cli_diagnose_command():
    """Verify 'airun diagnose' command."""
    result = runner.invoke(app, ["diagnose", "demo"])
    assert result.exit_code == 0
    assert "DIAGNOSTIC" in result.output
    assert "GPU Efficiency:" in result.output
    assert "ROOT CAUSE" in result.output


def test_cli_diagnose_json():
    """Verify 'airun diagnose --json' outputs valid parseable structure."""
    result = runner.invoke(app, ["diagnose", "demo", "--json"])
    assert result.exit_code == 0
    assert '"trace_id":' in result.output
    assert '"gpu_efficiency":' in result.output
    assert '"root_cause":' in result.output


def test_cli_money_leak_command(tmp_path):
    """Verify 'airun money-leak' and HTML export."""
    result = runner.invoke(app, ["money-leak"])
    assert result.exit_code == 0
    assert "AIRUN MONEY LEAK" in result.output
    assert "Monthly" in result.output
    assert "Recoverable Waste" in result.output
    assert "GPU starvation" in result.output

    # Test HTML export
    report_file = tmp_path / "report.html"
    result_export = runner.invoke(app, ["money-leak", "--export", str(report_file)])
    assert result_export.exit_code == 0
    assert report_file.exists()
    content = report_file.read_text(encoding="utf-8")
    assert "<!DOCTYPE html>" in content
    assert "AIRUN MONEY LEAK AUDIT REPORT" in content


def test_cli_money_leak_json():
    """Verify 'airun money-leak --json' output."""
    result = runner.invoke(app, ["money-leak", "--json"])
    assert result.exit_code == 0
    assert '"monthly_spend_usd":' in result.output
    assert '"recoverable_waste_usd":' in result.output
    assert '"top_leaks":' in result.output


def test_cli_bench_command():
    """Verify 'airun bench' command."""
    result = runner.invoke(app, ["bench", "--model", "qwen3-8b", "--gpu", "l4"])
    assert result.exit_code == 0
    assert "AIRUN BENCHMARK" in result.output
    assert "vLLM" in result.output
    assert "SGLang" in result.output


def test_cli_bench_json():
    """Verify 'airun bench --json' output."""
    result = runner.invoke(app, ["bench", "--json"])
    assert result.exit_code == 0
    assert '"model":' in result.output
    assert '"results":' in result.output
    assert '"winner_throughput":' in result.output


def test_cli_agent_analyze_command():
    """Verify 'airun agent analyze' command."""
    result = runner.invoke(app, ["agent", "analyze"])
    assert result.exit_code == 0
    assert "AGENT EFFICIENCY REPORT" in result.output
    assert "Top findings" in result.output


def test_cli_agent_analyze_json():
    """Verify 'airun agent analyze --json' output."""
    result = runner.invoke(app, ["agent", "analyze", "--json"])
    assert result.exit_code == 0
    assert '"trace_id":' in result.output
    assert '"redundant_cost_pct":' in result.output
    assert '"findings":' in result.output
