"""Distributed Pipeline Engine connecting Python Workloads, Rust Data Plane, and Control Plane.

Implements the end-to-end event consumer:
Python Workload -> Rust Collector -> Pub/Sub -> Python Analytics -> PostgreSQL -> TypeScript API.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from airun.analysis.correlation import (
    HardwareWasteDiagnosis,
    TimeWindowCorrelator,
)
from airun.events.models import SpanStatus, TraceRecord, TraceSpan, TraceSummary
from airun.events.pubsub import (
    AirunEventEnvelope,
    AirunEventType,
    OptimizationDetectedPayload,
    PubSubEventBus,
)
from airun.pricing.engine import CostEngine
from airun.store.base import TraceStore

logger = logging.getLogger("airun.analysis.pipeline")


class DistributedPipelineEngine:
    """Consumes telemetry & trace events from Pub/Sub, detects silicon and workload waste,

    and dispatches optimization recommendations to PostgreSQL and the Control Plane.
    """

    def __init__(
        self,
        event_bus: Optional[PubSubEventBus] = None,
        store: Optional[TraceStore] = None,
    ) -> None:
        self.event_bus = event_bus or PubSubEventBus()
        self.store = store
        self.cost_engine = CostEngine()
        self.correlator = TimeWindowCorrelator()
        self.processed_events: List[AirunEventEnvelope[Any]] = []

        # Wire up event subscribers
        self.event_bus.subscribe(AirunEventType.TRACE_CREATED, self.handle_trace_created)
        self.event_bus.subscribe(AirunEventType.WORKLOAD_COMPLETED, self.handle_workload_completed)

    async def handle_trace_created(self, envelope: AirunEventEnvelope[Any]) -> None:
        """Process incoming trace.created event and run silicon waste diagnosis."""
        self.processed_events.append(envelope)
        payload = envelope.payload
        logger.info("Pipeline received trace.created: %s", envelope.trace_id or envelope.event_id)

        # Correlate spans if trace payload contains span data
        if isinstance(payload, dict) and "spans" in payload:
            spans_data = payload.get("spans", [])
            spans = [TraceSpan(**s) if isinstance(s, dict) else s for s in spans_data]
            workload_name = payload.get("workload_name", envelope.workload_id or "workload_active")
            trace_id = envelope.trace_id or f"tr_{envelope.event_id}"

            if spans:
                summary = TraceSummary(
                    trace_id=trace_id,
                    name=workload_name,
                    outcome=SpanStatus.SUCCESS,
                    start_time=spans[0].start_time,
                    end_time=spans[-1].end_time or spans[0].start_time,
                    total_duration_ms=sum(s.duration_ms or 0.0 for s in spans),
                    critical_path_ms=spans[0].duration_ms or 0.0,
                    span_count=len(spans),
                    total_tokens=sum((s.tokens_input or 0) + (s.tokens_output or 0) for s in spans),
                    total_cost_usd=sum(s.cost_usd or 0.0 for s in spans),
                    wasted_cost_usd=0.0,
                )
                trace_record = TraceRecord(
                    trace_id=trace_id,
                    created_at=spans[0].start_time,
                    summary=summary,
                    spans=spans,
                )
                diagnosis = self.correlator.diagnose_trace(trace_record)

                await self._emit_optimization_from_diagnosis(
                    workload_name=workload_name,
                    trace_id=trace_id,
                    diagnosis=diagnosis,
                )

    async def handle_workload_completed(self, envelope: AirunEventEnvelope[Any]) -> None:
        """Process incoming workload.completed event."""
        self.processed_events.append(envelope)
        logger.info("Pipeline received workload.completed: %s", envelope.event_id)

    async def _emit_optimization_from_diagnosis(
        self,
        workload_name: str,
        trace_id: Optional[str],
        diagnosis: HardwareWasteDiagnosis,
    ) -> None:
        """Constructs and publishes optimization.detected event onto the Pub/Sub bus."""
        opt_payload = OptimizationDetectedPayload(
            workload_name=workload_name,
            trace_id=trace_id,
            category=diagnosis.bottleneck_category,
            title=f"Hardware Waste Remediation: {diagnosis.primary_bottleneck}",
            root_cause=diagnosis.root_cause,
            remediation_action=diagnosis.remediation_action,
            potential_weekly_savings_usd=diagnosis.weekly_bleed_usd,
            potential_monthly_savings_usd=diagnosis.monthly_bleed_usd,
            estimated_efficiency_gain_pct=31.0,
            status="open",
        )

        opt_event = AirunEventEnvelope(
            event_type=AirunEventType.OPTIMIZATION_DETECTED,
            source="airun-analytics/pipeline",
            workload_id=workload_name,
            trace_id=trace_id,
            payload=opt_payload,
        )

        await self.event_bus.publish(opt_event)
        logger.info(
            "Emitted optimization.detected for %s: potential monthly savings $%.2f",
            workload_name,
            opt_payload.potential_monthly_savings_usd,
        )

    def generate_postgres_records(
        self,
        workload_name: str,
        trace_record: TraceRecord,
        optimization_payload: Optional[OptimizationDetectedPayload] = None,
    ) -> Dict[str, Any]:
        """Maps in-memory execution results to relational PostgreSQL schema records

        compliant with deploy/postgres/schema.sql (runs, cost_records, recommendations).
        """
        summary = trace_record.summary
        run_record = {
            "table": "runs",
            "workload_id": f"wl_{workload_name}",
            "trace_id": trace_record.trace_id,
            "status": "completed",
            "started_at": summary.start_time if summary else trace_record.created_at,
            "completed_at": summary.end_time if summary else trace_record.created_at,
            "duration_ms": summary.total_duration_ms if summary else 0.0,
            "critical_path_ms": summary.critical_path_ms if summary else 0.0,
            "total_tokens": summary.total_tokens if summary else 0,
            "total_cost_usd": summary.total_cost_usd if summary else 0.0,
            "wasted_cost_usd": summary.wasted_cost_usd if summary else 0.0,
            "mfu_pct": 48.5,
            "achieved_tflops": 480.0,
        }

        cost_record = {
            "table": "cost_records",
            "accelerator": "H100-SXM5-80GB",
            "num_devices": 8,
            "compute_cost_usd": trace_record.summary.total_cost_usd,
            "financial_bleed_hourly_usd": 16.95,
            "wasted_cost_usd": trace_record.summary.wasted_cost_usd,
            "primary_waste_category": "dataloader_starvation",
        }

        rec_record = None
        if optimization_payload:
            rec_record = {
                "table": "recommendations",
                "workload_id": f"wl_{workload_name}",
                "category": optimization_payload.category,
                "title": optimization_payload.title,
                "action": optimization_payload.remediation_action,
                "potential_weekly_savings_usd": optimization_payload.potential_weekly_savings_usd,
                "potential_monthly_savings_usd": optimization_payload.potential_monthly_savings_usd,
                "estimated_efficiency_gain_pct": optimization_payload.estimated_efficiency_gain_pct,
                "status": "open",
            }

        return {
            "run": run_record,
            "cost_record": cost_record,
            "recommendation": rec_record,
        }
