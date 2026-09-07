"""Physics of AI Waste Engine and Model FLOPs Utilization (MFU) Calculator.

Implements deep detection of the 4 canonical physical bottlenecks in AI workloads:
1. Dataloader Starvation (CPU/IO Bound)
2. NCCL Communication Overhead (Network Bound)
3. PCIe Bus Saturation (Memory Bound)
4. Framework Eager-Mode Overhead (Software Bound)

Quantifies MFU against theoretical peak accelerator FLOPs and calculates real-time
'Financial Bleed' ($/hr and total wasted dollars) with actionable remediation steps.
"""

from __future__ import annotations

from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field

from airun.pricing.energy import get_accelerator_profile


class WasteCategory(str, Enum):
    DATALOADER_STARVATION = "dataloader_starvation"
    NCCL_OVERHEAD = "nccl_overhead"
    PCIE_BOTTLENECK = "pcie_bottleneck"
    FRAMEWORK_OVERHEAD = "framework_overhead"


class WasteSeverity(str, Enum):
    LOW = "low"
    MODERATE = "moderate"
    HIGH = "high"
    CRITICAL = "critical"


class WasteComponent(BaseModel):
    """Breakdown of a specific physical compute waste factor."""

    category: WasteCategory
    display_name: str
    waste_pct: float  # Percentage of execution time or capacity wasted (0.0 - 100.0)
    wasted_duration_ms: float
    wasted_cost_usd: float
    hourly_bleed_usd: float
    severity: WasteSeverity
    diagnosis: str
    remediation: str


class MFUReport(BaseModel):
    """Model FLOPs Utilization (MFU) measurement and classification."""

    accelerator_name: str
    num_accelerators: int = 1
    theoretical_peak_tflops_per_device: float
    total_theoretical_peak_tflops: float
    total_flops: float
    achieved_tflops: float
    mfu_pct: float  # (achieved_tflops / total_theoretical_peak_tflops) * 100
    efficiency_rating: str  # 'Optimal', 'Moderate', 'Critical Waste'
    is_training: bool = False
    tokens_processed: int = 0
    model_params_billions: float = 0.0


class WasteAnalysisReport(BaseModel):
    """Comprehensive physical waste analysis and financial bleed report."""

    workload_id: str
    accelerator: str
    num_gpus: int = 1
    duration_ms: float
    total_cost_usd: float
    total_wasted_cost_usd: float
    total_waste_pct: float
    effective_cost_usd: float
    hourly_burn_rate_usd: float
    hourly_financial_bleed_usd: float
    mfu: Optional[MFUReport] = None
    waste_components: List[WasteComponent] = Field(default_factory=list)
    top_bottleneck: Optional[str] = None
    recommendations: List[Dict[str, Any]] = Field(default_factory=list)


def calculate_mfu(
    tokens_processed: int,
    model_params_billions: float,
    duration_ms: float,
    accelerator: Optional[str] = "h100",
    num_accelerators: int = 1,
    is_training: bool = False,
) -> MFUReport:
    """
    Calculate Model FLOPs Utilization (MFU).

    MFU = (Achieved TFLOPS) / (Theoretical Peak TFLOPS)

    Standard Transformer FLOPs scaling:
    - Inference: 2 * Parameters * Tokens
    - Training: 6 * Parameters * Tokens (forward + backward pass)
    """
    profile = get_accelerator_profile(accelerator)
    num_dev = max(1, num_accelerators)
    peak_per_device = profile.peak_tflops_fp16
    total_peak_tflops = peak_per_device * num_dev

    # FLOPs multiplier: 6 for training, 2 for inference
    multiplier = 6.0 if is_training else 2.0
    params = max(0.0, model_params_billions) * 1e9
    tokens = max(0, tokens_processed)

    total_flops = multiplier * params * tokens

    duration_sec = max(0.001, duration_ms / 1000.0)
    # 1 TFLOP = 1e12 FLOPs
    achieved_tflops = (total_flops / duration_sec) / 1e12

    if total_peak_tflops > 0:
        mfu_pct = min(100.0, max(0.0, (achieved_tflops / total_peak_tflops) * 100.0))
    else:
        mfu_pct = 0.0

    if mfu_pct >= 45.0:
        rating = "Optimal"
    elif mfu_pct >= 30.0:
        rating = "Moderate"
    else:
        rating = "Critical Waste"

    return MFUReport(
        accelerator_name=profile.name,
        num_accelerators=num_dev,
        theoretical_peak_tflops_per_device=peak_per_device,
        total_theoretical_peak_tflops=round(total_peak_tflops, 2),
        total_flops=total_flops,
        achieved_tflops=round(achieved_tflops, 2),
        mfu_pct=round(mfu_pct, 2),
        efficiency_rating=rating,
        is_training=is_training,
        tokens_processed=tokens,
        model_params_billions=model_params_billions,
    )


def detect_compute_waste(
    telemetry_samples: Optional[List[Dict[str, Any]]] = None,
    accelerator: Optional[str] = "h100",
    num_gpus: int = 1,
    duration_ms: float = 0.0,
    total_cost_usd: Optional[float] = None,
    tokens_processed: int = 0,
    model_params_billions: float = 0.0,
    is_training: bool = False,
    workload_id: str = "workload-default",
) -> WasteAnalysisReport:
    """
    Detect the 4 physical AI compute waste patterns from DCGM / telemetry samples:
    1. Dataloader Starvation (CPU/IO Bound)
    2. NCCL Communication Overhead (Network Bound)
    3. PCIe Bottleneck (Memory Bound)
    4. Framework Overhead (Software Bound)

    Calculates financial bleed ($/hr and total wasted $) and generates remediation steps.
    """
    profile = get_accelerator_profile(accelerator)
    num_dev = max(1, num_gpus)
    hourly_rate_per_gpu = profile.typical_hourly_cost_usd
    total_hourly_rate = hourly_rate_per_gpu * num_dev

    # Default run cost if not explicitly passed
    duration_hours = max(0.0, duration_ms) / 3_600_000.0
    if total_cost_usd is None:
        total_cost_usd = total_hourly_rate * duration_hours

    components: List[WasteComponent] = []

    # Default sample metrics or aggregate from provided telemetry
    if telemetry_samples and len(telemetry_samples) > 0:
        avg_sm_util = sum(s.get("sm_util_pct", 70.0) for s in telemetry_samples) / len(
            telemetry_samples
        )
        avg_pcie_tx_rx = sum(s.get("pcie_throughput_mb", 500.0) for s in telemetry_samples) / len(
            telemetry_samples
        )
        avg_nccl_sync_ms = sum(s.get("nccl_wait_ms", 0.0) for s in telemetry_samples) / len(
            telemetry_samples
        )
        avg_cpu_util = sum(s.get("cpu_util_pct", 40.0) for s in telemetry_samples) / len(
            telemetry_samples
        )
        avg_eager_overhead_pct = sum(
            s.get("eager_overhead_pct", 5.0) for s in telemetry_samples
        ) / len(telemetry_samples)
    else:
        # Heuristic baseline for AI workloads
        avg_sm_util = 65.0
        avg_pcie_tx_rx = 250.0
        avg_nccl_sync_ms = 45.0
        avg_cpu_util = 85.0
        avg_eager_overhead_pct = 12.0

    # 1. Dataloader Starvation Detection
    # Symptom: SM utilization drops (<55%) while PCIe throughput is low (<600MB/s)
    # The GPU is stalling waiting for CPU workers to fetch/transform batches.
    dataloader_waste_pct = 0.0
    if avg_sm_util < 55.0 and avg_pcie_tx_rx < 600.0:
        dataloader_waste_pct = round(max(0.0, (55.0 - avg_sm_util) * 0.75), 1)
    elif avg_sm_util < 70.0 and avg_pcie_tx_rx < 300.0:
        dataloader_waste_pct = round(max(0.0, (70.0 - avg_sm_util) * 0.40), 1)

    if dataloader_waste_pct > 0.0:
        w_dur = (dataloader_waste_pct / 100.0) * duration_ms
        w_cost = (dataloader_waste_pct / 100.0) * total_cost_usd
        h_bleed = (dataloader_waste_pct / 100.0) * total_hourly_rate
        sev = (
            WasteSeverity.CRITICAL
            if dataloader_waste_pct >= 20.0
            else (WasteSeverity.HIGH if dataloader_waste_pct >= 10.0 else WasteSeverity.MODERATE)
        )
        components.append(
            WasteComponent(
                category=WasteCategory.DATALOADER_STARVATION,
                display_name="Dataloader Starvation (CPU/IO Bound)",
                waste_pct=dataloader_waste_pct,
                wasted_duration_ms=round(w_dur, 2),
                wasted_cost_usd=round(w_cost, 4),
                hourly_bleed_usd=round(h_bleed, 2),
                severity=sev,
                diagnosis=(
                    f"GPU SM active cycles dropped while PCIe bandwidth is idle (~{avg_pcie_tx_rx:.0f} MB/s). "
                    "Accelerator is starving waiting for CPU batch preparation."
                ),
                remediation=(
                    "Increase DataLoader 'num_workers' (recommended: 4-8 per GPU), "
                    "enable 'pin_memory=True', or pre-cache datasets to local NVMe."
                ),
            )
        )

    # 2. NCCL Communication Overhead Detection
    # Symptom: Multi-GPU All-Reduce synchronization stalls or high barrier wait times
    nccl_waste_pct = 0.0
    if num_dev > 1 or avg_nccl_sync_ms > 30.0:
        if avg_nccl_sync_ms >= 80.0:
            nccl_waste_pct = round(min(35.0, avg_nccl_sync_ms * 0.25), 1)
        elif avg_nccl_sync_ms >= 30.0:
            nccl_waste_pct = round(min(20.0, avg_nccl_sync_ms * 0.15), 1)

    if nccl_waste_pct > 0.0:
        w_dur = (nccl_waste_pct / 100.0) * duration_ms
        w_cost = (nccl_waste_pct / 100.0) * total_cost_usd
        h_bleed = (nccl_waste_pct / 100.0) * total_hourly_rate
        sev = (
            WasteSeverity.CRITICAL
            if nccl_waste_pct >= 20.0
            else (WasteSeverity.HIGH if nccl_waste_pct >= 10.0 else WasteSeverity.MODERATE)
        )
        components.append(
            WasteComponent(
                category=WasteCategory.NCCL_OVERHEAD,
                display_name="NCCL Communication Overhead (Network Bound)",
                waste_pct=nccl_waste_pct,
                wasted_duration_ms=round(w_dur, 2),
                wasted_cost_usd=round(w_cost, 4),
                hourly_bleed_usd=round(h_bleed, 2),
                severity=sev,
                diagnosis=(
                    f"Gradient synchronization barrier stalls (~{avg_nccl_sync_ms:.1f}ms wait/step). "
                    "Inter-GPU network fabric (InfiniBand/RoCE) or ring topology bottleneck."
                ),
                remediation=(
                    "Tune NCCL buffer sizes ('NCCL_BUFFSIZE=16777216'), enable gradient accumulation "
                    "to reduce all-reduce frequency, or inspect InfiniBand retransmit counters."
                ),
            )
        )

    # 3. PCIe Bottlenecks Detection
    # Symptom: Host RAM <-> VRAM saturation with high PCIe throughput but stagnant compute
    pcie_waste_pct = 0.0
    if avg_pcie_tx_rx > 15000.0 and avg_sm_util < 60.0:
        pcie_waste_pct = 18.0
    elif avg_pcie_tx_rx > 8000.0 and avg_sm_util < 65.0:
        pcie_waste_pct = 10.0

    if pcie_waste_pct > 0.0:
        w_dur = (pcie_waste_pct / 100.0) * duration_ms
        w_cost = (pcie_waste_pct / 100.0) * total_cost_usd
        h_bleed = (pcie_waste_pct / 100.0) * total_hourly_rate
        sev = WasteSeverity.HIGH if pcie_waste_pct >= 15.0 else WasteSeverity.MODERATE
        components.append(
            WasteComponent(
                category=WasteCategory.PCIE_BOTTLENECK,
                display_name="PCIe Bus Saturation (Memory Bound)",
                waste_pct=pcie_waste_pct,
                wasted_duration_ms=round(w_dur, 2),
                wasted_cost_usd=round(w_cost, 4),
                hourly_bleed_usd=round(h_bleed, 2),
                severity=sev,
                diagnosis=(
                    f"Excessive Host-to-Device tensor transfers ({avg_pcie_tx_rx:.0f} MB/s) "
                    "saturating PCIe bus while GPU compute sits idle."
                ),
                remediation=(
                    "Batch Host-to-Device transfers, keep embeddings/weights in GPU VRAM, "
                    "or enable asynchronous non-blocking memory copies (tensor.to(device, non_blocking=True))."
                ),
            )
        )

    # 4. Framework Overhead Detection
    # Symptom: High CPU utilization in Python process (PyTorch eager mode dispatch)
    framework_waste_pct = 0.0
    if avg_cpu_util > 75.0 and avg_sm_util < 75.0:
        framework_waste_pct = round(max(3.0, min(25.0, avg_eager_overhead_pct)), 1)
    elif avg_eager_overhead_pct > 8.0:
        framework_waste_pct = round(avg_eager_overhead_pct, 1)

    if framework_waste_pct > 0.0:
        w_dur = (framework_waste_pct / 100.0) * duration_ms
        w_cost = (framework_waste_pct / 100.0) * total_cost_usd
        h_bleed = (framework_waste_pct / 100.0) * total_hourly_rate
        sev = WasteSeverity.HIGH if framework_waste_pct >= 15.0 else WasteSeverity.LOW
        components.append(
            WasteComponent(
                category=WasteCategory.FRAMEWORK_OVERHEAD,
                display_name="Framework Eager-Mode Overhead (Software Bound)",
                waste_pct=framework_waste_pct,
                wasted_duration_ms=round(w_dur, 2),
                wasted_cost_usd=round(w_cost, 4),
                hourly_bleed_usd=round(h_bleed, 2),
                severity=sev,
                diagnosis=(
                    f"PyTorch eager mode host Python dispatch latency ({avg_cpu_util:.0f}% CPU util). "
                    "GPU is experiencing idle inter-kernel launch bubbles."
                ),
                remediation=(
                    "Compile graph via 'torch.compile(model, mode=\"reduce-overhead\")' or "
                    "capture execution in CUDA Graphs to eliminate CPU kernel launch overhead."
                ),
            )
        )

    # Sort components by waste percentage descending
    components.sort(key=lambda c: c.waste_pct, reverse=True)

    # Aggregate totals
    total_waste_pct = min(100.0, sum(c.waste_pct for c in components))
    total_wasted_cost_usd = sum(c.wasted_cost_usd for c in components)
    total_hourly_bleed_usd = sum(c.hourly_bleed_usd for c in components)
    effective_cost_usd = max(0.0, total_cost_usd - total_wasted_cost_usd)

    top_bottleneck = components[0].display_name if components else "None Detected (Optimal)"

    # Compute MFU if model parameters and tokens are available
    mfu_report = None
    if tokens_processed > 0 and model_params_billions > 0:
        mfu_report = calculate_mfu(
            tokens_processed=tokens_processed,
            model_params_billions=model_params_billions,
            duration_ms=duration_ms,
            accelerator=accelerator,
            num_accelerators=num_dev,
            is_training=is_training,
        )

    # Actionable FinOps Recommendations
    recommendations: List[Dict[str, Any]] = []
    for comp in components:
        # Projected savings if resolved
        weekly_savings = comp.hourly_bleed_usd * 24 * 7
        monthly_savings = weekly_savings * 4.33
        recommendations.append(
            {
                "category": comp.category.value,
                "title": f"Mitigate {comp.display_name}",
                "severity": comp.severity.value,
                "action": comp.remediation,
                "potential_weekly_savings_usd": round(weekly_savings, 2),
                "potential_monthly_savings_usd": round(monthly_savings, 2),
                "estimated_efficiency_gain_pct": comp.waste_pct,
            }
        )

    # Add pool migration recommendation if significant waste detected
    if total_waste_pct >= 25.0:
        est_mig_weekly = total_hourly_bleed_usd * 0.70 * 24 * 7
        recommendations.append(
            {
                "category": "workload_migration",
                "title": f"Migrate {workload_id} to Optimized GPU Pool",
                "severity": "high",
                "action": "Relocate workload to GKE GPU Node Pool B with host NVMe and InfiniBand fabric.",
                "potential_weekly_savings_usd": round(est_mig_weekly, 2),
                "potential_monthly_savings_usd": round(est_mig_weekly * 4.33, 2),
                "estimated_efficiency_gain_pct": round(total_waste_pct * 0.70, 1),
            }
        )

    return WasteAnalysisReport(
        workload_id=workload_id,
        accelerator=profile.name,
        num_gpus=num_dev,
        duration_ms=round(duration_ms, 2),
        total_cost_usd=round(total_cost_usd, 6),
        total_wasted_cost_usd=round(total_wasted_cost_usd, 6),
        total_waste_pct=round(total_waste_pct, 1),
        effective_cost_usd=round(effective_cost_usd, 6),
        hourly_burn_rate_usd=round(total_hourly_rate, 2),
        hourly_financial_bleed_usd=round(total_hourly_bleed_usd, 2),
        mfu=mfu_report,
        waste_components=components,
        top_bottleneck=top_bottleneck,
        recommendations=recommendations,
    )
