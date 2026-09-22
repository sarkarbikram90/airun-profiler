"""Reproducible micro-benchmark measuring airun @trace decorator and context manager overhead.

Measures in-memory span allocation, context propagation, and metadata tracking latency
across 100,000 iterations to calculate exact p50, p90, p95, and p99 percentiles in microseconds.
"""

from __future__ import annotations

import json
import platform
import statistics
import sys
import time
from pathlib import Path

# Add project root to sys.path
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from airun.events.models import SpanKind  # noqa: E402
from airun.sdk.tracer import set_span_metadata, set_span_tokens, trace  # noqa: E402


def benchmark_context_manager(iterations: int = 50_000) -> list[float]:
    """Measure raw context manager overhead with token and metadata setting."""
    latencies_us: list[float] = []

    # Warmup
    for _ in range(500):
        with trace("warmup", kind=SpanKind.CUSTOM, save_on_exit=False):
            pass

    for i in range(iterations):
        t0 = time.perf_counter_ns()
        with trace(f"bench_span_{i}", kind=SpanKind.CUSTOM, save_on_exit=False):
            set_span_tokens(input_tokens=100, output_tokens=25)
            set_span_metadata({"iteration": i, "batch": "test"})
        duration_us = (time.perf_counter_ns() - t0) / 1_000.0
        latencies_us.append(duration_us)

    return latencies_us


def benchmark_decorator(iterations: int = 50_000) -> list[float]:
    """Measure function decorator overhead."""
    latencies_us: list[float] = []

    @trace(kind=SpanKind.LLM, model="mock-model", provider="test", save_on_exit=False)
    def dummy_inference(val: int) -> int:
        return val * 2

    # Warmup
    for _ in range(500):
        dummy_inference(0)

    for i in range(iterations):
        t0 = time.perf_counter_ns()
        dummy_inference(i)
        duration_us = (time.perf_counter_ns() - t0) / 1_000.0
        latencies_us.append(duration_us)

    return latencies_us


def compute_metrics(latencies: list[float]) -> dict[str, float]:
    """Compute statistics percentiles from sample list."""
    sorted_l = sorted(latencies)
    n = len(sorted_l)
    return {
        "count": n,
        "mean_us": round(statistics.mean(sorted_l), 2),
        "min_us": round(sorted_l[0], 2),
        "p50_us": round(statistics.median(sorted_l), 2),
        "p90_us": round(sorted_l[int(n * 0.90)], 2),
        "p95_us": round(sorted_l[int(n * 0.95)], 2),
        "p99_us": round(sorted_l[int(n * 0.99)], 2),
        "max_us": round(sorted_l[-1], 2),
    }


def main():
    print("=" * 65)
    print("  airun Reproducible Overhead Benchmark")
    print("=" * 65)
    print(f"  * Python:  {platform.python_version()} ({platform.python_implementation()})")
    print(f"  * OS:      {platform.system()} {platform.release()} ({platform.machine()})")
    print(f"  * CPU:     {platform.processor() or 'x86_64'}")
    print("=" * 65)

    iterations = 50_000
    print(f"[*] Running Context Manager Benchmark ({iterations:,} iterations)...")
    cm_latencies = benchmark_context_manager(iterations)
    cm_metrics = compute_metrics(cm_latencies)

    print(f"[*] Running Function Decorator Benchmark ({iterations:,} iterations)...")
    dec_latencies = benchmark_decorator(iterations)
    dec_metrics = compute_metrics(dec_latencies)

    print("\nBenchmark Results (Microseconds - us):")
    print("-" * 65)
    print(f"{'Metric':<18} | {'with trace()':<18} | {'@trace decorator':<18}")
    print("-" * 65)
    for k in ["p50_us", "p90_us", "p95_us", "p99_us", "mean_us", "min_us"]:
        label = k.replace("_us", "").upper()
        print(f"{label:<18} | {cm_metrics[k]:>15.2f} us | {dec_metrics[k]:>15.2f} us")
    print("-" * 65)

    results = {
        "benchmark": "trace_overhead",
        "iterations_per_suite": iterations,
        "environment": {
            "python": platform.python_version(),
            "os": f"{platform.system()} {platform.release()}",
            "arch": platform.machine(),
        },
        "context_manager": cm_metrics,
        "decorator": dec_metrics,
        "verified_overhead_sub_20us": cm_metrics["p95_us"] < 20.0 and dec_metrics["p95_us"] < 20.0,
    }

    results_dir = ROOT / "benchmarks" / "results"
    results_dir.mkdir(parents=True, exist_ok=True)
    out_file = results_dir / "trace_overhead.json"
    out_file.write_text(json.dumps(results, indent=2), encoding="utf-8")
    print(f"\n[+] Results saved to {out_file.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
