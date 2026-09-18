from typer.testing import CliRunner

from airun.cli.main import app

runner = CliRunner()


def test_cli_policy_list():
    """Verify 'airun policy list' outputs remediation rules table."""
    result = runner.invoke(app, ["policy", "list"])
    assert result.exit_code == 0
    assert "Closed-Loop Remediation Rules" in result.output
    assert "excessive" in result.output
    assert "ENABLED" in result.output


def test_cli_policy_evaluate():
    """Verify 'airun policy evaluate' runs on a demo trace."""
    demo_res = runner.invoke(app, ["demo"])
    assert demo_res.exit_code == 0

    eval_res = runner.invoke(app, ["policy", "evaluate", "latest"])
    assert eval_res.exit_code == 0
    assert "Closed-Loop Remediation" in eval_res.output
