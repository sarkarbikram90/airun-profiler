"""Unit tests for Time-Window Correlation Engine."""

from __future__ import annotations

from airun.analysis.correlation import (
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
