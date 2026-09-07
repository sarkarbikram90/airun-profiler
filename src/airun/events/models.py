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


class TraceRecord(BaseModel):
    """A full persisted trace containing all spans and optional computed summary."""

    trace_id: str
    created_at: str
    spans: List[TraceSpan] = Field(default_factory=list)
    summary: Optional[TraceSummary] = None
