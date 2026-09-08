"""Pub/Sub event backbone for distributed airun architecture.

Codifies the 10 standard event types and provides the asynchronous event bus
connecting Python workloads, Rust collectors, and TypeScript control planes.
"""

from __future__ import annotations

import asyncio
import json
import logging
import uuid
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Callable, Coroutine, Dict, Generic, List, Optional, TypeVar

from pydantic import BaseModel, Field

logger = logging.getLogger("airun.events.pubsub")

T = TypeVar("T")


class AirunEventType(str, Enum):
    """The 10 standard event types in the airun distributed event backbone."""

    WORKLOAD_STARTED = "workload.started"
    WORKLOAD_COMPLETED = "workload.completed"
    TRACE_CREATED = "trace.created"
    GPU_ALERT = "gpu.alert"
    PROVIDER_DEGRADED = "provider.degraded"
    PROVIDER_FAILED = "provider.failed"
    DR_DRILL_STARTED = "dr.drill.started"
    DR_DRILL_COMPLETED = "dr.drill.completed"
    OPTIMIZATION_DETECTED = "optimization.detected"
    OPTIMIZATION_APPLIED = "optimization.applied"


class AirunEventEnvelope(BaseModel, Generic[T]):
    """Standardized event envelope across Python, Rust, and TypeScript."""

    event_id: str = Field(default_factory=lambda: f"evt_{uuid.uuid4().hex[:16]}")
    event_type: AirunEventType
    source: str  # e.g. 'airun-sdk', 'airun-collector/node-gpu-01', 'airun-analytics'
    timestamp: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    org_id: Optional[str] = "org_default"
    project_id: Optional[str] = "proj_default"
    cluster_id: Optional[str] = "gke-us-central1-ai"
    workload_id: Optional[str] = None
    trace_id: Optional[str] = None
    payload: T

    def to_json(self) -> str:
        """Serialize envelope to JSON string."""
        return self.model_dump_json()

    @classmethod
    def from_json(cls, json_str: str) -> "AirunEventEnvelope[Any]":
        """Deserialize envelope from JSON string."""
        data = json.loads(json_str)
        return cls(**data)


# Strongly typed payloads for standard events
class WorkloadLifecyclePayload(BaseModel):
    workload_name: str
    workload_type: str = "agent"  # 'training', 'inference', 'eval', 'agent'
    model_name: Optional[str] = None
    node_id: Optional[str] = None
    pid: Optional[int] = None
    duration_ms: Optional[float] = None
    status: str = "running"  # 'running', 'completed', 'failed'


class GpuAlertPayload(BaseModel):
    node_id: str
    gpu_index: int
    accelerator: str = "H100-SXM5-80GB"
    alert_type: str  # 'thermal_throttling', 'pcie_degradation', 'xid_error', 'memory_saturation'
    severity: str = "critical"  # 'info', 'warning', 'critical'
    description: str
    metric_value: float
    threshold_value: float
    hourly_financial_bleed_usd: float = 0.0


class OptimizationDetectedPayload(BaseModel):
    workload_name: str
    trace_id: Optional[str] = None
    category: str  # 'dataloader_starvation', 'nccl_overhead', 'pcie_bottleneck', 'model_switch'
    title: str
    root_cause: str
    remediation_action: str
    potential_weekly_savings_usd: float
    potential_monthly_savings_usd: float
    estimated_efficiency_gain_pct: float
    status: str = "open"


EventHandler = Callable[[AirunEventEnvelope[Any]], Coroutine[Any, Any, None]]


class PubSubEventBus:
    """High-throughput distributed event bus.

    Supports local in-memory async message routing for tests/CLI and
    integrates with Google Cloud Pub/Sub in production GKE deployments.
    """

    def __init__(self, topic_prefix: str = "airun-events") -> None:
        self.topic_prefix = topic_prefix
        self._subscribers: Dict[str, List[EventHandler]] = {}
        self._event_history: List[AirunEventEnvelope[Any]] = []
        self._queue: asyncio.Queue[AirunEventEnvelope[Any]] = asyncio.Queue()
        self._running = False
        self._dispatch_task: Optional[asyncio.Task[None]] = None

    def subscribe(self, event_type: AirunEventType, handler: EventHandler) -> None:
        """Register an async handler for a specific event type."""
        type_str = event_type.value
        if type_str not in self._subscribers:
            self._subscribers[type_str] = []
        self._subscribers[type_str].append(handler)

    def subscribe_all(self, handler: EventHandler) -> None:
        """Subscribe to all events (wildcard)."""
        if "*" not in self._subscribers:
            self._subscribers["*"] = []
        self._subscribers["*"].append(handler)

    async def publish(self, envelope: AirunEventEnvelope[Any]) -> str:
        """Publish an event envelope onto the event bus."""
        self._event_history.append(envelope)
        await self._queue.put(envelope)
        logger.debug(
            "Published event %s of type %s from %s",
            envelope.event_id,
            envelope.event_type,
            envelope.source,
        )
        return envelope.event_id

    async def dispatch_next(self, timeout: float = 2.0) -> Optional[AirunEventEnvelope[Any]]:
        """Pull and synchronously dispatch the next queued event (useful in tests)."""
        try:
            envelope = await asyncio.wait_for(self._queue.get(), timeout=timeout)
            await self._dispatch_envelope(envelope)
            self._queue.task_done()
            return envelope
        except asyncio.TimeoutError:
            return None

    async def _dispatch_envelope(self, envelope: AirunEventEnvelope[Any]) -> None:
        type_str = envelope.event_type.value
        handlers = list(self._subscribers.get(type_str, []))
        handlers.extend(self._subscribers.get("*", []))

        for handler in handlers:
            try:
                await handler(envelope)
            except Exception as e:
                logger.error("Error executing handler for %s: %s", type_str, e)

    @property
    def history(self) -> List[AirunEventEnvelope[Any]]:
        return list(self._event_history)

    def clear(self) -> None:
        self._event_history.clear()
        while not self._queue.empty():
            self._queue.get_nowait()
