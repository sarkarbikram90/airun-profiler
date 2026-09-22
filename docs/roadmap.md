# Strategic Roadmap: From Observability to Engineering Infrastructure

```text
Observe → Diagnose → Quantify Economics → Optimize → Replay → Verify (CI Gate)
```

## `v0.1.7` — Core Wedge Release (Current)
- [x] **Trace -> GPU -> Root Cause Engine (`airun diagnose`)**: Correlating logical trace spans with physical silicon bottlenecks and financial impact.
- [x] **Enterprise Money Leak Audit (`airun money-leak`)**: Recoverable waste breakdown with standalone HTML report export and data source credibility indicators.
- [x] **Standardized GPU Efficiency Score (0-100)**: Mathematically defensible score across SM, memory bandwidth, MFU, and bus throughput with penalty deductions.
- [x] **Inference Benchmark Suite (`airun bench`)**: vLLM, SGLang, and TensorRT-LLM comparative benchmarking.
- [x] **Agent Workflow & MCP Inefficiency Analyzer (`airun agent analyze`)**: Detecting duplicate queries, model escalation, and tool loops.
- [x] **Zero-Setup Local Trace Seeding**: Automatic offline demo trace creation for instant first-run experience.
- [x] **Crates.io Trusted Publishing via OIDC**: Automated tokenless publishing via `rust-lang/crates-io-auth-action@v1`.

---

## `v0.2.0` — Proof (Next Milestone)
- [ ] **vLLM Deep Reference Integration**: First-class reference serving engine profiler capturing queue time, chunked prefill, TTFT, TPOT, KV-cache block allocation, and GPU power draw.
- [ ] **Empirical Infrastructure Case Studies**: 3 public reproducible case studies with raw telemetry fixtures (`docs/case-studies/`).
- [ ] **Defensible GPU Efficiency Score Specification**: Mathematical proofs, weight rationale, and calibration matrix (`docs/gpu-efficiency-score.md`).
- [ ] **Reproducible Benchmark Standard (`airun-bench/`)**: Standardized `benchmark.yaml` configuration format and public benchmark dataset.

---

## `v0.3.0` — Regression (CI Performance Gates)
- [ ] **Official GitHub Action (`sarkarbikram90/airun-action@v1`)**: Automatic PR performance checks with rich markdown summary comments.
- [ ] **Cost & Latency Performance Budgets**: Enforce strict CI exit codes on cost/request (+10%), TTFT p95 (+15%), or throughput degradation.
- [ ] **Quality Regression Gate**: Eval-driven quality delta verification alongside cost delta before merging PRs.

---

## `v0.4.0` — Optimization (`airun replay`)
- [ ] **Trace Replay Engine (`airun replay trace.json`)**: Replay production traces against candidate models or engine configurations to test hypothetical cost/latency savings.
- [ ] **Automated Model Routing & Quantization Advisor**: Specific model downsizing recommendations with empirical quality preservation guarantees.
- [ ] **vLLM / SGLang Parameter Tuner**: Automatic suggestions for `gpu_memory_utilization`, `max_num_seqs`, and prefix caching flags based on observed traces.

---

## `v0.5.0` — Agent Infrastructure
- [ ] **Deep MCP Server Observability**: Native Model Context Protocol server instrumentation and traffic monitoring.
- [ ] **Agent Execution DAG Pruning**: Automatic detection of context bloat, runaway tool loops, and recursive agent amplification.
- [ ] **Agent FinOps & ROI Modeling**: Measuring cost-per-successful-agent-task across multi-turn reasoning loops.

---

## `v1.0` — Production Category Leader
- [ ] Complete closed-loop workflow:
  $$\text{Install} \longrightarrow \text{Observe} \longrightarrow \text{Diagnose} \longrightarrow \text{Quantify} \longrightarrow \text{Optimize} \longrightarrow \text{Verify}$$
  tested, validated, and battle-hardened against multi-node production clusters.
