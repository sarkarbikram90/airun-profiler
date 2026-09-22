from typer.testing import CliRunner

from airun.cli.main import app

runner = CliRunner(env={"COLUMNS": "160"})


def test_cli_cluster_list():
    """Verify 'airun cluster list' outputs federated clusters across clouds."""
    result = runner.invoke(app, ["cluster", "list"])
    assert result.exit_code == 0
    assert "Airun Multi-Cluster Cross-Cloud Federation" in result.output
    assert "gke-us-central1-h100" in result.output
    assert "eks-us-east-1-h100" in result.output
    assert "aks-westus3-a100" in result.output
    assert "onprem-dgx-h100" in result.output


def test_cli_cluster_list_with_provider_filter():
    """Verify 'airun cluster list --provider gcp' only lists GCP clusters."""
    result = runner.invoke(app, ["cluster", "list", "--provider", "gcp"])
    assert result.exit_code == 0
    assert "gke-us-central1-h100" in result.output
    assert "eks-us-east-1-h100" not in result.output
    assert "aks-westus3-a100" not in result.output


def test_cli_cluster_list_with_accelerator_filter():
    """Verify 'airun cluster list --accelerator a100' only lists A100 clusters."""
    result = runner.invoke(app, ["cluster", "list", "--accelerator", "a100"])
    assert result.exit_code == 0
    assert "aks-westus3-a100" in result.output
    assert "gke-us-central1-h100" not in result.output


def test_cli_cluster_overview():
    """Verify 'airun cluster overview' displays global capacity and spend."""
    result = runner.invoke(app, ["cluster", "overview"])
    assert result.exit_code == 0
    assert "Global Multi-Cloud Federation Overview" in result.output
    assert "Global GPU Footprint" in result.output
    assert "Aggregate Hourly Spend" in result.output
    assert "Aggregate Financial Bleed" in result.output
    assert "Global Average MFU" in result.output


def test_cli_cluster_recommend():
    """Verify 'airun cluster recommend' recommends optimal cluster placement."""
    result = runner.invoke(
        app,
        ["cluster", "recommend", "llama3-70b-train", "--gpus", "8", "--accelerator", "h100"],
    )
    assert result.exit_code == 0
    assert "Airun Intelligent Workload Placement" in result.output
    assert "llama3-70b-train" in result.output
    assert "Recommended Cluster" in result.output
    assert "Hourly Rate / GPU" in result.output
    assert "Expected MFU" in result.output
    assert "MFU/Dollar Score" in result.output
