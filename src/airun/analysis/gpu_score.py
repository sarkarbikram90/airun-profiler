"""GPU Efficiency Scoring Engine for AI Workloads.

Calculates an opinionated, physically-grounded 0-100 efficiency score across
modern AI accelerators (NVIDIA H100 SXM/PCIe, A100, L4, B200, TPU v5e) by
synthesizing SM active cycles, memory bandwidth saturation, MFU, and bus transfers.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, Optional


@dataclass
class GPUEfficiencyScore:
    """Standardized 0-100 GPU Efficiency Score with bottleneck attribution."""

    score: int  # 0 to 100
    accelerator: str
    gpu_id: int = 0
    primary_bottleneck: str = "Optimal compute utilization"
    potential_throughput_gain_pct: float = 0.0
    cost_savings_per_1k_tokens_usd: float = 0.0
    subscores: Dict[str, float] = field(default_factory=dict)
    recommendations: list[str] = field(default_factory=list)

    @property
    def ascii_bar(self) -> str:
        """Render a 20-character visual progress bar."""
        filled = int(round(self.score / 5.0))
        empty = 20 - filled
        return f"[{'#' * filled}{'-' * empty}] {self.score}/100"

    @property
    def rating(self) -> str:
        if self.score >= 85:
            return "EXCELLENT"
        elif self.score >= 70:
            return "GOOD"
        elif self.score >= 50:
            return "SUBOPTIMAL"
        else:
            return "CRITICAL_WASTE"

    def to_dict(self) -> dict[str, Any]:
        return {
            "score": self.score,
            "rating": self.rating,
            "accelerator": self.accelerator,
            "gpu_id": self.gpu_id,
            "primary_bottleneck": self.primary_bottleneck,
            "potential_throughput_gain_pct": self.potential_throughput_gain_pct,
            "cost_savings_per_1k_tokens_usd": self.cost_savings_per_1k_tokens_usd,
            "ascii_bar": self.ascii_bar,
            "subscores": self.subscores,
            "recommendations": self.recommendations,
        }


def calculate_gpu_efficiency_score(
    accelerator: str = "h100",
    gpu_id: int = 0,
    sm_util_pct: float = 50.0,
    memory_bandwidth_pct: float = 50.0,
    mfu_pct: Optional[float] = None,
    pcie_util_pct: float = 30.0,
    thermal_throttling: bool = False,
    pcie_errors: int = 0,
    nccl_stall_ms: float = 0.0,
    cost_per_1m_tokens_usd: float = 2.50,
) -> GPUEfficiencyScore:
    """Compute the standardized 0-100 GPU Efficiency Score.

    Weight distribution:
    - Streaming Multiprocessor (SM) utilization: 35%
    - Memory Bandwidth utilization: 30%
    - Model FLOPs Utilization (MFU) normalized: 20%
    - Host-to-Device Bus transfer efficiency: 15%
    """
    accel_clean = accelerator.lower().strip()
    norm_mfu = mfu_pct if mfu_pct is not None else (sm_util_pct * 0.75)

    # Base weighted calculation
    w_sm = 0.35
    w_mem = 0.30
    w_mfu = 0.20
    w_bus = 0.15

    raw_score = (
        (min(100.0, max(0.0, sm_util_pct)) * w_sm)
        + (min(100.0, max(0.0, memory_bandwidth_pct)) * w_mem)
        + (min(100.0, max(0.0, norm_mfu)) * w_mfu)
        + (min(100.0, max(0.0, pcie_util_pct)) * w_bus)
    )

    # Deductions for physical silicon anomalies
    deductions = 0.0
    if thermal_throttling:
        deductions += 15.0
    if pcie_errors > 0:
        deductions += min(15.0, pcie_errors * 3.0)
    if nccl_stall_ms > 20.0:
        deductions += min(15.0, (nccl_stall_ms - 20.0) * 0.5)

    final_score = int(round(max(5.0, min(100.0, raw_score - deductions))))

    # Determine primary bottleneck and actionable gains
    recommendations: list[str] = []
    primary_bottleneck = "Balanced execution profile"
    gain_pct = 0.0

    if thermal_throttling:
        primary_bottleneck = "Thermal throttling (silicon clocks capped)"
        gain_pct = 25.0
        recommendations.append("Inspect chassis fans and GPU power limits (nvidia-smi -pl)")
    elif nccl_stall_ms > 30.0:
        primary_bottleneck = "Distributed AllReduce / NCCL fabric stall"
        gain_pct = min(40.0, nccl_stall_ms * 0.8)
        recommendations.append("Tune NCCL_BUFFSIZE=16MB and check InfiniBand PFC pause frames")
    elif sm_util_pct < 45.0 and pcie_util_pct < 20.0:
        primary_bottleneck = "Host DataLoader starvation (CPU/IO Bound)"
        gain_pct = round((75.0 - sm_util_pct) * 0.8, 1)
        recommendations.append(
            "Increase DataLoader workers, set pin_memory=True, and prefetch tensors"
        )
    elif memory_bandwidth_pct > 80.0 and sm_util_pct < 60.0:
        primary_bottleneck = "Memory bandwidth bound (VRAM bus saturated)"
        gain_pct = 19.0
        recommendations.append(
            "Apply FlashAttention-3 kernel fusion or weight quantization (FP8/INT4)"
        )
    elif sm_util_pct < 50.0:
        primary_bottleneck = "Small batch size / compute starvation"
        gain_pct = round((80.0 - sm_util_pct) * 0.7, 1)
        recommendations.append("Increase batch size or implement continuous/dynamic batching")
    else:
        primary_bottleneck = "Optimal silicon utilization"
        gain_pct = 5.0
        recommendations.append("Hardware operating within target efficiency envelope")

    # Potential financial savings per 1k tokens
    cost_per_1k = cost_per_1m_tokens_usd / 1000.0
    savings_per_1k = round(cost_per_1k * (gain_pct / 100.0) * 0.6, 5)

    return GPUEfficiencyScore(
        score=final_score,
        accelerator=accel_clean.upper(),
        gpu_id=gpu_id,
        primary_bottleneck=primary_bottleneck,
        potential_throughput_gain_pct=gain_pct,
        cost_savings_per_1k_tokens_usd=savings_per_1k,
        subscores={
            "sm_utilization_pct": round(sm_util_pct, 1),
            "memory_bandwidth_pct": round(memory_bandwidth_pct, 1),
            "mfu_pct": round(norm_mfu, 1),
            "pcie_utilization_pct": round(pcie_util_pct, 1),
            "nccl_stall_ms": round(nccl_stall_ms, 1),
        },
        recommendations=recommendations,
    )
