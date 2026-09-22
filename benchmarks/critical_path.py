"""Reproducible benchmark measuring airun interval DAG critical path resolution latency.

Measures graph construction and interval union scheduling across DAGs with up to 100 parallel spans.
"""

from __future__ import annotations

import json
import statistics
import sys
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from airun.events.models import SpanKind, TraceSpan  # noqa: E402
from airun.graph.builder import ExecutionGraph  # noqa: E402
from airun.graph.critical_path import compute_critical_path  # noqa: E402


def generate_dag_spans(num_parallel: int = 20) -> list[TraceSpan]:
    """Create a root span with parallel child tool calls."""
    base = datetime.now(timezone.utc)
    root_start = base.isoformat()
    root_end = (base + timedelta(milliseconds=150)).isoformat()

    spans = [
        TraceSpan(
            span_id="root",
            trace_id="bench_dag",
            parent_id=None,
            name="orchestrator",
            kind=SpanKind.WORKFLOW,
            start_time=root_start,
            end_time=root_end,
            duration_ms=150.0,
        )
    ]

    for i in range(num_parallel):
        # Stagger start and end times to form overlapping intervals
        s_offset = 10 + (i % 5) * 5
        duration = 20 + (i % 10) * 8
        s_time = (base + timedelta(milliseconds=s_offset)).isoformat()
        e_time = (base + timedelta(milliseconds=s_offset + duration)).isoformat()
        spans.append(
            TraceSpan(
                span_id=f"tool_{i}",
                trace_id="bench_dag",
                parent_id="root",
                name=f"vector_search_{i}",
                kind=SpanKind.TOOL,
                start_time=s_time,
                end_time=e_time,
                duration_ms=float(duration),
            )
        )

    return spans


def main():
    print("=" * 65)
    print("  airun Critical Path DAG Resolution Benchmark")
    print("=" * 65)

    iterations = 2_000
    span_sizes = [10, 50, 100]
    all_results = {}

    for size in span_sizes:
        spans = generate_dag_spans(size)
        latencies_us: list[float] = []

        # Warmup
        for _ in range(50):
            graph = ExecutionGraph(spans)
            compute_critical_path(graph)

        for _ in range(iterations):
            t0 = time.perf_counter_ns()
            graph = ExecutionGraph(spans)
            crit_ms, _ = compute_critical_path(graph)
            latencies_us.append((time.perf_counter_ns() - t0) / 1_000.0)

        s = sorted(latencies_us)
        n = len(s)
        stats = {
            "p50_us": round(statistics.median(s), 2),
            "p90_us": round(s[int(n * 0.90)], 2),
            "p95_us": round(s[int(n * 0.95)], 2),
            "p99_us": round(s[int(n * 0.99)], 2),
            "mean_us": round(statistics.mean(s), 2),
            "computed_critical_path_ms": round(crit_ms, 2),
        }
        all_results[f"{size}_spans"] = stats
        print(f"[*] {size:>3} parallel spans: p50={stats['p50_us']:>6.2f} us | p90={stats['p90_us']:>6.2f} us | p99={stats['p99_us']:>6.2f} us (crit_path={crit_ms:.1f}ms)")

    results_dir = ROOT / "benchmarks" / "results"
    results_dir.mkdir(parents=True, exist_ok=True)
    out_file = results_dir / "critical_path.json"
    out_file.write_text(json.dumps(all_results, indent=2), encoding="utf-8")
    print(f"\n[+] Results saved to {out_file.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
