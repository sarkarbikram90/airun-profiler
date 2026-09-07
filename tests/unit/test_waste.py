"""Unit tests for the Physics of AI Waste engine and MFU calculator."""

from __future__ import annotations

from airun.analysis.waste import (
    WasteCategory,
    WasteSeverity,
    calculate_mfu,
    detect_compute_waste,
)


def test_calculate_mfu_inference():
    """Verify MFU calculation for LLM inference (2 * params * tokens)."""
    # 70B parameter model, 10,000 tokens, 1000ms duration on single H100
    report = calculate_mfu(
        tokens_processed=10_000,
        model_params_billions=70.0,
        duration_ms=1000.0,
        accelerator="h100",
        num_accelerators=1,
        is_training=False,
    )

    assert report.accelerator_name == "NVIDIA H100 SXM5"
    assert report.theoretical_peak_tflops_per_device == 989.0
    assert report.total_theoretical_peak_tflops == 989.0
    # Total FLOPs = 2 * 70e9 * 10,000 = 1.4e15 FLOPs = 1400 TFLOPs in 1.0s -> 1400 TFLOPS
    assert report.achieved_tflops > 0.0
    assert report.efficiency_rating in ("Optimal", "Moderate", "Critical Waste")


def test_calculate_mfu_training():
    """Verify MFU calculation for LLM training (6 * params * tokens)."""
    # 7B parameter model, 50,000 tokens, 5000ms on 8x H100
    report = calculate_mfu(
        tokens_processed=50_000,
        model_params_billions=7.0,
        duration_ms=5000.0,
        accelerator="h100",
        num_accelerators=8,
        is_training=True,
    )

    assert report.num_accelerators == 8
    assert report.total_theoretical_peak_tflops == 989.0 * 8
    assert report.is_training is True
    assert 0.0 <= report.mfu_pct <= 100.0


def test_detect_compute_waste_dataloader_starvation():
    """Verify detection of Dataloader Starvation when SM cycles drop and PCIe is idle."""
    samples = [
        {
            "sm_util_pct": 35.0,
            "pcie_throughput_mb": 150.0,
            "nccl_wait_ms": 5.0,
            "cpu_util_pct": 90.0,
        },
        {
            "sm_util_pct": 40.0,
            "pcie_throughput_mb": 200.0,
            "nccl_wait_ms": 8.0,
            "cpu_util_pct": 88.0,
        },
    ]

    report = detect_compute_waste(
        telemetry_samples=samples,
        accelerator="h100",
        num_gpus=8,
        duration_ms=60_000.0,  # 1 minute
        total_cost_usd=0.466,  # 8 * $3.50 * (1/60)
        workload_id="training-run-starve",
    )

    categories = [c.category for c in report.waste_components]
    assert WasteCategory.DATALOADER_STARVATION in categories
    assert report.total_waste_pct > 0.0
    assert report.hourly_financial_bleed_usd > 0.0
    assert "DataLoader" in report.recommendations[0]["action"]


def test_detect_compute_waste_nccl_overhead():
    """Verify detection of NCCL All-Reduce gradient synchronization stalls."""
    samples = [
        {
            "sm_util_pct": 80.0,
            "pcie_throughput_mb": 2500.0,
            "nccl_wait_ms": 110.0,
            "cpu_util_pct": 30.0,
        },
        {
            "sm_util_pct": 75.0,
            "pcie_throughput_mb": 2200.0,
            "nccl_wait_ms": 95.0,
            "cpu_util_pct": 32.0,
        },
    ]

    report = detect_compute_waste(
        telemetry_samples=samples,
        accelerator="h100",
        num_gpus=8,
        duration_ms=120_000.0,
        workload_id="training-allreduce-stall",
    )

    categories = [c.category for c in report.waste_components]
    assert WasteCategory.NCCL_OVERHEAD in categories
    nccl_comp = next(
        c for c in report.waste_components if c.category == WasteCategory.NCCL_OVERHEAD
    )
    assert nccl_comp.severity in (WasteSeverity.HIGH, WasteSeverity.CRITICAL)
    assert "NCCL" in nccl_comp.remediation


def test_detect_compute_waste_pcie_bottleneck():
    """Verify detection of PCIe bus saturation with low kernel compute."""
    samples = [
        {
            "sm_util_pct": 45.0,
            "pcie_throughput_mb": 18000.0,
            "nccl_wait_ms": 10.0,
            "cpu_util_pct": 40.0,
        },
    ]

    report = detect_compute_waste(
        telemetry_samples=samples,
        accelerator="h100_pcie",
        num_gpus=1,
        duration_ms=30_000.0,
    )

    categories = [c.category for c in report.waste_components]
    assert WasteCategory.PCIE_BOTTLENECK in categories


def test_detect_compute_waste_framework_overhead():
    """Verify detection of PyTorch eager mode host Python dispatch latency."""
    samples = [
        {
            "sm_util_pct": 60.0,
            "pcie_throughput_mb": 800.0,
            "nccl_wait_ms": 10.0,
            "cpu_util_pct": 85.0,
            "eager_overhead_pct": 18.0,
        },
    ]

    report = detect_compute_waste(
        telemetry_samples=samples,
        accelerator="a100",
        num_gpus=4,
        duration_ms=60_000.0,
    )

    categories = [c.category for c in report.waste_components]
    assert WasteCategory.FRAMEWORK_OVERHEAD in categories
    fw_comp = next(
        c for c in report.waste_components if c.category == WasteCategory.FRAMEWORK_OVERHEAD
    )
    assert "torch.compile" in fw_comp.remediation


def test_financial_bleed_and_recommendations():
    """Verify dollar burn rate, bleed, and actionable recommendations with ROI."""
    report = detect_compute_waste(
        accelerator="h100",
        num_gpus=8,
        duration_ms=3_600_000.0,  # 1 hour
        total_cost_usd=28.0,  # 8 * $3.50
        tokens_processed=100_000,
        model_params_billions=7.0,
    )

    assert report.hourly_burn_rate_usd == 28.0
    assert report.total_cost_usd == 28.0
    assert report.hourly_financial_bleed_usd >= 0.0
    assert len(report.recommendations) > 0
    assert report.recommendations[0]["potential_weekly_savings_usd"] >= 0.0
    assert report.recommendations[0]["potential_monthly_savings_usd"] >= 0.0
