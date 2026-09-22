"""Sensitivity analysis and canonical workload tests for GPU Efficiency Score.

Verifies mathematical linearity, sensitivity derivatives, penalty bounds, and
the 6 canonical AI workload profiles:
1. Compute-bound (Dense Matrix Multiplication / Training GEMM)
2. Memory-bound decode (LLM Autoregressive Generation)
3. Communication-bound (Distributed AllReduce / NCCL fabric stall)
4. DataLoader-starved (Host CPU/IO pipeline bottleneck)
5. Mixed inference (Continuous batching prefill + decode)
6. Idle / severely starved accelerator
"""

from airun.analysis.gpu_score import calculate_gpu_efficiency_score


class TestGPUEfficiencyScoreWorkloads:
    """Verify classification and tiering across the 6 canonical workload profiles."""

    def test_workload_1_compute_bound_training(self):
        """Workload 1: Dense GEMM / Training Prefill (High SM, High MemBW, High MFU)."""
        score = calculate_gpu_efficiency_score(
            accelerator="h100",
            sm_util_pct=95.0,
            memory_bandwidth_pct=92.0,
            mfu_pct=80.0,
            pcie_util_pct=70.0,
        )
        assert score.rating == "EXCELLENT"
        assert score.score >= 85
        assert "Optimal" in score.primary_bottleneck or "Balanced" in score.primary_bottleneck
        assert score.deductions == 0.0

    def test_workload_2_memory_bound_llm_decode(self):
        """Workload 2: LLM autoregressive token decode (Moderate SM, Saturated MemBW)."""
        score = calculate_gpu_efficiency_score(
            accelerator="h100",
            sm_util_pct=52.0,
            memory_bandwidth_pct=88.0,
            mfu_pct=30.0,
            pcie_util_pct=35.0,
        )
        assert score.rating in ("SUBOPTIMAL", "GOOD")
        assert score.primary_bottleneck == "Memory bandwidth bound (VRAM bus saturated)"
        assert any("FlashAttention" in r or "quantization" in r for r in score.recommendations)

    def test_workload_3_communication_bound_nccl(self):
        """Workload 3: Multi-node AllReduce barrier stall."""
        score = calculate_gpu_efficiency_score(
            accelerator="h100",
            sm_util_pct=38.0,
            memory_bandwidth_pct=32.0,
            mfu_pct=25.0,
            pcie_util_pct=15.0,
            nccl_stall_ms=50.0,
        )
        assert score.rating == "CRITICAL_WASTE"
        assert score.primary_bottleneck == "Distributed AllReduce / NCCL fabric stall"
        assert score.deductions > 0.0
        assert any("NCCL_BUFFSIZE" in r for r in score.recommendations)

    def test_workload_4_dataloader_starved(self):
        """Workload 4: Host CPU DataLoader starvation."""
        score = calculate_gpu_efficiency_score(
            accelerator="h100",
            sm_util_pct=24.0,
            memory_bandwidth_pct=20.0,
            mfu_pct=15.0,
            pcie_util_pct=10.0,
        )
        assert score.rating == "CRITICAL_WASTE"
        assert score.primary_bottleneck == "Host DataLoader starvation (CPU/IO Bound)"
        assert any("DataLoader workers" in r for r in score.recommendations)

    def test_workload_5_mixed_inference_balanced(self):
        """Workload 5: Well-tuned mixed inference serving with continuous batching."""
        score = calculate_gpu_efficiency_score(
            accelerator="l4",
            sm_util_pct=80.0,
            memory_bandwidth_pct=80.0,
            mfu_pct=60.0,
            pcie_util_pct=50.0,
        )
        assert score.rating == "GOOD"
        assert 70 <= score.score <= 84
        assert score.deductions == 0.0

    def test_workload_6_idle_accelerator(self):
        """Workload 6: Idle or unallocated GPU."""
        score = calculate_gpu_efficiency_score(
            accelerator="a100",
            sm_util_pct=2.0,
            memory_bandwidth_pct=3.0,
            mfu_pct=1.0,
            pcie_util_pct=1.0,
        )
        assert score.rating == "CRITICAL_WASTE"
        assert score.score <= 15
        assert score.score >= 5  # Clamped minimum


class TestGPUEfficiencyScoreSensitivity:
    """Verify partial derivatives and sensitivity response of individual dimensions."""

    def test_sm_utilization_sensitivity_slope(self):
        """Varying SM utilization must reflect a 0.35 sensitivity slope."""
        low = calculate_gpu_efficiency_score(
            accelerator="h100", sm_util_pct=20.0, memory_bandwidth_pct=50.0, mfu_pct=40.0, pcie_util_pct=30.0
        )
        high = calculate_gpu_efficiency_score(
            accelerator="h100", sm_util_pct=80.0, memory_bandwidth_pct=50.0, mfu_pct=40.0, pcie_util_pct=30.0
        )
        # Expected delta = 60 * 0.35 = 21.0
        delta = high.score - low.score
        assert abs(delta - 21) <= 1

    def test_memory_bandwidth_sensitivity_slope(self):
        """Varying Memory Bandwidth must reflect a 0.30 sensitivity slope."""
        low = calculate_gpu_efficiency_score(
            accelerator="h100", sm_util_pct=60.0, memory_bandwidth_pct=20.0, mfu_pct=40.0, pcie_util_pct=30.0
        )
        high = calculate_gpu_efficiency_score(
            accelerator="h100", sm_util_pct=60.0, memory_bandwidth_pct=80.0, mfu_pct=40.0, pcie_util_pct=30.0
        )
        # Expected delta = 60 * 0.30 = 18.0
        delta = high.score - low.score
        assert abs(delta - 18) <= 1

    def test_thermal_penalty_exact_deduction(self):
        """Thermal throttling must deduct exactly 15 points and set bottleneck."""
        normal = calculate_gpu_efficiency_score(
            accelerator="h100", sm_util_pct=80.0, memory_bandwidth_pct=80.0, mfu_pct=50.0, pcie_util_pct=40.0,
            thermal_throttling=False
        )
        throttled = calculate_gpu_efficiency_score(
            accelerator="h100", sm_util_pct=80.0, memory_bandwidth_pct=80.0, mfu_pct=50.0, pcie_util_pct=40.0,
            thermal_throttling=True
        )
        assert throttled.deductions == 15.0
        assert normal.score - throttled.score == 15
        assert "Thermal throttling" in throttled.primary_bottleneck

    def test_pcie_errors_penalty_capping(self):
        """PCIe errors deduct 3 points each, capped at 15 points."""
        single_err = calculate_gpu_efficiency_score(
            accelerator="h100", sm_util_pct=70.0, memory_bandwidth_pct=70.0, mfu_pct=50.0, pcie_util_pct=40.0,
            pcie_errors=2
        )
        assert single_err.deductions == 6.0

        many_err = calculate_gpu_efficiency_score(
            accelerator="h100", sm_util_pct=70.0, memory_bandwidth_pct=70.0, mfu_pct=50.0, pcie_util_pct=40.0,
            pcie_errors=10
        )
        assert many_err.deductions == 15.0  # Capped at 15

    def test_clamping_bounds(self):
        """Score must never exceed 100 or drop below 5."""
        overclock = calculate_gpu_efficiency_score(
            accelerator="h100", sm_util_pct=150.0, memory_bandwidth_pct=150.0, mfu_pct=120.0, pcie_util_pct=150.0
        )
        assert overclock.score == 100

        total_failure = calculate_gpu_efficiency_score(
            accelerator="h100", sm_util_pct=0.0, memory_bandwidth_pct=0.0, mfu_pct=0.0, pcie_util_pct=0.0,
            thermal_throttling=True, pcie_errors=10, nccl_stall_ms=500.0
        )
        assert total_failure.score == 5
