"""Asynchronous Pub/Sub Message Queue backbone for AI Infrastructure telemetry.

Provides decoupled event streaming between the Rust telemetry collector,
Python ML/waste detection worker, and TypeScript control plane:
- telemetry.gpu.metrics (high-frequency DCGM batches)
- workload.waste.detected (bottleneck & financial bleed alerts)
- workload.completed (end-of-run efficiency calculations)
- cluster.node.health (thermal, PCIe errors, and NVLink fabric state)
"""

from __future__ import annotations

import time
import uuid
from typing import Any, Callable, Dict, List, Optional

from pydantic import BaseModel, Field


class EventMessage(BaseModel):
    """Event message envelope for Pub/Sub messaging."""

    event_id: str = Field(default_factory=lambda: f"evt_{uuid.uuid4().hex[:12]}")
    event_type: str
    topic: str = "ai-infrastructure-events"
    payload: Dict[str, Any] = Field(default_factory=dict)
    timestamp: float = Field(default_factory=time.time)
    source_service: str = "airun-collector"
    acknowledged: bool = False


class EventQueue:
    """In-memory & Pub/Sub compatible event bus for decoupled AI workload processing."""

    def __init__(self, topic: str = "ai-infrastructure-events") -> None:
        self.topic = topic
        self._subscribers: Dict[str, List[Callable[[EventMessage], None]]] = {}
        self._history: List[EventMessage] = []
        self._max_history: int = 1000

    def subscribe(self, event_type: str, handler: Callable[[EventMessage], None]) -> None:
        """Register an event handler callback for a specific event type or wildcard '*'."""
        if event_type not in self._subscribers:
            self._subscribers[event_type] = []
        self._subscribers[event_type].append(handler)

    def publish(
        self,
        event_type: str,
        payload: Dict[str, Any],
        source_service: str = "airun-collector",
    ) -> EventMessage:
        """Publish an event to the queue and notify active subscribers."""
        msg = EventMessage(
            event_type=event_type,
            topic=self.topic,
            payload=payload,
            source_service=source_service,
        )
        self._history.append(msg)
        if len(self._history) > self._max_history:
            self._history.pop(0)

        # Notify specific listeners
        handlers = self._subscribers.get(event_type, []) + self._subscribers.get("*", [])
        for handler in handlers:
            try:
                handler(msg)
            except Exception:  # pragma: no cover
                pass

        return msg

    def publish_batch(
        self,
        event_type: str,
        payloads: List[Dict[str, Any]],
        source_service: str = "airun-collector",
    ) -> List[EventMessage]:
        """Batch publish multiple telemetry events for efficiency."""
        messages: List[EventMessage] = []
        for p in payloads:
            messages.append(self.publish(event_type, p, source_service=source_service))
        return messages

    def get_history(self, event_type: Optional[str] = None, limit: int = 50) -> List[EventMessage]:
        """Retrieve recent events from the queue buffer."""
        if event_type:
            filtered = [m for m in self._history if m.event_type == event_type]
            return filtered[-limit:]
        return self._history[-limit:]

    def clear(self) -> None:
        """Clear event history buffer."""
        self._history.clear()


# Default singleton instance
DEFAULT_EVENT_QUEUE = EventQueue()
