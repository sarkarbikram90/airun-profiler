"""Unit tests for Time-Window Correlation Engine."""

from __future__ import annotations

from airun.analysis.correlation import (
    FabricTelemetrySample,
    PhysicalTelemetrySample,
    TimeWindowCorrelator,
)
from airun.events.models import TraceRecord, TraceSpan


def test_correlate_span_with_samples() -> None:
    correlator = TimeWindowCorrelator(accelerator="h100", num_gpus=8)
    span = TraceSpan(
        trace_id="t1",
        span_id="s1",
        name="dataloader_batch_0",
        start_time="100.0",
        end_time="100.5",
        duration_ms=500.0,
    )
    samples = [
        PhysicalTelemetrySample(timestamp=100.1, sm_util_pct=32.0, pcie_tx_mbs=200.0),
        PhysicalTelemetrySample(timestamp=100.3, sm_util_pct=36.0, pcie_tx_mbs=250.0),
    ]

    res = correlator.correlate_span(span, samples)
    assert res["span_id"] == "s1"
    assert res["name"] == "dataloader_batch_0"
    assert res["avg_sm_util_pct"] == 34.0
    assert res["max_pcie_tx_mbs"] == 250.0


def test_diagnose_trace_dataloader_starvation() -> None:
    correlator = TimeWindowCorrelator(accelerator="h100", num_gpus=8)
    spans = [
        TraceSpan(
            trace_id="t_dl",
            span_id="s_dl",
            name="dataloader_worker_fetch",
            start_time="10.0",
            end_time="10.4",
            duration_ms=400.0,
        )
    ]
    record = TraceRecord(trace_id="t_dl", created_at="2026-09-07T00:00:00Z", spans=spans)

    diag = correlator.diagnose_trace(record, force_category="dataloader_starvation")
    assert diag.trace_id == "t_dl"
    assert diag.bottleneck_category == "dataloader_starvation"
    assert "Dataloader Starvation" in diag.primary_bottleneck
    assert diag.hourly_bleed_usd > 0
    assert diag.weekly_bleed_usd > diag.hourly_bleed_usd
    assert "pin_memory=True" in diag.remediation_action


def test_diagnose_trace_nccl_overhead() -> None:
    correlator = TimeWindowCorrelator(accelerator="h100", num_gpus=8)
    spans = [
        TraceSpan(
            trace_id="t_nccl",
            span_id="s_nccl",
            name="nccl_allreduce_barrier",
            start_time="20.0",
            end_time="20.2",
            duration_ms=200.0,
        )
    ]
    record = TraceRecord(trace_id="t_nccl", created_at="2026-09-07T00:00:00Z", spans=spans)

    diag = correlator.diagnose_trace(record, force_category="nccl_overhead")
    assert diag.bottleneck_category == "nccl_overhead"
    assert "NCCL_BUFFSIZE=16MB" in diag.remediation_action
    assert diag.hourly_bleed_usd > 0
    assert diag.is_estimated is True
    assert diag.telemetry_source == "architectural_estimate"
    assert "[ARCHITECTURAL ESTIMATE" in diag.symptom


def test_diagnose_trace_measured_hardware() -> None:
    correlator = TimeWindowCorrelator(accelerator="h100", num_gpus=8)
    spans = [
        TraceSpan(
            trace_id="t_real",
            span_id="s_real",
            name="training_step",
            start_time="10.0",
            end_time="10.5",
            duration_ms=500.0,
        )
    ]
    record = TraceRecord(trace_id="t_real", created_at="2026-09-07T00:00:00Z", spans=spans)
    samples = [
        PhysicalTelemetrySample(timestamp=10.1, sm_util_pct=28.0, pcie_tx_mbs=350.0),
        PhysicalTelemetrySample(timestamp=10.3, sm_util_pct=32.0, pcie_tx_mbs=380.0),
    ]

    diag = correlator.diagnose_trace(record, telemetry=samples)
    assert diag.is_estimated is False
    assert diag.telemetry_source == "measured_hardware"
    assert diag.avg_sm_util_pct == 30.0
    assert diag.bottleneck_category == "dataloader_starvation"
    assert "[ARCHITECTURAL ESTIMATE" not in diag.symptom


def test_diagnose_trace_healthy_optimal() -> None:
    correlator = TimeWindowCorrelator(accelerator="h100", num_gpus=8)
    spans = [
        TraceSpan(
            trace_id="t_good",
            span_id="s_good",
            name="optimized_forward_backward",
            start_time="10.0",
            end_time="10.5",
            duration_ms=500.0,
        )
    ]
    record = TraceRecord(trace_id="t_good", created_at="2026-09-07T00:00:00Z", spans=spans)
    samples = [
        PhysicalTelemetrySample(
            timestamp=10.1, sm_util_pct=88.0, pcie_tx_mbs=2500.0, nccl_wait_ms=5.0
        ),
        PhysicalTelemetrySample(
            timestamp=10.3, sm_util_pct=92.0, pcie_tx_mbs=2800.0, nccl_wait_ms=6.0
        ),
    ]

    diag = correlator.diagnose_trace(record, telemetry=samples)
    assert diag.is_estimated is False
    assert diag.telemetry_source == "measured_hardware"
    assert diag.bottleneck_category == "healthy_optimal"
    assert "Optimal Silicon Utilization" in diag.primary_bottleneck
    assert diag.hourly_bleed_usd == 0.0


def test_diagnose_trace_with_ebpf_fabric_telemetry() -> None:
    """Verify eBPF fabric congestion telemetry attributes NCCL stalls to PFC pause storms."""
    correlator = TimeWindowCorrelator(accelerator="h100", num_gpus=8)
    spans = [
        TraceSpan(
            trace_id="t_fabric",
            span_id="s_fabric",
            name="distributed_allreduce",
            start_time="50.0",
            end_time="50.8",
            duration_ms=800.0,
        )
    ]
    record = TraceRecord(trace_id="t_fabric", created_at="2026-09-07T00:00:00Z", spans=spans)
    telemetry = [
        PhysicalTelemetrySample(
            timestamp=50.1, sm_util_pct=62.0, pcie_tx_mbs=1200.0, nccl_wait_ms=45.0
        ),
        PhysicalTelemetrySample(
            timestamp=50.4, sm_util_pct=58.0, pcie_tx_mbs=1100.0, nccl_wait_ms=52.0
        ),
    ]
    fabric_samples = [
        FabricTelemetrySample(
            timestamp=50.2,
            interface="ib0",
            packet_drops=25,
            pfc_pause_rx=85,
            pfc_pause_tx=12,
            nccl_buffer_queue_depth_bytes=16777216,
        )
    ]

    diag = correlator.diagnose_trace(record, telemetry=telemetry, fabric_telemetry=fabric_samples)
    assert diag.bottleneck_category == "nccl_overhead"
    assert diag.fabric_congestion_detected is True
    assert diag.fabric_drops_total == 25
    assert "eBPF detected 25 packet drops and 85 PFC pause frames" in diag.symptom
    assert "In-kernel eBPF confirmed network fabric buffer overflow" in diag.root_cause
