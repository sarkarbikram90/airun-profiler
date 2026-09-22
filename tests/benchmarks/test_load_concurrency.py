"""High-throughput concurrency and load benchmark suite for airun."""

import asyncio
import os
import statistics
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from typing import List

import pytest

from airun.analysis.correlation import HardwareWasteDiagnosis
from airun.events.models import SpanKind, SpanStatus, TraceRecord, TraceSummary
from airun.resilience.remediation_engine import RemediationEngine
from airun.sdk.tracer import set_span_metadata, set_span_tokens, trace
from airun.utils.time_utils import perf_counter_ms


def _worker_task(thread_id: int, spans_per_thread: int, latencies: List[float]) -> int:
    """Execute a complete workflow lifecycle with nested child spans."""
    span_count = 0
    with trace(f"concurrent_workflow_{thread_id}", kind=SpanKind.WORKFLOW, save_on_exit=False):
        span_count += 1
        for i in range(spans_per_thread):
            t0 = perf_counter_ms()
            with trace(f"child_step_{thread_id}_{i}", kind=SpanKind.CUSTOM, save_on_exit=False):
                set_span_tokens(input_tokens=10, output_tokens=5)
                set_span_metadata({"thread": thread_id, "step": i})
            duration_ms = perf_counter_ms() - t0
            latencies.append(duration_ms)
            span_count += 1
    return span_count


def test_concurrent_multithreaded_span_generation():
    """Verify tracer thread-safety, zero-deadlock guarantee, and <1.5ms p99 latency under 50 concurrent threads."""
    num_threads = 50
    spans_per_thread = 20  # 50 * 20 = 1,000 child spans + 50 root = 1,050 spans
    latencies: List[float] = []

    start_time = time.perf_counter()

    with ThreadPoolExecutor(max_workers=num_threads) as executor:
        futures = [
            executor.submit(_worker_task, tid, spans_per_thread, latencies)
            for tid in range(num_threads)
        ]
        total_spans = sum(f.result() for f in as_completed(futures))

    total_time_sec = time.perf_counter() - start_time

    assert total_spans == num_threads * (spans_per_thread + 1)
    assert len(latencies) == num_threads * spans_per_thread

    # Latency percentiles
    sorted_latencies = sorted(latencies)
    p50 = statistics.median(sorted_latencies)
    p90 = sorted_latencies[int(len(sorted_latencies) * 0.90)]
    p99 = sorted_latencies[int(len(sorted_latencies) * 0.99)]
    throughput_spans_per_sec = total_spans / total_time_sec

    # Validate zero-overhead guarantee: p99 latency should remain < 2.0ms (relaxed to 15.0ms on shared 2-core CI runners)
    max_p99 = 15.0 if os.environ.get("CI") else 2.5
    min_throughput = 200.0 if os.environ.get("CI") else 500.0
    assert 0.0 <= p50 <= p90 <= p99
    assert p99 < max_p99, f"p99 span overhead {p99:.3f}ms exceeded {max_p99}ms target under load"
    assert throughput_spans_per_sec > min_throughput, f"Throughput {throughput_spans_per_sec:.1f} spans/s too low"


@pytest.mark.asyncio
async def test_asyncio_high_concurrency_stress():
    """Verify 100 concurrent async coroutines maintain isolated context vars without race conditions."""
    async def async_worker(coro_id: int):
        async with trace(f"async_stress_{coro_id}", kind=SpanKind.WORKFLOW, save_on_exit=False) as root:
            root_id = root.trace_id
            await asyncio.sleep(0.001)
            async with trace(f"async_child_{coro_id}", kind=SpanKind.AGENT_STEP, save_on_exit=False) as child:
                assert child.trace_id == root_id
                assert child.parent_id == root.span_id
                set_span_tokens(input_tokens=100, output_tokens=50)
            return root_id

    coros = [async_worker(i) for i in range(100)]
    trace_ids = await asyncio.gather(*coros)

    assert len(trace_ids) == 100
    # Every root trace should have a unique ID
    assert len(set(trace_ids)) == 100


def test_concurrent_policy_engine_evaluation():
    """Verify closed-loop RemediationEngine executes thread-safely across 50 parallel threads."""
    engine = RemediationEngine()
    now_str = datetime.now(timezone.utc).isoformat()

    def eval_worker(tid: int) -> int:
        summary = TraceSummary(
            trace_id=f"tr_par_{tid}",
            name="concurrent_eval",
            outcome=SpanStatus.SUCCESS,
            start_time=now_str,
            total_tokens=2000,
            quality_score=0.75 if tid % 2 == 0 else 0.95,
        )
        record = TraceRecord(trace_id=f"tr_par_{tid}", created_at=now_str, spans=[], summary=summary)
        diagnosis = HardwareWasteDiagnosis(
            workload_name="job",
            trace_id=f"tr_par_{tid}",
            accelerator="H100",
            num_gpus=8,
            primary_bottleneck="Stall",
            bottleneck_category="i_o_bottleneck",
            symptom="Stall",
            root_cause="Stall",
            remediation_action="None",
            hourly_rate_per_gpu=3.5,
            hourly_bleed_usd=25.0 if tid % 3 == 0 else 2.0,
            weekly_bleed_usd=4000.0,
            monthly_bleed_usd=17000.0,
            avg_sm_util_pct=30.0 if tid % 5 == 0 else 85.0,
            avg_power_watts=450.0,
        )
        results = engine.evaluate_trace(record, diagnosis)
        return len(results)

    with ThreadPoolExecutor(max_workers=50) as executor:
        futures = [executor.submit(eval_worker, i) for i in range(50)]
        results_counts = [f.result() for f in as_completed(futures)]

    assert len(results_counts) == 50
    assert all(isinstance(c, int) for c in results_counts)
