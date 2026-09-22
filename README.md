# AI Infrastructure Performance Engineering & GPU FinOps (`airun`)

<p align="center">
  <a href="https://github.com/sarkarbikram90/airun-profiler/actions/workflows/ci.yml"><img src="https://github.com/sarkarbikram90/airun-profiler/actions/workflows/ci.yml/badge.svg" alt="CI"></a>
  <a href="https://pypi.org/project/airun-profiler/"><img src="https://img.shields.io/pypi/v/airun-profiler?color=blue&logo=pypi&logoColor=white" alt="PyPI"></a>
  <a href="https://crates.io/crates/airun-collector"><img src="https://img.shields.io/crates/v/airun-collector.svg?color=orange&logo=rust&logoColor=white" alt="crates.io"></a>
  <a href="https://docs.rs/airun-collector"><img src="https://img.shields.io/docsrs/airun-collector?logo=docs.rs" alt="docs.rs"></a>
  <a href="https://pepy.tech/projects/airun-profiler"><img src="https://api.pepy.tech/badge/airun-profiler/month" alt="Downloads"></a>
  <a href="https://github.com/sarkarbikram90/airun-profiler"><img src="https://img.shields.io/github/stars/sarkarbikram90/airun-profiler?style=social" alt="Stars"></a>
  <a href="LICENSE"><img src="https://img.shields.io/badge/License-Apache_2.0-blue.svg" alt="License"></a>
  <a href="benchmarks/"><img src="https://img.shields.io/badge/Overhead-%3C20%CE%BCs-success.svg" alt="Overhead"></a>
  <a href="https://github.com/astral-sh/ruff"><img src="https://img.shields.io/badge/code%20style-ruff-000000.svg" alt="Ruff"></a>
</p>

<p align="center">
  <a href="pyproject.toml"><img src="https://img.shields.io/badge/Python-3.11+-3776AB.svg?logo=python&logoColor=white" alt="Python"></a>
  <a href="crates/airun-collector"><img src="https://img.shields.io/badge/Rust-Data%20Plane-DEA584.svg?logo=rust&logoColor=black" alt="Rust Data Plane"></a>
  <a href="packages/control-plane"><img src="https://img.shields.io/badge/TypeScript-Control%20Plane-3178C6.svg?logo=typescript&logoColor=white" alt="TypeScript Control Plane"></a>
  <a href="https://developer.nvidia.com/dcgm"><img src="https://img.shields.io/badge/NVIDIA-DCGM%20%26%20NVML-76B900.svg?logo=nvidia&logoColor=white" alt="NVIDIA DCGM"></a>
  <a href="docs/gcp-gke-deployment-guide.md"><img src="https://img.shields.io/badge/Kubernetes-GKE%20DaemonSet-326CE5.svg?logo=kubernetes&logoColor=white" alt="GCP GKE"></a>
  <a href="docs/aws-eks-deployment-guide.md"><img src="https://img.shields.io/badge/Kubernetes-EKS%20DaemonSet-FF9900.svg?logo=kubernetes&logoColor=white" alt="AWS EKS"></a>
  <a href="docs/azure-aks-deployment-guide.md"><img src="https://img.shields.io/badge/Kubernetes-AKS%20DaemonSet-0078D4.svg?logo=kubernetes&logoColor=white" alt="Azure AKS"></a>
  <a href="deploy/helm/airun-data-plane"><img src="https://img.shields.io/badge/Helm-v3-0F1689.svg?logo=helm&logoColor=white" alt="Helm"></a>
  <a href="src/airun/exporters/otlp.py"><img src="https://img.shields.io/badge/OpenTelemetry-OTLP%20Native-F5A800.svg?logo=opentelemetry&logoColor=white" alt="OpenTelemetry"></a>
</p>

<p align="center">
  <code>ai-infrastructure</code> • 
  <code>gpu-finops</code> • 
  <code>nvidia-dcgm</code> • 
  <code>h100-sxm5</code> • 
  <code>vllm-benchmarking</code> • 
  <code>sglang</code> • 
  <code>gpu-efficiency-score</code> • 
  <code>circuit-breakers</code> • 
  <code>disaster-recovery</code>
</p>

---

> **The Core Wedge:** `airun` tells you why an AI workload is expensive or slow by connecting the logical AI trace to the physical silicon bottlenecks causing it.

```text
               +-------------------------------------------------------------+
               |                  THE AIRUN 5-PILLAR ARCHITECTURE            |
               +-------------------------------------------------------------+
               |                                                             |
   [ PROFILE ] |  Universal Tracing  *  NVIDIA DCGM Telemetry  *  Token DAG  |
               |  Measure exact execution spans, SM cycles, PCIe & NVLink    |
               +------------------------------+------------------------------+
                                              |
               +------------------------------v------------------------------+
  [ DIAGNOSE ] |  Trace -> GPU -> Root Cause  *  GPU Efficiency Score (0-100)|
               |  airun diagnose <trace-id> --accelerator h100               |
               +------------------------------+------------------------------+
                                              |
               +------------------------------v------------------------------+
 [ ECONOMICS ] |  Executive Money Leak Audit  *  Compute & Power Waste $/mo  |
               |  airun money-leak --spend 184720 --export audit.html        |
               +------------------------------+------------------------------+
                                              |
               +------------------------------v------------------------------+
  [ OPTIMIZE ] |  Inference Benchmark (vLLM, SGLang, TRT-LLM) * Pareto Front |
               |  airun bench --model qwen3-8b --gpu l4                      |
               +------------------------------+------------------------------+
                                              |
               +------------------------------v------------------------------+
    [ VERIFY ] |  Automated Remediation Policies  *  DR Fault Drills & Breaker|
               |  airun policy check  *  airun dr drill                      |
               +-------------------------------------------------------------+
```

| Question | Answer |
| :--- | :--- |
| **1. What is it?** | An open-source, local-first **AI Infrastructure Performance Engineering & GPU FinOps Platform** that bridges the gap between physical silicon telemetry (NVIDIA DCGM / NVLink / PCIe), LLM token economics, multi-agent execution graphs, and automated multi-provider failover. |
| **2. Who is it for?** | **AI Engineers**, **MLOps / Platform Engineers**, and **Engineering Leaders (CTOs/CFOs)** operating production LLM pipelines, autonomous multi-agent systems, or distributed GPU training/inference clusters. |
| **3. Why does it exist?** | Traditional APMs (Datadog, New Relic) only see generic HTTP spans. They cannot correlate GPU streaming multiprocessor (SM) stalls or PCIe Gen1 throttling to wasted compute dollars, cannot compute Model FLOPs Utilization (MFU), cannot detect prompt context bloat, and cannot benchmark serving engines. |
| **4. How to install?** | `pip install airun-profiler` (Python SDK & CLI) <br> `cargo install airun-collector` (High-frequency Rust node telemetry daemon) |
| **5. What does it catch?** | Run `airun diagnose` for instant Trace-to-GPU root cause analysis, `airun money-leak` to audit enterprise recoverable waste, and `airun bench` to benchmark vLLM vs SGLang. |

### 1. Signature Command: `airun diagnose` (Trace -> GPU -> Root Cause)

```text
$ airun diagnose demo --accelerator h100

+--------------------------- AIRUN DIAGNOSTIC ---------------------------+
| Workflow: research_agent_workflow                                      |
| Duration: 0.28s                                                        |
| Cost: $0.0081                                                          |
| GPU: H100 SXM                                                          |
| GPU utilization: 32%                                                   |
| SM active: 29%                                                         |
| PCIe RX: 1.1 GB/s                                                      |
| CPU utilization: 55%                                                   |
| GPU Efficiency: [#####---------------] 24/100                          |
|                                                                        |
| ROOT CAUSE ----------------------------------------                    |
| Host DataLoader starvation (CPU/IO Bound)                              |
|                                                                        |
| EVIDENCE ------------------------------------------                    |
| * GPU SM active cycles stalled at 29.0% (idle wait)                    |
| * PCIe Host-to-Device RX bus at 1.1 GB/s (<5% bus capacity)            |
| * CPU worker threads saturated at 55.0% during mini-batch dispatch     |
|                                                                        |
| FINANCIAL IMPACT ----------------------------------                    |
| Current cost:    $0.0081/request                                       |
| Estimated waste: $0.0034/request (42.0%)                               |
| Monthly waste:   $1,700.00                                             |
|                                                                        |
| RECOMMENDATION ------------------------------------                    |
| [OK] Increase DataLoader workers, set pin_memory=True, prefetch tensors|
| [OK] Pin CPU worker threads to local NUMA node sockets                 |
|                                                                        |
| EXPECTED RESULT -----------------------------------                    |
| Gpu Utilization    32% -> ~74%                                         |
| Cost Per Request   -42%                                                |
| Throughput         +51%                                                |
+------------------------------------------------------------------------+
```

### 2. Signature Command: `airun money-leak` (Executive Financial Bleed Audit)

```text
$ airun money-leak --spend 184720 --export report.html

+------------------ AIRUN MONEY LEAK ------------------+
| Monthly AI Infrastructure Spend   $184,720           |
| Recoverable Waste                 $41,932 (22.7%)    |
|                                                      |
| TOP LEAKS ------------------------------------------ |
| $14,820  GPU starvation                              |
| $ 9,410  oversized model selection                   |
| $ 6,280  redundant agent/tool calls                  |
| $ 5,731  KV-cache misses                             |
| $ 3,921  retry amplification                         |
| $ 1,770  idle GPU capacity                           |
|                                                      |
| TOP RECOMMENDATION --------------------------------- |
| Route low-complexity requests to smaller model       |
| Projected savings: $9,410/month                      |
+------------------------------------------------------+

[+] Executive Money Leak report saved to report.html
```

### 3. Signature Command: `airun bench` (Inference Engine Showdown)

```text
$ airun bench --model qwen3-8b --gpu l4

            AIRUN BENCHMARK: QWEN3-8B (L4)
+-----------------+-----------+-----------+
| Metric          |      vLLM |    SGLang |
+-----------------+-----------+-----------+
| TTFT p50        |    71.2ms |    83.1ms |
| TTFT p99        |   184.5ms |   211.2ms |
| TPOT (Decode)   |    31.4ms |    27.1ms |
| Throughput      | 812 tok/s | 901 tok/s |
| GPU util        |     78.2% |     84.0% |
| $/1M tokens     |     $2.71 |     $2.44 |
| Energy / token  |   0.18 mJ |   0.16 mJ |
+-----------------+-----------+-----------+

---

## Key Features

- **Intelligence per Dollar (IPD) & Watt (IPW)**: Core economic efficiency metrics:
  $$\text{IPD} = \frac{\text{Validated Output}}{\text{Compute Cost} + \text{Energy Cost}}$$
  $$\text{IPW} = \frac{\text{Validated Output}}{\text{Energy (kWh)}}$$
- **Hardware Accelerator Power Modeling**: Electrical TDP specifications for NVIDIA H100 (SXM/PCIe), A100, B200 Blackwell, L40S, Google TPU v5e, AMD MI300X, and Apple Silicon with data center PUE modeling.
- **The Efficient Frontier of AI**: Multi-dimensional Pareto optimal frontier plotting models across (Quality vs Cost vs Latency) for dynamic model selection without regression.
- **Eval-Driven Routing**: Policy engine enforcing quality SLA constraints (Tier 1 $\ge 0.95$, Tier 2 $\ge 0.88$, Tier 3 Economy) with background shadow testing on cheaper candidates.
- **The AI Breaker Box**: Multi-provider resilience with automated circuit breakers (`CLOSED`, `OPEN`, `HALF-OPEN`) that detect provider outages, latency spikes, and quality degradation.
- **Semantic Equivalence Mapping**: Automatic translation of prompts, generation parameters, and tool/function calling schemas across OpenAI, Anthropic, Google Gemini, and Local formats.
- **AI Disaster Recovery (DR) Drills (`airun dr drill`)**: Automated fault injection simulations measuring capability parity, quality retention %, latency delta, and cost delta during outages.
- **AI-Aware Causal Incident Graph**: Diagnostic graph correlating hardware issues (GPU Xid 79, PCIe Gen1 throttling), network fabric stalls, and NCCL barrier timeouts to wasted dollars.
- **Executive Command Center (`airun ui`)**: Interactive Web UI featuring real-time KPI tiles, Pareto frontier visualizer, circuit breaker status, and trace DAG inspector.
- **Zero-Friction Tracing**: Universal `@trace` decorator and `with trace()` context manager.
- **Concurrent Critical Path**: Accurately computes critical-path latency across parallel tools using interval DAG scheduling.
- **Privacy by Default**: Automatic API key and sensitive token redaction. Prompt and completion contents are never stored without explicit opt-in.
- **Ultra-Low Overhead & High Throughput**: Measured in-memory span profiling overhead is $<20\mu\text{s}$ (p50: **9.40 $\mu$s**), interval DAG critical path resolution is sub-millisecond, and trace query latency is $<1\text{ms}$. See verified, reproducible benchmarks in [`benchmarks/`](benchmarks/).

---

## 3-Minute Quickstart

### 1. Installation

```bash
# Python SDK & CLI (PyPI)
pip install airun-profiler

# Rust Real-Time Node Telemetry Collector (crates.io)
cargo install airun-collector
```

### 2. Environment Health Check

```bash
airun doctor
```

### 3. Run the Instant Demo (Zero Setup)

Run an offline multi-step agent simulation without external API keys:

```bash
airun demo
```

Output:
```text
+---------- AI Workflow Runtime Summary -----------+
| Trace ID        5664cdc8296e41d2ab0b1feae7f0d481  |
| Workflow Name   multi_agent_coordination_pipeline |
| Final Outcome   [OK] SUCCESS                      |
| Total Cost      $0.0310                           |
| Cost / Success  $0.0310                           |
| Total Duration  411.7ms                           |
| Critical Path   411.7ms                           |
| Total Tokens    12,170 (in: 10,900, out: 1,270)   |
| Model Calls     4                                 |
| External Calls  2                                 |
| Retries         0                                 |
| Failed Steps    0                                 |
+---------------------------------------------------+

+-------------------- Findings & Optimization Insights ---------------------+
| * [CRITICAL] 56% of total cost comes from step 'agent_researcher' ($0.017)|
| * [WARNING] Token bloat: prompt context grew 2.7x from planner to synthesis|
| * [INFO] Concurrent execution: parallel tools saved ~411ms sequential delay|
+---------------------------------------------------------------------------+

                               Top Cost Drivers                                
+-----------------------------------------------------------------------------+
| #   | Span Name        | Kind | Model / Target    | Cost (USD) | % Total | Duration | Tokens |
|-----+------------------+------+-------------------+------------+---------+----------+--------|
| 1   | agent_researcher | llm  | claude-3-5-sonnet |    $0.0174 |   55.8% |  140.1ms |  3,020 |
| 2   | agent_planner    | llm  | gpt-4o            |    $0.0054 |   21.4% |  100.2ms |  1,590 |
| 3   | agent_critic     | llm  | gemini-1.5-pro    |    $0.0049 |   19.5% |   90.4ms |  3,310 |
| 4   | agent_synth      | llm  | gpt-4o-mini       |    $0.0008 |    3.3% |   80.2ms |  4,250 |
+-----------------------------------------------------------------------------+

Execution Hierarchy:
Execution Trace
`-- [OK] [workflow] multi_agent_coordination_pipeline (411.7ms)
    +-- [OK] [agent_step] agent_planner_phase (100.3ms)
    |   `-- [OK] [llm] agent_planner (100.2ms, model: gpt-4o, 1590 tok, $0.0054)
    +-- [OK] [agent_step] agent_researcher_phase (140.3ms)
    |   `-- [OK] [llm] agent_researcher (140.1ms, model: claude-3-5-sonnet, 3020 tok, $0.0174)
    +-- [OK] [agent_step] agent_critic_phase (90.6ms)
    |   `-- [OK] [llm] agent_critic (90.4ms, model: gemini-1.5-pro, 3310 tok, $0.0049)
    `-- [OK] [agent_step] agent_synthesizer_phase (80.4ms)
        `-- [OK] [llm] agent_synthesizer (80.2ms, model: gpt-4o-mini, 4250 tok, $0.0008)
```

---

## Instrumenting Your Code

### 1. Synchronous Functions

```python
from airun import trace, set_span_tokens, SpanKind

@trace(kind=SpanKind.LLM, model="gpt-4o", provider="openai")
def agent_step(prompt: str) -> str:
    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[{"role": "user", "content": prompt}]
    )
    set_span_tokens(
        input_tokens=response.usage.prompt_tokens,
        output_tokens=response.usage.completion_tokens,
    )
    return response.choices[0].message.content

with trace("customer_support_pipeline", kind=SpanKind.WORKFLOW):
    result = agent_step("Summarize ticket #4821")
```

### 2. Asynchronous Coroutines & Parallel Tools

```python
import asyncio
from airun import trace, SpanKind

async def run_agent():
    async with trace("travel_agent", kind=SpanKind.WORKFLOW):
        # Parallel tools executed concurrently
        async with trace("parallel_booking", kind=SpanKind.AGENT_STEP):
            flights, hotels = await asyncio.gather(
                fetch_flights(),
                fetch_hotels()
            )
```

### 3. Zero-Code-Change CLI Profiling & CI/CD Integration

Prefix any Python execution with `airun run` and capture trace IDs deterministically:

```bash
airun run --trace-id-file .airun/trace_id ./agents/my_agent.py
airun report $(cat .airun/trace_id)
```

---

## Comparing Runs (`airun compare`)

Benchmark two architectures or model swaps side-by-side:

```bash
airun compare previous latest
```

```text
                    Trace Comparison: 84081c95 vs 6f1fe728                    
+----------------------------------------------------------------------------+
| Metric         | Run A (Baseline) | Run B (Optimized)|       Delta (B - A) |
|----------------+------------------+------------------+---------------------|
| Total Duration |          425.0ms |          177.0ms |   -248.0ms (-58.4%) |
| Total Cost     |            $0.03 |          $0.0007 | $-0.027764 (-97.4%) |
| Tokens         |            8,100 |            3,290 |              -4,810 |
| Retries        |                2 |                0 |                  -2 |
| Failed Steps   |                0 |                0 |                   0 |
| Quality Score  |             0.94 |             0.95 |               +0.01 |
+----------------------------------------------------------------------------+
```

---

## CLI Reference

| Command | Description |
|---|---|
| `airun waste [latest\|<id>]` | Detect the 4 physical compute waste bottlenecks (Dataloader, NCCL, PCIe, Eager Mode) & financial bleed |
| `airun golden-signals [latest\|<id>]` | Display 4-Layer Golden Signals hierarchy (Economics, Efficiency, Reliability, Infrastructure) |
| `airun profiler trace --pid <pid>` | Open-source profiler hook with hardware counter sampling & Airun Cloud ROI assessment |
| `airun metrics [latest\|<id>]` | Display Executive Economics: Intelligence per Dollar (IPD), Intelligence per Watt (IPW), Energy |
| `airun frontier` | View Pareto Efficient Frontier across Model Quality, Latency, and Cost |
| `airun policy [list\|evaluate]` | Manage and evaluate automated closed-loop remediation policies |
| `airun dr drill` | Run automated Disaster Recovery drill with provider failover audit scorecard |
| `airun breaker status` | Inspect live AI Breaker Box provider circuit breaker health |
| `airun doctor` | Verify local workspace, database health, and micro-overhead |
| `airun init` | Initialize workspace configuration and trace storage |
| `airun demo` | Run built-in simulated agent workflow |
| `airun run <script.py>` | Execute Python script with active profiler and instant summary |
| `airun report [latest\|<id>]` | View runtime summary, diagnostic findings, and execution tree |
| `airun compare [previous\|<id1>] [latest\|<id2>]` | Compare two runs and inspect economic/latency deltas |
| `airun trace list` | List stored execution traces |
| `airun trace show [latest\|<id>]` | Inspect execution tree hierarchy |
| `airun export [latest\|<id>] --format [json\|otel-json]` | Export trace in raw JSON or OpenTelemetry format |
| `airun ui` / `airun serve` | Launch interactive Command Center Web UI and REST API |

---

## Production Architecture & Durable Technology Stack

`airun` transforms AI infrastructure from opaque hardware spend into an accountable, measurable, and autonomic engineering discipline. Rather than treating components as mere utilities, each language and layer has a **durable architectural role**:

```text
┌──────────────────────────────────────────────────────────┐
│                       TypeScript                         │
│               Control Plane / API Gateway                │
│                 + Executive Web Console                  │
└────────────────────────────┬─────────────────────────────┘
                             │ PostgreSQL State, Decisions, Metadata, Policies
┌────────────────────────────▼─────────────────────────────┐
│                         Pub/Sub                          │
│                      Event Backbone                      │
└──────────────┬────────────────────────────┬──────────────┘
               │                            │
┌──────────────▼─────────────┐┌─────────────▼──────────────┐
│            Rust            ││           Python           │
│    Real-Time Data Plane    ││      Intelligence Plane    │
│ (Ring Buffer, DCGM, OTLP)  ││ (Correlation, Waste, MFU)  │
└──────────────┬─────────────┘└─────────────┬──────────────┘
               │                            │
               └──────────────┬─────────────┘
                              │
┌─────────────────────────────▼────────────────────────────┐
│                GKE / EKS / AKS Kubernetes                │
│             Production Execution Environment             │
└──────────────────────────────────────────────────────────┘
```

### Durable Architectural Boundaries

| Layer / Technology | Durable Role | Core Responsibilities |
|---|---|---|
| **Rust** ([`crates/airun-collector`](crates/airun-collector), [crates.io](https://crates.io/crates/airun-collector)) | **Real-Time Data Plane** | Node/cluster telemetry collector, high-frequency GPU telemetry (DCGM/NVML), in-memory ring buffer (10Hz / 100ms), OTLP span ingestion, critical-path DAG engine, tri-state circuit breaker runtime. |
| **TypeScript** (`packages/control-plane`) | **Control Plane** | REST/gRPC API gateway, authentication/RBAC, organizations, projects, cluster configurations, billing, policies, and executive dashboard. |
| **Python** (`src/airun`) | **Intelligence Plane & SDK** | Developer-facing `@trace` SDK, OTLP span exporter, Time-Window Correlation engine, Physics of AI Waste diagnostics, MFU calculator, and CLI. |
| **PostgreSQL** (`deploy/postgres`) | **System of Record** | Source of truth for state, decisions, runs, policies, recommendations, and aggregated 1-minute rollups (never raw unaggregated telemetry). |
| **Pub/Sub** | **Event Fabric** | High-throughput asynchronous event backbone for batched telemetry, run completions, and waste alerts. |
| **Kubernetes (GKE / EKS / AKS)** (`deploy/kubernetes`, `deploy/helm`) | **Execution Environment** | Managed GPU node pools with `nvidia.com/gpu` tolerations and DaemonSets mounting `/var/run/nvidia-dcgm` and `/sys/fs/cgroup`. |

---

### The Crucial Bridge: Logical vs. Physical Tracing

Observability tools (LangSmith, Langfuse) only observe the *logical* layer (tokens, API costs). Infrastructure monitors (Datadog) only observe the *physical* layer (average GPU utilization).

**`airun`'s category moat is the Time-Window Correlation Bridge connecting the logical trace span directly to physical silicon.**

Run the hardware waste diagnostic on any trace:
```bash
airun waste --hardware
```

Output:
```text
+--- ! HARDWARE WASTE DETECTED IN TRACE: 5ff3390b470d49dc93de5ebb04d292aa ----+
| Workload         research_agent_workflow (8x H100)                          |
| Bottleneck       Dataloader Starvation (CPU/IO Bound)                       |
| Symptom          GPU SM active cycles dropped to 38.2% (idle stalls) while  |
|                  PCIe TX was idle (<400 MB/s)                               |
| Financial Bleed  $1,599.36 / week ($9.52/hr | $6,854.40/mo)                 |
| Root Cause       Host CPU data loading workers starved accelerator between  |
|                  training mini-batches                                      |
| Actionable Fix   Increase DataLoader num_workers=8, set pin_memory=True,    |
|                  and pre-fetch tensors                                      |
| Expected Impact  throughput_gain: +31%, waste_reduction: -82%,              |
|                  weekly_cost_savings: $1279.49                              |
|                                                                             |
|             Culprit Execution Spans in Critical Path                        |
| +---------------------------------------------------------------+           |
| | Span Name               | Duration (ms) | Cost (USD) | Tokens |           |
| |-------------------------+---------------+------------+--------|           |
| | research_agent_workflow |       334.7ms |    $0.0000 |      0 |           |
| | agent_planning          |       160.9ms |    $0.0000 |      0 |           |
| | planner_llm_call        |       120.4ms |    $0.0073 |   1800 |           |
| +---------------------------------------------------------------+           |
+-----------------------------------------------------------------------------+
```

Or diagnose workload-level economics:
```bash
airun waste --workload customer-support-agent
```

Output:
```text
+---- Airun Workload Economics & Optimization Report -----+
| Workload         customer-support-agent                 |
| Monthly Spend    $84,210.00                             |
| Potential Waste  $17,430.00 (20.7% recoverable)         |
| Top Issue        42% of cost from researcher agent      |
| Root Cause       Large prompt context + expensive model |
| Recommendation   Route 73% of requests to cheaper model |
|                                                         |
|       Expected Impact from Optimization                 |
| +------------------------------+                        |
| | Dimension | Projected Change |                        |
| |-----------+------------------|                        |
| | Cost      | -31%             |                        |
| | Latency   | -18%             |                        |
| | Quality   | -0.4%            |                        |
| +------------------------------+                        |
+---------------------------------------------------------+
```

---

### The 3 Evolutionary Phases
- **Phase 1 — Developer Platform**: Local-first Python SDK & CLI (`@trace`, `airun report`, `airun compare`, `airun waste`, `airun frontier`) with microsecond overhead and zero network dependencies.
- **Phase 2 — Cloud Control Plane & Silicon Bridge**: Multi-tenant SaaS architecture connecting logical traces to physical silicon via Rust Data Plane DaemonSet (`deploy/kubernetes/daemonset-agent.yaml`, `deploy/helm/airun-data-plane/`), Pub/Sub, PostgreSQL (`deploy/postgres/schema.sql`), and TypeScript control plane (`packages/control-plane`).
- **Phase 3 — Autonomous Multi-Cloud Platform (10.0 / 10.0)**:
  - **In-Kernel eBPF Fabric Tracing**: Kernel tracepoints (`kfree_skb`, `net_dev_xmit`) detecting RoCE/InfiniBand packet drops and PFC pause frame storms.
  - **Multi-Cluster Cross-Cloud Federation (`airun cluster [list|overview|recommend]`)**: Global GPU capacity aggregation and intelligent MFU-per-dollar placement across GCP GKE, AWS EKS, Azure AKS, and on-premise DGX SuperPODs.
  - **Live Silicon CI Hardware Testing**: Dedicated physical GPU test suite (`tests/hardware/test_silicon_hardware.py`), Kubernetes GPU runner manifest (`deploy/ci/gpu-runner.yaml`), and GitHub Actions workflow (`.github/workflows/gpu-hardware-ci.yml`).
  $$\text{Observe} \longrightarrow \text{Understand} \longrightarrow \text{Measure Economics} \longrightarrow \text{Find Waste} \longrightarrow \text{Recommend Optimization} \longrightarrow \text{Remediate} \longrightarrow \text{Learn}$$

---

## CLI Command Reference (5-Pillar Mental Model)

| Pillar | Command | Description |
| :--- | :--- | :--- |
| **PROFILE** | `airun demo` | Run zero-friction simulated agent trace offline |
| | `airun report <id>` | Generate executive execution summary and flamegraph tree |
| | `airun golden-signals <id>` | Inspect 4-layer physical-to-economic health metrics |
| **DIAGNOSE** | `airun diagnose <id>` | Connect logical trace to physical silicon bottlenecks & root cause |
| | `airun agent analyze <id>` | Detect duplicate retrievals, loop redundancy, and tool chain stalls |
| | `airun waste <id>` | Diagnose silicon starvation and compute dollar bleed |
| **ECONOMICS** | `airun money-leak` | Executive audit of enterprise recoverable AI infrastructure waste |
| | `airun metrics <id>` | Measure Intelligence per Dollar (IPD) and IPW |
| **OPTIMIZE** | `airun bench` | Benchmark inference engines (vLLM, SGLang, TensorRT-LLM) |
| | `airun frontier` | Plot Pareto-optimal models across Quality, Cost, and Latency |
| | `airun compare <id1> <id2>` | Deep comparative delta between two workflow traces |
| **VERIFY** | `airun breaker status` | Real-time state of multi-provider circuit breakers |
| | `airun dr drill` | Automated disaster recovery fault injection simulation |
| | `airun policy evaluate` | Evaluate closed-loop automated remediation policies |

---

## AI Workload Laboratory

Explore representative runnable agent archetypes in [`examples/lab/`](examples/lab):
```bash
python examples/lab/run_all.py
```
- `chat_workload.py` — Simple Chatbot
- `rag_workload.py` — RAG Retrieval & Synthesis
- `tool_agent_workload.py` — Tool Agent with Parallel Concurrency & Retries
- `coding_agent_workload.py` — Code Evaluation & Bug Fix Loop
- `multi_agent_workload.py` — Multi-Agent Coordination Pipeline
- `comparison_workload.py` — The Same Workload, Two Ways (Cost & Latency Regression Lab)

---

## Documentation & Deployment Guides

- **Deployment Guides**:
  - [Google Kubernetes Engine (GCP GKE) Deployment Guide](docs/gcp-gke-deployment-guide.md)
  - [Amazon Elastic Kubernetes Service (AWS EKS) Deployment Guide](docs/aws-eks-deployment-guide.md)
  - [Azure Kubernetes Service (Azure AKS) Deployment Guide](docs/azure-aks-deployment-guide.md)
- **Technical Architecture & Specifications**:
  - [System Architecture & Distributed Data Path](docs/architecture.md)
  - [Reproducible Performance Benchmarks](benchmarks/README.md)
  - [Master Product Specification (`SPECIFICATION.md`)](SPECIFICATION.md)
  - [Developer & AI Agent Guide (`AGENT.md`)](AGENT.md)
  - [5-Minute Quickstart Guide](docs/quickstart.md)
  - [Pricing & Accelerator Energy Economics](docs/pricing.md)
  - [Architecture Decision Records (ADRs)](docs/decision-log.md)
  - [Automated Release & Publishing Runbook](docs/release-guide.md)
- **External Validation Kit (AIRUN-100)**:
  - [Milestone AIRUN-100 Charter](validation/AIRUN-100.md)
  - [Campaign Outreach Playbook](validation/outreach-playbook.md)
  - [Pipeline Teardown Template](validation/teardown-template.md)
  - [Quickstart Checklist](validation/quickstart-checklist.md)
  - [Feedback Form](validation/feedback-form.md)
  - [Friction Log](validation/results/friction-log.md)
  - [Pain Ranking Matrix](validation/results/pain-ranking.md)

---

## License

Apache 2.0 License. See [LICENSE](LICENSE) for details.
