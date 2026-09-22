# `airun-action`: Automated AI Performance & FinOps PR Gate

The **`airun-action`** GitHub Action enables engineering teams to block AI serving performance regressions, latency spikes (p95/p99 TTFT), and GPU compute waste **directly in Pull Requests** before merging into `main`.

---

## 🚀 Quickstart

Add the following workflow to `.github/workflows/ai-performance-gate.yml`:

```yaml
name: AI Performance & FinOps Gate

on:
  pull_request:
    branches: [main]
    paths:
      - "model/**"
      - "serving/**"
      - "vllm/**"
      - "requirements.txt"

jobs:
  performance-gate:
    runs-on: ubuntu-latest
    steps:
      - name: Checkout Code
        uses: actions/checkout@v4

      - name: Run airun PR Performance Gate
        uses: sarkarbikram90/airun-action@v1
        with:
          config: "examples/benchmarks/benchmark.yaml"
          fail-on-regression: "true"
          github-token: ${{ secrets.GITHUB_TOKEN }}
```

---

## ⚙️ Action Inputs

| Input | Description | Required | Default |
| :--- | :--- | :---: | :--- |
| `config` | Path to declarative standard benchmark configuration YAML | No | `examples/benchmarks/benchmark.yaml` |
| `fail-on-regression` | Whether to fail the CI job if a gate threshold is breached (`true` / `false`) | No | `true` |
| `output-json` | Path to export the standardized JSON benchmark artifact | No | `airun-results.json` |
| `github-token` | GitHub token for posting PR comments and check runs | No | `""` |

---

## 📊 Action Outputs

| Output | Description | Example |
| :--- | :--- | :--- |
| `gate-status` | Overall evaluation result (`PASS` or `FAIL`) | `PASS` |
| `ttft-p95-ms` | Observed Time-To-First-Token p95 latency | `148.2` |
| `throughput-tps` | Token throughput across the workload | `812.0` |
| `cost-per-1m` | Projected serving cost per 1M tokens in USD | `$2.71` |

---

## 🔬 Benchmark Configuration Schema (`benchmark.yaml`)

```yaml
schema_version: "1.0"
benchmark_name: "vllm-l4-serving-baseline"
description: "vLLM serving regression evaluation on NVIDIA L4"

environment:
  accelerator: "l4"
  num_gpus: 1
  driver_version: "550.54.15"
  cuda_version: "12.4"

workload:
  model: "qwen3-8b"
  concurrency_levels: [1, 8, 32, 64]
  num_requests: 500
  warmup_requests: 20

engines:
  - name: "vllm"
    args: ["--enable-chunked-prefill", "--gpu-memory-utilization=0.90"]
  - name: "sglang"
    args: ["--enable-radix-cache"]

gate_thresholds:
  max_ttft_p95_ms: 160.0
  max_ttft_p99_ms: 220.0
  min_throughput_tokens_sec: 750.0
  max_cost_per_1m_tokens_usd: 3.00
```

---

## 🛡️ Pull Request Step Summary

When the action runs, it automatically renders a GitHub Step Summary:

```markdown
## 🚀 airun Performance & FinOps Gate: PASS

- **Benchmark**: `vllm-l4-serving-baseline`
- **Workload**: `qwen3-8b` on `L4`

| Serving Engine | TTFT p50 | TTFT p95 | Throughput | $/1M Tokens | Gate Status |
| :--- | :---: | :---: | :---: | :---: | :---: |
| **vLLM** | 71.2ms | 148.2ms | 812 tok/s | $2.71 | ✅ PASS |
| **SGLang** | 83.1ms | 172.4ms | 901 tok/s | $2.44 | ❌ FAIL |
```
