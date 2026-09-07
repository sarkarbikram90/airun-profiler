"""Event models for airun runtime profiler."""

from __future__ import annotations

from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class SpanKind(str, Enum):
    WORKFLOW = "workflow"
    AGENT_STEP = "agent_step"
    LLM = "llm"
    TOOL = "tool"
    HTTP = "http"
    DB = "db"
    SEARCH = "search"
    CUSTOM = "custom"


class SpanStatus(str, Enum):
    SUCCESS = "success"
    FAILURE = "failure"
    TIMEOUT = "timeout"
    RETRY = "retry"
    PARTIAL_SUCCESS = "partial_success"
    UNKNOWN = "unknown"


class FindingSeverity(str, Enum):
    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"


class DiagnosticFinding(BaseModel):
    """Structured diagnostic finding with severity and category."""

    severity: FindingSeverity
    message: str
    category: str = "general"
    impact_cost_usd: Optional[float] = None
    impact_duration_ms: Optional[float] = None


class TraceSpan(BaseModel):
    """Represents a single profiled execution span."""

    trace_id: str
    span_id: str
    parent_id: Optional[str] = None
    name: str
    kind: SpanKind = SpanKind.CUSTOM
    start_time: str
    end_time: Optional[str] = None
    duration_ms: Optional[float] = None
    status: SpanStatus = SpanStatus.SUCCESS
    provider: Optional[str] = None
    model: Optional[str] = None
    tokens_input: Optional[int] = None
    tokens_output: Optional[int] = None
    cost_usd: Optional[float] = None
    retry_count: int = 0
    quality_score: Optional[float] = None
    evaluation_metrics: Dict[str, Any] = Field(default_factory=dict)
    accelerator_type: Optional[str] = None
    power_watts: Optional[float] = None
    energy_joules: Optional[float] = None
    energy_kwh: Optional[float] = None
    energy_cost_usd: Optional[float] = None
    error: Optional[Dict[str, Any]] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)

    @property
    def total_tokens(self) -> int:
        return (self.tokens_input or 0) + (self.tokens_output or 0)


# ==============================================================================
# Golden Signals Hierarchy for AI Infrastructure
# ==============================================================================


class GoldenSignalsEconomics(BaseModel):
    """Layer 1: Economics - What the CFO sees."""

    cost_per_effective_gpu_hour_usd: float = 0.0
    cost_per_token_usd: Optional[float] = None
    cost_per_1m_tokens_usd: Optional[float] = None
    cost_per_successful_outcome_usd: Optional[float] = None
    financial_bleed_hourly_usd: float = 0.0
    total_wasted_spend_usd: float = 0.0
    waste_percentage: float = 0.0


class GoldenSignalsEfficiency(BaseModel):
    """Layer 2: Efficiency - What the ML Engineer sees."""

    mfu_pct: float = 0.0  # Model FLOPs Utilization %
    achieved_tflops: float = 0.0  # Measured tensor compute throughput
    gpu_sm_utilization_pct: float = 0.0  # Streaming Multiprocessor active cycles
    memory_bandwidth_utilization_pct: float = 0.0  # HBM/VRAM bus saturation
    pcie_utilization_pct: float = 0.0  # Host <-> Device transfer efficiency
    effective_utilization_pct: float = 0.0


class GoldenSignalsReliability(BaseModel):
    """Layer 3: Reliability - What the Platform Engineer sees."""

    job_failure_rate_pct: float = 0.0
    mean_time_to_recovery_ms: float = 0.0
    retry_count: int = 0
    checkpoint_frequency_min: float = 30.0
    recovery_overhead_cost_usd: float = 0.0


class GoldenSignalsInfrastructure(BaseModel):
    """Layer 4: Infrastructure - The physical reality under the hood."""

    power_draw_watts: float = 0.0
    thermal_throttling: bool = False
    pcie_error_count: int = 0
    network_retransmits_pct: float = 0.0
    nvlink_throughput_gbs: float = 0.0
    pue: float = 1.20


class GoldenSignals(BaseModel):
    """Complete 4-Layer Golden Signals hierarchy."""

    economics: GoldenSignalsEconomics = Field(default_factory=GoldenSignalsEconomics)
    efficiency: GoldenSignalsEfficiency = Field(default_factory=GoldenSignalsEfficiency)
    reliability: GoldenSignalsReliability = Field(default_factory=GoldenSignalsReliability)
    infrastructure: GoldenSignalsInfrastructure = Field(default_factory=GoldenSignalsInfrastructure)


class DCGMSample(BaseModel):
    """Single high-frequency NVIDIA DCGM / host node telemetry sample."""

    timestamp: str
    gpu_id: int = 0
    node_name: str = "gke-gpu-node"
    sm_util_pct: float = 0.0
    memory_used_mb: float = 0.0
    memory_total_mb: float = 81920.0
    temperature_c: float = 55.0
    power_watts: float = 350.0
    pcie_tx_bytes_sec: float = 0.0
    pcie_rx_bytes_sec: float = 0.0
    pcie_errors: int = 0
    nvlink_throughput_mb_sec: float = 0.0
    nccl_barrier_wait_ms: float = 0.0
    cpu_util_pct: float = 20.0


class TelemetryBatch(BaseModel):
    """Batched high-frequency node telemetry payload for Pub/Sub ingestion."""

    batch_id: str
    cluster_id: str
    node_id: str
    accelerator_type: str = "h100"
    num_gpus: int = 8
    samples: List[DCGMSample] = Field(default_factory=list)
    published_at: str


class TraceSummary(BaseModel):
    """High-level computed summary of a complete execution trace."""

    trace_id: str
    name: str
    outcome: SpanStatus
    start_time: str
    end_time: Optional[str] = None
    total_duration_ms: float = 0.0
    critical_path_ms: float = 0.0
    total_cost_usd: float = 0.0
    wasted_cost_usd: float = 0.0
    cost_per_successful_outcome_usd: Optional[float] = None
    quality_score: Optional[float] = None
    evaluation_metrics: Dict[str, Any] = Field(default_factory=dict)
    total_energy_joules: float = 0.0
    total_energy_kwh: float = 0.0
    total_energy_cost_usd: float = 0.0
    intelligence_per_dollar: Optional[float] = None
    intelligence_per_watt: Optional[float] = None
    tokens_per_dollar: Optional[float] = None
    tokens_per_kwh: Optional[float] = None
    cluster_utilization_pct: Optional[float] = None
    effective_utilization_pct: Optional[float] = None
    total_tokens: int = 0
    input_tokens: int = 0
    output_tokens: int = 0
    span_count: int = 0
    llm_call_count: int = 0
    tool_call_count: int = 0
    external_call_count: int = 0
    retry_count: int = 0
    failed_steps_count: int = 0
    top_cost_drivers: List[Dict[str, Any]] = Field(default_factory=list)
    findings: List[str] = Field(default_factory=list)
    diagnostic_findings: List[DiagnosticFinding] = Field(default_factory=list)
    # Advanced AI Infrastructure metrics
    mfu_pct: Optional[float] = None
    achieved_tflops: Optional[float] = None
    financial_bleed_usd: Optional[float] = None
    hourly_bleed_usd: Optional[float] = None
    golden_signals: Optional[GoldenSignals] = None


class TraceRecord(BaseModel):
    """A full persisted trace containing all spans and optional computed summary."""

    trace_id: str
    created_at: str
    spans: List[TraceSpan] = Field(default_factory=list)
    summary: Optional[TraceSummary] = None
