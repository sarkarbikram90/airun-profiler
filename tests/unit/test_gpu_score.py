"""Tests for GPU Efficiency Scoring engine."""

from airun.analysis.gpu_score import calculate_gpu_efficiency_score


def test_gpu_efficiency_score_optimal():
    score = calculate_gpu_efficiency_score(
        accelerator="h100",
        sm_util_pct=92.0,
        memory_bandwidth_pct=88.0,
        mfu_pct=72.0,
        pcie_util_pct=50.0,
    )
    assert 75 <= score.score <= 100
    assert score.rating in ("GOOD", "EXCELLENT")
    assert "Optimal" in score.primary_bottleneck or "Balanced" in score.primary_bottleneck
    assert "100" in score.ascii_bar


def test_gpu_efficiency_score_dataloader_starvation():
    score = calculate_gpu_efficiency_score(
        accelerator="h100",
        sm_util_pct=34.0,
        memory_bandwidth_pct=30.0,
        mfu_pct=25.0,
        pcie_util_pct=8.0,
    )
    assert score.score < 55
    assert "DataLoader starvation" in score.primary_bottleneck
    assert score.potential_throughput_gain_pct > 20.0
    assert len(score.recommendations) > 0


def test_gpu_efficiency_score_thermal_throttling_penalty():
    score_normal = calculate_gpu_efficiency_score(
        accelerator="a100",
        sm_util_pct=75.0,
        memory_bandwidth_pct=70.0,
        thermal_throttling=False,
    )
    score_throttled = calculate_gpu_efficiency_score(
        accelerator="a100",
        sm_util_pct=75.0,
        memory_bandwidth_pct=70.0,
        thermal_throttling=True,
    )
    assert score_throttled.score < score_normal.score
    assert "Thermal throttling" in score_throttled.primary_bottleneck


def test_gpu_efficiency_score_to_dict():
    score = calculate_gpu_efficiency_score(accelerator="l4", sm_util_pct=60.0)
    d = score.to_dict()
    assert "score" in d
    assert "rating" in d
    assert "ascii_bar" in d
    assert d["accelerator"] == "L4"
