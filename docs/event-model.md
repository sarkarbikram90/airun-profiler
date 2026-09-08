# Event Model & Telemetry Schemas

`airun` represents AI execution paths, hardware telemetry, and distributed pub/sub messages as strictly-typed Pydantic v2 schemas aligned with OpenTelemetry conventions.

---

## 1. Trace Span Schema (`TraceSpan`)

```json
{
  "trace_id": "9f2c184e0f314842a2789123456789ab",
  "span_id": "3a1b2c3d4e5f6789",
  "parent_id": "1a2b3c4d5e6f7890",
  "name": "planner_llm_call",
  "kind": "llm",
  "start_time": "2026-09-07T12:00:00.000000+00:00",
  "end_time": "2026-09-07T12:00:00.350000+00:00",
  "duration_ms": 350.0,
  "status": "success",
  "provider": "openai",
  "model": "gpt-4o",
  "tokens_input": 1420,
  "tokens_output": 380,
  "cost_usd": 0.00735,
  "retry_count": 0,
  "quality_score": 0.95,
  "evaluation_metrics": {
    "correctness": 0.96,
    "evaluator": "human_curated"
  },
  "accelerator_type": "H100_SXM5",
  "power_watts": 700.0,
  "energy_joules": 245.0,
  "energy_kwh": 0.000068,
  "energy_cost_usd": 0.000008,
  "error": null,
  "metadata": {
    "temperature": 0.2
  }
}
```

---

## 2. Span Kinds (`SpanKind`) & Statuses (`SpanStatus`)

| Kind | Description |
|---|---|
| `workflow` | The top-level root operation or end-to-end task |
| `agent_step` | An intermediate reasoning, planning, or decision block |
| `llm` | A language model generation or embedding call |
| `tool` | An external tool or function invocation |
| `search` | Web search or retrieval operation |
| `db` | Vector database or relational storage query |
| `http` | External HTTP API request |
| `custom` | Any custom user-defined execution unit |

### Statuses (`SpanStatus`)
- `success`: Completed without errors.
- `failure`: Encountered an unhandled exception.
- `timeout`: Exceeded maximum allowable timeout limit.
- `retry`: Step was retried due to transient error.
- `partial_success`: Overall workflow succeeded despite partial child step failures.

---

## 3. The 4-Layer Golden Signals Hierarchy (`GoldenSignals`)

Organizes telemetry into four operational tiers spanning FinOps, ML Engineering, and Operations:

```json
{
  "economics": {
    "cost_per_effective_gpu_hour_usd": 3.85,
    "cost_per_1m_tokens_usd": 4.12,
    "cost_per_successful_outcome_usd": 0.018,
    "financial_bleed_hourly_usd": 42.50,
    "total_wasted_spend_usd": 12.80,
    "waste_percentage": 28.5
  },
  "efficiency": {
    "mfu_pct": 38.2,
    "achieved_tflops": 378.0,
    "gpu_sm_utilization_pct": 52.4,
    "memory_bandwidth_utilization_pct": 68.1,
    "pcie_utilization_pct": 44.0,
    "effective_utilization_pct": 49.6
  },
  "reliability": {
    "job_failure_rate_pct": 2.1,
    "mean_time_to_recovery_ms": 420.0,
    "retry_count": 3,
    "checkpoint_frequency_min": 30.0,
    "recovery_overhead_cost_usd": 1.45
  },
  "infrastructure": {
    "power_draw_watts": 680.0,
    "thermal_throttling": false,
    "pcie_error_count": 0,
    "network_retransmits_pct": 0.02,
    "nvlink_throughput_gbs": 850.0,
    "pue": 1.20
  }
}
```

---

## 4. Hardware Telemetry Sample (`DCGMSample`)

High-frequency 10Hz sampling captured from NVIDIA DCGM/NVML in the Rust data plane:

```json
{
  "timestamp": "2026-09-07T12:00:00.100000Z",
  "gpu_id": 0,
  "node_name": "gke-accelerator-h100-pool-node-4",
  "sm_util_pct": 64.2,
  "memory_used_mb": 62400.0,
  "memory_total_mb": 81920.0,
  "temperature_c": 58.0,
  "power_watts": 685.0,
  "pcie_tx_bytes_sec": 482000000.0,
  "pcie_rx_bytes_sec": 790000000.0
}
```

---

## 5. Distributed Pub/Sub Event Backbone (`EventEnvelope`)

Structured envelope unifying asynchronous event dispatch across Python, Rust, and TypeScript:

```json
{
  "event_id": "evt_01J7K3M4N5P6Q7R8S9T0V1W2X3",
  "event_type": "workload.completed",
  "timestamp": "2026-09-07T12:00:01.420000Z",
  "source": "airun-collector-daemonset",
  "payload": {
    "workload_id": "wkld_customer_support_v2",
    "trace_id": "9f2c184e0f314842a2789123456789ab",
    "total_cost_usd": 0.0142,
    "wasted_spend_usd": 0.0,
    "quality_score": 0.95
  }
}
```

### The 10 Canonical Event Types
1. `workload.started` / `workload.completed`
2. `trace.created`
3. `gpu.alert`
4. `provider.degraded` / `provider.failed`
5. `dr.drill.started` / `dr.drill.completed`
6. `optimization.detected` / `optimization.applied`

