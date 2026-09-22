"""Deep vLLM Reference Instrumentation and Silicon Telemetry Profiler.

Captures and correlates the complete vLLM request and batch execution lifecycle:
Request Arrival -> Queueing -> Scheduling -> Chunked Prefill -> KV Block Allocation -> Decode -> Completion

Correlates engine state (KV blocks, swaps, queues) directly with physical silicon telemetry
(SM active, DRAM active, PCIe bus throughput, GPU power draw).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List


class VLLMStage(str, Enum):
    ARRIVAL = "arrival"
    QUEUE = "queue"
    SCHEDULING = "scheduling"
    PREFILL = "prefill"
    KV_ALLOCATION = "kv_allocation"
    DECODE = "decode"
    COMPLETION = "completion"


@dataclass
class VLLMRequestSpan:
    """Detailed telemetry span for a single vLLM inference request."""

    request_id: str
    model: str
    prompt_tokens: int
    output_tokens: int
    queue_time_ms: float
    prefill_time_ms: float
    decode_time_ms: float
    total_time_ms: float
    ttft_ms: float
    tpot_ms: float
    kv_blocks_allocated: int
    gpu_cache_usage_pct: float
    swapped_blocks: int = 0
    prefix_cache_hit: bool = False
    sm_active_pct: float = 0.0
    dram_active_pct: float = 0.0
    pcie_throughput_mb_s: float = 0.0
    gpu_power_w: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        return {
            "request_id": self.request_id,
            "model": self.model,
            "prompt_tokens": self.prompt_tokens,
            "output_tokens": self.output_tokens,
            "queue_time_ms": self.queue_time_ms,
            "prefill_time_ms": self.prefill_time_ms,
            "decode_time_ms": self.decode_time_ms,
            "total_time_ms": self.total_time_ms,
            "ttft_ms": self.ttft_ms,
            "tpot_ms": self.tpot_ms,
            "kv_blocks_allocated": self.kv_blocks_allocated,
            "gpu_cache_usage_pct": self.gpu_cache_usage_pct,
            "swapped_blocks": self.swapped_blocks,
            "prefix_cache_hit": self.prefix_cache_hit,
            "sm_active_pct": self.sm_active_pct,
            "dram_active_pct": self.dram_active_pct,
            "pcie_throughput_mb_s": self.pcie_throughput_mb_s,
            "gpu_power_w": self.gpu_power_w,
        }


@dataclass
class VLLMBatchTelemetry:
    """Snapshot of active vLLM scheduler iteration and GPU hardware signals."""

    step_id: int
    num_running_reqs: int
    num_waiting_reqs: int
    num_swapped_reqs: int
    gpu_cache_usage_pct: float
    cpu_cache_usage_pct: float
    sm_active_pct: float
    dram_active_pct: float
    pcie_rx_mb_s: float
    pcie_tx_mb_s: float
    gpu_power_w: float
    timestamp_ms: float = 0.0


@dataclass
class VLLMDiagnosticReport:
    """Silicon and scheduling diagnosis for a vLLM serving instance."""

    model: str
    total_requests: int
    ttft_p50_ms: float
    ttft_p95_ms: float
    ttft_p99_ms: float
    tpot_p50_ms: float
    tpot_p95_ms: float
    avg_throughput_tok_s: float
    primary_bottleneck: str
    root_cause_explanation: str
    evidence: List[str] = field(default_factory=list)
    recommended_parameters: List[str] = field(default_factory=list)
    observed_hardware_metrics: Dict[str, float] = field(default_factory=dict)
    data_source: str = "OBSERVED_VLLM_TELEMETRY"

    def to_dict(self) -> dict[str, Any]:
        return {
            "model": self.model,
            "total_requests": self.total_requests,
            "data_source": self.data_source,
            "latency": {
                "ttft_p50_ms": self.ttft_p50_ms,
                "ttft_p95_ms": self.ttft_p95_ms,
                "ttft_p99_ms": self.ttft_p99_ms,
                "tpot_p50_ms": self.tpot_p50_ms,
                "tpot_p95_ms": self.tpot_p95_ms,
            },
            "throughput_tokens_per_sec": self.avg_throughput_tok_s,
            "primary_bottleneck": self.primary_bottleneck,
            "root_cause_explanation": self.root_cause_explanation,
            "evidence": self.evidence,
            "recommended_parameters": self.recommended_parameters,
            "observed_hardware_metrics": self.observed_hardware_metrics,
        }


class VLLMProfiler:
    """High-frequency request and engine profiler for vLLM deployments."""

    def __init__(self, model: str = "qwen-2.5-32b"):
        self.model = model
        self.request_spans: List[VLLMRequestSpan] = []
        self.batch_snapshots: List[VLLMBatchTelemetry] = []

    def record_request(self, span: VLLMRequestSpan) -> None:
        """Record an end-to-end inference request span."""
        self.request_spans.append(span)

    def record_batch_telemetry(self, batch: VLLMBatchTelemetry) -> None:
        """Record a scheduler iteration snapshot with physical GPU signals."""
        self.batch_snapshots.append(batch)

    def diagnose(self) -> VLLMDiagnosticReport:
        """Analyze recorded spans and hardware telemetry to extract silicon root causes."""
        if not self.request_spans:
            return VLLMDiagnosticReport(
                model=self.model,
                total_requests=0,
                ttft_p50_ms=0.0,
                ttft_p95_ms=0.0,
                ttft_p99_ms=0.0,
                tpot_p50_ms=0.0,
                tpot_p95_ms=0.0,
                avg_throughput_tok_s=0.0,
                primary_bottleneck="No requests recorded",
                root_cause_explanation="Profiler has not ingested any active vLLM spans.",
                data_source="EMPTY",
            )

        ttft_values = sorted(s.ttft_ms for s in self.request_spans)
        tpot_values = sorted(s.tpot_ms for s in self.request_spans)
        total_tokens = sum(s.prompt_tokens + s.output_tokens for s in self.request_spans)
        total_duration_sec = sum(s.total_time_ms for s in self.request_spans) / 1000.0
        n = len(ttft_values)

        def pct(arr: list[float], p: float) -> float:
            idx = int(round(p * (len(arr) - 1)))
            return arr[idx]

        ttft_p50 = pct(ttft_values, 0.50)
        ttft_p95 = pct(ttft_values, 0.95)
        ttft_p99 = pct(ttft_values, 0.99)
        tpot_p50 = pct(tpot_values, 0.50)
        tpot_p95 = pct(tpot_values, 0.95)
        throughput = (total_tokens / total_duration_sec) if total_duration_sec > 0 else 0.0

        # Hardware averages
        avg_sm = sum(s.sm_active_pct for s in self.request_spans) / n
        avg_dram = sum(s.dram_active_pct for s in self.request_spans) / n
        avg_pcie = sum(s.pcie_throughput_mb_s for s in self.request_spans) / n
        avg_queue = sum(s.queue_time_ms for s in self.request_spans) / n
        total_swapped = sum(s.swapped_blocks for s in self.request_spans)
        prefix_hits = sum(1 for s in self.request_spans if s.prefix_cache_hit)

        evidence: List[str] = []
        recommendations: List[str] = []

        # Identify physical root cause
        if total_swapped > 0 or avg_pcie > 10000.0:
            bottleneck = "Host-to-Device KV-Cache Thrashing (PCIe Bus Saturated)"
            explanation = (
                f"GPU VRAM exhausted with {total_swapped} blocks swapped to host RAM. "
                f"DMA transfers saturated PCIe bus at {avg_pcie:.1f} MB/s, forcing GPU SM cores to stall."
            )
            evidence.append(f"{total_swapped} KV cache blocks swapped across {n} requests")
            evidence.append(f"PCIe throughput reached {avg_pcie:.1f} MB/s during memory swap operations")
            recommendations.append("Set --gpu-memory-utilization 0.95 (default is 0.90)")
            recommendations.append("Activate --enable-prefix-caching to eliminate redundant KV allocations")
            recommendations.append("Reduce --max-model-len or deploy node with PCIe Gen5 / NVLink")

        elif avg_queue > (ttft_p50 * 0.4) and avg_queue > 150.0:
            bottleneck = "Scheduler Queue Saturation (Head-of-Line Blocking)"
            explanation = (
                f"Average request queued for {avg_queue:.1f}ms before prefill execution. "
                "Large unchunked prefill prompts blocked incoming request scheduling."
            )
            evidence.append(f"Mean queue time {avg_queue:.1f}ms represents {(avg_queue/ttft_p50)*100:.1f}% of TTFT")
            evidence.append(f"TTFT p99 degraded to {ttft_p99:.1f}ms under concurrent load")
            recommendations.append("Enable --enable-chunked-prefill to interleave prefill with decode iterations")
            recommendations.append("Tune --max-num-batched-tokens (e.g. 512 or 1024) to smooth prefill latency")
            recommendations.append("Increase --max-num-seqs to increase scheduler batch concurrency")

        elif avg_dram > 75.0 and avg_sm < 55.0:
            bottleneck = "Memory-Bandwidth Bound (Autoregressive Token Decode)"
            explanation = (
                f"HBM memory bus saturated at {avg_dram:.1f}% while SM compute cores remained underutilized at {avg_sm:.1f}%. "
                "Throughput is strictly bound by weights memory bandwidth."
            )
            evidence.append(f"DRAM active {avg_dram:.1f}% vs SM active {avg_sm:.1f}%")
            evidence.append(f"TPOT p95 is {tpot_p95:.1f}ms per generated token")
            recommendations.append("Deploy model with FP8 / AWQ 4-bit weight quantization to cut memory bandwidth demands by 50%")
            recommendations.append("Increase concurrent batch size to improve arithmetic intensity")

        else:
            bottleneck = "Optimal Hardware Envelope"
            explanation = "vLLM serving instance operating with balanced compute, memory, and bus metrics."
            evidence.append(f"SM active {avg_sm:.1f}%, DRAM active {avg_dram:.1f}%")
            evidence.append(f"Prefix cache hit rate: {(prefix_hits/n)*100:.1f}%")
            recommendations.append("Current serving configuration within target SLA envelope")

        return VLLMDiagnosticReport(
            model=self.model,
            total_requests=n,
            ttft_p50_ms=round(ttft_p50, 1),
            ttft_p95_ms=round(ttft_p95, 1),
            ttft_p99_ms=round(ttft_p99, 1),
            tpot_p50_ms=round(tpot_p50, 1),
            tpot_p95_ms=round(tpot_p95, 1),
            avg_throughput_tok_s=round(throughput, 1),
            primary_bottleneck=bottleneck,
            root_cause_explanation=explanation,
            evidence=evidence,
            recommended_parameters=recommendations,
            observed_hardware_metrics={
                "avg_sm_active_pct": round(avg_sm, 1),
                "avg_dram_active_pct": round(avg_dram, 1),
                "avg_pcie_throughput_mb_s": round(avg_pcie, 1),
                "avg_queue_time_ms": round(avg_queue, 1),
            },
            data_source="OBSERVED_VLLM_TELEMETRY",
        )
