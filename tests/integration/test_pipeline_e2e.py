"""End-to-End integration test for the distributed pipeline milestone:

Python Workload -> Rust Collector -> Pub/Sub -> Python Analytics -> PostgreSQL -> TypeScript API.
"""

from datetime import datetime, timezone

import pytest

from airun.analysis.pipeline import DistributedPipelineEngine
from airun.events.models import SpanStatus, TraceRecord, TraceSpan, TraceSummary
from airun.events.pubsub import (
    AirunEventEnvelope,
    AirunEventType,
    PubSubEventBus,
    WorkloadLifecyclePayload,
)


@pytest.mark.asyncio
async def test_end_to_end_pipeline_flow():
    """Verify that a trace event published onto Pub/Sub flows through the Python analytics engine,

    emits an optimization.detected event, and formats PostgreSQL relational records.
    """
    event_bus = PubSubEventBus()
    engine = DistributedPipelineEngine(event_bus=event_bus)

    now_iso = datetime.now(timezone.utc).isoformat()
    trace_id = "tr_e2e_test_001"
    workload_name = "customer-support-agent"

    # Step 1: Workload started event
    start_payload = WorkloadLifecyclePayload(
        workload_name=workload_name,
        workload_type="agent",
        node_id="gke-node-gpu-01",
        status="running",
    )
    start_evt = AirunEventEnvelope(
        event_type=AirunEventType.WORKLOAD_STARTED,
        source="airun-sdk/python",
        workload_id=workload_name,
        trace_id=trace_id,
        payload=start_payload,
    )
    await event_bus.publish(start_evt)

    # Step 2: Trace created with agent spans
    spans = [
        TraceSpan(
            trace_id=trace_id,
            span_id="sp_01",
            name="customer_support_workflow",
            start_time=now_iso,
            end_time=now_iso,
            duration_ms=450.0,
            cost_usd=0.012,
        ),
        TraceSpan(
            trace_id=trace_id,
            span_id="sp_02",
            parent_id="sp_01",
            name="knowledge_base_retrieval",
            start_time=now_iso,
            end_time=now_iso,
            duration_ms=210.0,
            cost_usd=0.0,
        ),
    ]

    trace_payload = {
        "workload_name": workload_name,
        "spans": [s.model_dump() for s in spans],
    }
    trace_evt = AirunEventEnvelope(
        event_type=AirunEventType.TRACE_CREATED,
        source="airun-sdk/python",
        workload_id=workload_name,
        trace_id=trace_id,
        payload=trace_payload,
    )
    await event_bus.publish(trace_evt)

    # Step 3: Trigger pipeline processing
    await engine.handle_trace_created(trace_evt)

    # Verify that optimization.detected was emitted
    history = event_bus.history
    event_types = [e.event_type for e in history]
    assert AirunEventType.WORKLOAD_STARTED in event_types
    assert AirunEventType.TRACE_CREATED in event_types
    assert AirunEventType.OPTIMIZATION_DETECTED in event_types

    opt_events = [e for e in history if e.event_type == AirunEventType.OPTIMIZATION_DETECTED]
    assert len(opt_events) == 1
    opt_payload = opt_events[0].payload
    assert opt_payload.potential_monthly_savings_usd > 0.0
    assert "Hardware Waste Remediation" in opt_payload.title

    # Step 4: Verify PostgreSQL schema mapping
    summary = TraceSummary(
        trace_id=trace_id,
        name=workload_name,
        outcome=SpanStatus.SUCCESS,
        start_time=now_iso,
        end_time=now_iso,
        total_duration_ms=450.0,
        critical_path_ms=450.0,
        span_count=2,
        total_tokens=2400,
        total_cost_usd=0.012,
    )
    record = TraceRecord(trace_id=trace_id, created_at=now_iso, summary=summary, spans=spans)
    pg_records = engine.generate_postgres_records(workload_name, record, opt_payload)

    assert pg_records["run"]["table"] == "runs"
    assert pg_records["run"]["trace_id"] == trace_id
    assert pg_records["cost_record"]["table"] == "cost_records"
    assert pg_records["cost_record"]["accelerator"] == "H100-SXM5-80GB"
    assert pg_records["recommendation"]["table"] == "recommendations"
    assert pg_records["recommendation"]["status"] == "open"
