"""Unit tests for Pub/Sub event backbone and the 10 standard event types."""

import pytest

from airun.events.pubsub import (
    AirunEventEnvelope,
    AirunEventType,
    GpuAlertPayload,
    PubSubEventBus,
)


def test_standard_event_types():
    """Verify all 10 standard event types are codified in the enum."""
    expected = [
        "workload.started",
        "workload.completed",
        "trace.created",
        "gpu.alert",
        "provider.degraded",
        "provider.failed",
        "dr.drill.started",
        "dr.drill.completed",
        "optimization.detected",
        "optimization.applied",
    ]
    for exp in expected:
        assert AirunEventType(exp) is not None
    assert len(AirunEventType) == 10


def test_event_envelope_json_roundtrip():
    """Verify serialization and deserialization of AirunEventEnvelope."""
    payload = GpuAlertPayload(
        node_id="gke-node-gpu-01",
        gpu_index=0,
        accelerator="H100-SXM5-80GB",
        alert_type="thermal_throttling",
        severity="warning",
        description="GPU Core exceeded 82C throttle limit",
        metric_value=84.5,
        threshold_value=82.0,
        hourly_financial_bleed_usd=16.95,
    )

    envelope = AirunEventEnvelope(
        event_type=AirunEventType.GPU_ALERT,
        source="airun-collector/gke-node-gpu-01",
        workload_id="customer-support-agent",
        trace_id="tr_998877",
        payload=payload,
    )

    json_str = envelope.to_json()
    assert "gpu.alert" in json_str
    assert "thermal_throttling" in json_str

    restored = AirunEventEnvelope[GpuAlertPayload].from_json(json_str)
    assert restored.event_type == AirunEventType.GPU_ALERT
    assert restored.source == "airun-collector/gke-node-gpu-01"
    assert restored.payload.gpu_index == 0
    assert restored.payload.metric_value == 84.5


@pytest.mark.asyncio
async def test_pubsub_event_bus_dispatch():
    """Verify async event routing and handler dispatching in PubSubEventBus."""
    bus = PubSubEventBus()
    received_events = []

    async def handle_alert(env: AirunEventEnvelope):
        received_events.append(env)

    bus.subscribe(AirunEventType.GPU_ALERT, handle_alert)

    payload = GpuAlertPayload(
        node_id="node-01",
        gpu_index=1,
        alert_type="pcie_degradation",
        severity="critical",
        description="PCIe link speed downgraded to Gen1",
        metric_value=1.5,
        threshold_value=32.0,
    )
    evt = AirunEventEnvelope(
        event_type=AirunEventType.GPU_ALERT,
        source="airun-collector/node-01",
        payload=payload,
    )

    await bus.publish(evt)
    dispatched = await bus.dispatch_next(timeout=1.0)

    assert dispatched is not None
    assert len(received_events) == 1
    assert received_events[0].event_type == AirunEventType.GPU_ALERT
    assert len(bus.history) == 1
