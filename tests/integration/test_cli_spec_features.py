"""Integration tests for SPECIFICATION.md CLI commands: metrics, frontier, dr drill, breaker status."""

from typer.testing import CliRunner

from airun.cli.main import app

runner = CliRunner()


def test_cli_frontier_command():
    """Verify 'airun frontier' output."""
    result = runner.invoke(app, ["frontier"])
    assert result.exit_code == 0
    assert "Efficient Frontier" in result.output
    assert "Claude" in result.output
    assert "GPT-4o" in result.output
    assert "PARETO" in result.output
    assert "OPTIMAL" in result.output


def test_cli_dr_drill_command():
    """Verify 'airun dr drill' command."""
    result = runner.invoke(app, ["dr", "drill", "--primary", "openai", "--fallback", "anthropic"])
    assert result.exit_code == 0
    assert "Disaster Recovery" in result.output
    assert "CONTINUITY PRESERVED" in result.output


def test_cli_breaker_status_command():
    """Verify 'airun breaker status' command."""
    result = runner.invoke(app, ["breaker", "status"])
    assert result.exit_code == 0
    assert "The AI Breaker Box" in result.output
    assert "OPENAI" in result.output
    assert "CLOSED" in result.output
    assert "HEALTHY" in result.output


def test_cli_metrics_command():
    """Verify 'airun metrics' on demo trace."""
    # First ensure a demo trace exists
    runner.invoke(app, ["demo"])
    result = runner.invoke(app, ["metrics", "latest"])
    assert result.exit_code == 0
    assert "AI Infrastructure Executive Economics" in result.output
    assert "Compute Cost" in result.output
    assert "Energy Cost" in result.output
