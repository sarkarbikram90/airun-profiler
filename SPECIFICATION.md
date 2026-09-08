# airun: AI Infrastructure Reliability, Economics & Optimization Platform
## Master Product Specification & Production Architecture

---

## 1. Executive Summary & Macro Thesis

### 1.1 The Compute Centralization Reality
AI infrastructure economics is undergoing extreme structural concentration. Frontier research and foundation models require capital expenditure of unprecedented scale ($10M–$15M per megawatt for modern data centers). At this magnitude:

$$\text{Better Models} \longrightarrow \text{Higher Revenue per MW} \longrightarrow \text{Ability to Outbid for Scarce Compute} \longrightarrow \text{More FLOPs} \longrightarrow \text{Better Models}$$

This flywheel concentrates usable frontier FLOPs into a tiny handful of frontier labs. By 2027–2028, frontier labs may control 40%–50%+ of incremental compute coming online.

### 1.2 The Opportunity: The Independent Layer for Everyone Else
As frontier labs prioritize internal R&D over commoditized external inference, the broader market—Series B/C applied-AI companies, enterprise Centers of Excellence, and sovereign AI initiatives spending $500K to $5M+ per month on compute—faces acute operational and economic pressures:
- **Binding Constraint**: Optimization shifts from raw GPU counts to **"Who extracts the most validated intelligence per dollar and per watt?"**
- **Dependency Risk**: Outages, silent model drift, provider lock-in, and rate limits threaten business continuity.
- **Compute Waste**: Clusters run at deceptive utilization rates where 20%–40% of expensive GPU-hours are burned in idle stalls, I/O bottlenecks, and framework overhead.

### 1.3 The Core Wedge
> **“Tell me exactly where my AI workload is wasting compute and how much money I'm losing.”**

`airun` transforms AI infrastructure from opaque hardware spend into an accountable, measurable, and autonomic engineering discipline. Rather than forcing a microservice rewrite, `airun` bridges local-first developer profiling directly into a cloud-scale control plane.

---

## 2. The Product Surface & Capabilities

`airun` provides a unified, production-grade product surface spanning observability, economics, physical waste detection, resilience, and executive control:

```text
                                    AIRUN PRODUCT SURFACE
 ┌───────────────────────────────────────────────────────────────────────────────────────────┐
 │                                EXECUTIVE CONTROL PLANE                                    │
 │    KPI Command Center  •  Real-Time Financial Bleed  •  MFU Gauges  •  Golden Signals     │
 ├───────────────────────────────┬───────────────────────────┬───────────────────────────────┤
 │         OBSERVABILITY         │         ECONOMICS         │          RESILIENCE           │
 │  • Python @trace decorator    │  • Tokens / Dollar        │  • AI Breaker Box (3-state)   │
 │  • Sub-microsecond overhead   │  • Tokens / kWh           │  • Semantic Equivalence Map   │
 │  • Execution DAG & Spans      │  • Intelligence / $ (IPD) │  • Automated DR Drills        │
 │  • Critical Path Analysis     │  • Intelligence / W (IPW) │  • Multi-Provider Failover    │
 │  • Trace Diff & Regressions   │  • PUE 1.20 DC Modeling   │  • Causal Incident Graph      │
 ├───────────────────────────────┴───────────────────────────┴───────────────────────────────┤
 │                         PHYSICS OF AI WASTE & MFU ENGINE                                  │
 │    Dataloader Starvation  •  NCCL Stalls  •  PCIe Saturation  •  PyTorch Eager Overhead    │
 └───────────────────────────────────────────────────────────────────────────────────────────┘
```

### 2.1 Developer Observability & Microsecond Profiling
- **Lightweight Instrumentation**: `@trace` decorator and context managers capture function, LLM call, agent step, and tool latencies with microsecond overhead.
- **Zero-Dependency Local Profiling**: Persists traces locally in SQLite or JSONL without requiring cloud connectivity or external services.
- **Critical Path Graph**: Constructs directed acyclic graphs (DAG) of multi-agent and async workflows, identifying the exact latency bottleneck and parallel speedups.

### 2.2 AI Economics & Energy Engine
Quantifies economic yield from raw hardware physics:
- **Accelerator Catalog**: Pre-calibrated thermal, electrical, and compute profiles for NVIDIA H100 SXM5, H100 PCIe, A100 SXM4, B200 Blackwell, L40S, Google TPU v5e, and AMD Instinct MI300X.
- **Intelligence per Dollar (IPD)**:
  $$\text{IPD} = \frac{\text{Quality-Weighted Useful Output}}{\text{Compute Cost (USD)} + \text{Electricity Cost (USD)}}$$
- **Intelligence per Watt (IPW)**:
  $$\text{IPW} = \frac{\text{Quality-Weighted Useful Output}}{\text{Energy Consumption (kWh)}}$$
- **Data Center PUE Integration**: Standard PUE 1.20 modeling calculating true facility electricity cost and carbon intensity ($g\text{CO}_2/\text{kWh}$).

### 2.3 Physics of AI Waste & MFU Engine
Identifies and quantifies the 4 canonical physical bottlenecks causing the gap between peak theoretical FLOPs and achieved throughput:

1. **Dataloader Starvation (CPU/IO Bound)**:
   - *Symptom*: GPU Streaming Multiprocessor (SM) active cycles drop below 55% while PCIe TX/RX is idle (<600 MB/s); the accelerator stalls waiting for CPU workers to assemble mini-batches.
   - *Remediation*: Auto-recommends increasing DataLoader `num_workers`, enabling `pin_memory=True`, and caching datasets on local NVMe.
2. **NCCL Communication Overhead (Network Bound)**:
   - *Symptom*: GPUs stall during `All-Reduce` gradient synchronization; InfiniBand or RoCE network fabric is saturated with high barrier wait times (>30ms).
   - *Remediation*: Recommends ring buffer tuning (`NCCL_BUFFSIZE=16MB`), gradient accumulation steps, and fabric retransmit inspection.
3. **PCIe Bus Saturation (Memory Bound)**:
   - *Symptom*: Excessive Host RAM $\leftrightarrow$ VRAM transfers saturate PCIe bandwidth (>8,000 MB/s) while kernel execution stalls.
   - *Remediation*: Recommends tensor batching, embedding pinning, and asynchronous non-blocking memory copies (`tensor.to(device, non_blocking=True)`).
4. **Framework Overhead (Software Bound)**:
   - *Symptom*: High host CPU utilization (>75%) in the Python process due to PyTorch eager mode kernel dispatch overhead, leaving idle bubbles between GPU kernels.
   - *Remediation*: Recommends `torch.compile(mode="reduce-overhead")` and CUDA Graphs capture.

#### Model FLOPs Utilization (MFU)
$$\text{MFU} = \frac{\text{Achieved TFLOPS}}{\text{Theoretical Peak TFLOPS}} \times 100\%$$
- Scaling: $2 \times \text{Params} \times \text{Tokens}$ for inference, $6 \times \text{Params} \times \text{Tokens}$ for training (forward + backward pass).
- Classification: $\ge 45\%$ Optimal, $30\% - 45\%$ Moderate, $< 30\%$ Critical Waste.

#### Real-Time Financial Bleed
Computes exact dollar loss per hour and per run based on accelerator hourly rates:
$$\text{Hourly Bleed (USD/hr)} = \left(\sum \text{Waste \%}_i\right) \times \text{Hourly Rate} \times \text{Number of GPUs}$$

### 2.4 The Golden Signals Hierarchy
Organizes cluster telemetry into 4 operational tiers:

| Layer | Golden Signal | Stakeholder | Key Metrics |
|---|---|---|---|
| **1. Economics** | Financial Health & Burn | CFO / FinOps | $/effective GPU-hr, $/1M tokens, hourly bleed ($/hr), wasted spend ($) |
| **2. Efficiency** | Compute Utilization | ML Engineer | MFU %, achieved TFLOPS, GPU SM active cycles %, memory bandwidth % |
| **3. Reliability** | Workload Health | Platform Eng | Failure rate %, MTTR ms, checkpoint cadence, retry storm penalty |
| **4. Infrastructure** | Physical Reality | Hardware / Ops | Power draw (Watts), PUE, thermal throttling, PCIe errors, network retransmits |

### 2.5 The Efficient Frontier & SLA Routing
- **Pareto Optimality**: Dynamically maps frontier models (GPT-4o, Claude 3.5 Sonnet, Gemini 1.5 Pro, Llama-3 70B, etc.) across Quality, Cost, and Latency.
- **Dominance Filtering**: Identifies Pareto-dominated models and alerts teams to swap models for lower cost and higher quality.
- **Shadow Evaluation Routing**: Shadow-tests candidate alternative models in the background to verify SLA and quality compliance before production routing.

### 2.6 The AI Breaker Box & Multi-Model Disaster Recovery
- **Tri-State Circuit Breakers**: Tracks `CLOSED` (healthy), `OPEN` (tripped/failing), and `HALF_OPEN` (canary recovery) across providers.
- **Auto-Trip Triggers**: Consecutive error rate $>3$, latency spikes $>2500\text{ms}$, or semantic quality drops $<0.70$.
- **Semantic Equivalence Mapping**: Normalizes tool calls, prompt formats, and JSON schemas between disparate providers (OpenAI $\leftrightarrow$ Anthropic $\leftrightarrow$ Google $\leftrightarrow$ Local open-weights).
- **Automated Synthetic DR Drills**: Simulates provider outages (`outage_500`, `latency_spike`, `quality_collapse`) and generates an executive business continuity scorecard.

### 2.7 AI-Aware Causal Incident Graph
Correlates physical infrastructure anomalies directly to application-layer compute loss:
$$\text{Hardware Degradation} \longrightarrow \text{Network Switch Retransmits} \longrightarrow \text{AllReduce Barrier Stall} \longrightarrow \text{GPU Idle Bleed}$$
Pinpoints root causes and provides immediate infrastructure remediation steps.

### 2.8 Executive Command Center Web UI
Interactive dashboard providing:
- Real-time **Financial Bleed** ticker and top problem alert banners.
- Visual **4-Tier Physics of AI Waste** breakdown and MFU gauge.
- **Golden Signals Hierarchy** 4-layer cards.
- Interactive trace DAG waterfall with critical path highlighting.
- AI Breaker Box live circuit health and DR drill trigger.

---

## 3. Target Customers & Go-To-Market Strategy

### 3.1 Target Customer Profiles
1. **Primary Segment (Series B/C Applied-AI Startups & Neocloud Deployers)**:
   - Spending $500K to $5M+ per month on GPU compute (legal, coding, healthcare, financial AI).
   - High burn pressure, lean platform teams, urgent requirement for ROI in weeks.
   - Primary pain: *"We are spending $200K/month on H100s, but our jobs run slower than expected and we don't know where the money is going."*
2. **Secondary Segment (Enterprise Centers of Excellence)**:
   - Multi-cloud and multi-accelerator enterprises requiring unified FinOps and SLA compliance.
3. **Excluded Initially**: Frontier AI labs (build proprietary internal tooling) and non-commercial academic research.

### 3.2 The Open-Source Developer Wedge
`airun` uses the proven GTM playbook of Datadog, Prometheus, and Telegraf:
1. **Open-Source Profiler CLI**: Distribute `airun` as a lightweight CLI tool (`airun profiler trace --pid <pid>`).
2. **The Viral Developer Hook**: An ML engineer profiling a slow training or inference run gets an immediate terminal visualization and Perfetto trace.
3. **The ROI Callout**:
   > *"You lost 14 hours of H100 time on this run ($49.00) due to Dataloader Starvation. Want to see how this scales across your whole cluster? Sign up for Airun Cloud."*
4. **SaaS Conversion**: Convert individual engineers to team-wide GKE DaemonSet deployment with savings-percentage or seat-based billing.

---

## 4. Production Architecture & Durable Technology Stack Allocation

`airun` enforces a strict, problem-driven separation of concerns. Rather than treating components as mere utilities, each language and layer has a **durable architectural role**:

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
│                      GKE Kubernetes                      │
│             Production Execution Environment             │
└──────────────────────────────────────────────────────────┘
```

### 4.1 Durable Stack Allocation Matrix

| Language / Tech | Durable Role | Responsibilities | Justification |
|---|---|---|---|
| **Rust** | **Real-Time Data Plane** | Node/cluster telemetry collector, high-frequency GPU telemetry (DCGM/NVML), in-memory ring buffering (10Hz / 100ms), OTLP span ingestion, critical-path DAG engine, tri-state circuit breaker runtime, local backpressure | Zero-cost abstractions, predictable sub-millisecond execution, zero garbage collection pauses on GPU nodes, safe concurrency |
| **TypeScript** | **Control Plane** | Enterprise API gateway (REST/gRPC), authentication, RBAC, organizations, projects, billing, cluster configuration, policies, executive dashboard, WebSockets, admin workflows | Rapid product iteration, world-class frontend/API ecosystem, robust JSON/GraphQL integration |
| **Python** | **Intelligence Plane & SDK** | Developer-facing `@trace` SDK, OTLP span exporter, Time-Window Correlation engine, Physics of AI Waste diagnostics, MFU calculator, anomaly detection, forecasting, Pareto frontier routing, CLI | De-facto language of AI/ML engineers, universal framework bindings (PyTorch, NumPy, Polars, Hugging Face) |
| **PostgreSQL** | **System of Record** | Organizations, projects, clusters, workloads, runs, cost records, policies, alerts, incidents, recommendations, 1-minute aggregated rollups | ACID guarantees, relational integrity for billing, auditing, and configuration state |
| **Pub/Sub** | **Event Fabric / Backbone** | High-throughput decoupled event stream for telemetry batches, run completions, hardware bleed alerts, incident triggers | Managed horizontal scalability, at-least-once delivery, zero inter-service coupling |
| **GKE Kubernetes** | **Execution Environment** | DaemonSet orchestrator on GPU node pools (`nvidia.com/gpu`), API gateway deployments, background analytics workers | Managed GPU scheduling, multi-cloud compatibility, cloud-native scalability |
| **Cloud Storage (GCS)** | **Cold Lakehouse Store** | Compressed Parquet telemetry archives, full trace dumps, raw profiling snapshots | Low-cost durable long-term storage for historical regression and benchmark queries |

---

### 4.2 The Crucial Bridge: Logical vs. Physical Tracing

Standard AI observability tools (LangSmith, Langfuse, Helicone) operate exclusively at the **Logical Layer**:
- Agent $\rightarrow$ Tool $\rightarrow$ LLM API calls
- Prompt / completion tokens
- API vendor invoices and latency

Conversely, infrastructure monitoring tools (Datadog, Prometheus) operate exclusively at the **Physical Layer**:
- Average node CPU/GPU percentage
- Host memory utilization
- Network interface bytes

**`airun`'s category moat is the Time-Window Correlation Bridge connecting the logical trace span directly to the physical silicon.**

```text
Logical Trace (Python SDK):
  [==================== agent_researcher span (140.1ms) ====================]
         │
         │ Correlated across exact microsecond timestamp window
         ▼
Physical Telemetry (Rust Data Plane Ring Buffer @ 10Hz):
  SM Active Cycles:   [ 12.4%  |  11.8%  |  14.1%  |  13.0% ]  <-- Idle Stalls!
  PCIe TX (MB/s):     [ 9,450  |  9,820  |  9,100  |  9,600 ]  <-- Saturation!
  True Power (Watts): [ 280W   |  275W   |  285W   |  280W  ]  <-- Dropped vs 700W TDP
         │
         ▼
Diagnosis & Actionable ROI:
  * Bottleneck:  PCIe Bus Saturation (Vector DB host-to-device memory copy)
  * Cost Bleed:  $2,847.20 / week ($16.95 / hour across 8x H100s)
  * Root Cause:  Synchronous unpinned tensor allocations during embedding lookup
  * Action:      Pin embeddings in VRAM and pass non_blocking=True
  * Gain:        -28% latency, recover $967/week in GPU spend
```

---

### 4.3 End-to-End Production Dataflow Path

```text
Python AI Workload / Agent (@trace SDK)
      │
      │ 1. Traces & Spans (OTLP HTTP via AIRUN_OTLP_ENDPOINT)
      ▼
Rust Data Plane (airun-collector DaemonSet on GKE GPU Node)
      │ 2. Scrapes DCGM/NVML @ 10Hz into In-Memory Ring Buffer
      │ 3. Evaluates Sub-Millisecond Tri-State Circuit Breakers
      │ 4. Batches High-Frequency Metrics into 1Hz Telemetry Packets
      │
      │ Pub/Sub Event Fabric
      ▼
Rust Event Processor / Python Analytics Worker
      │ 5. Performs Time-Window Correlation (Logical Spans <-> Physical Metrics)
      │ 6. Computes Physics of AI Waste, MFU, and Financial Bleed ($/hr)
      │ 7. Generates Concrete Actionable Recommendations
      │
      ├──────────────────────────────► PostgreSQL (State, Decisions, 1-Min Rollups)
      ▼
TypeScript Control Plane (REST / WebSocket API Gateway)
      │ 8. Enforces RBAC, Organizations, Projects, and Policies
      │
      ▼
Executive Command Center Web Dashboard & CLI (airun waste, airun compare)
```

---

### 4.4 First Production-Grade Use Case & The Core Thesis

> **AI Infrastructure Economics & Reliability.**
> Observability is only the input. The output is **economic action**.

`airun` tells an engineering team exactly where their AI workload is wasting money, latency, and compute—and quantifies the improvement from fixing it:

#### Example: Multi-Agent Workload FinOps
```text
Workload:        customer-support-agent
Monthly Spend:   $84,210.00
Potential Waste: $17,430.00 (20.7% recoverable)
Top Issue:       42% of cost from researcher agent
Root Cause:      Large prompt context + expensive model
Recommendation:  Route 73% of requests to cheaper model based on Pareto frontier
Expected Impact:
  * Cost:    -31%
  * Latency: -18%
  * Quality: -0.4%
```

#### Example: GPU Cluster Hardware Bleed
```text
! HARDWARE WASTE DETECTED IN TRACE: 5664cdc8
-----------------------------------------------------------------
Workload:    finetune-7b-v3 (8x H100 SXM5)
Bottleneck:  Dataloader Starvation (CPU/IO Bound)
Symptom:     GPU SM active cycles dropped to 38.2% (idle stalls)
Cost Bleed:  $2,847.20 / week ($16.95 / hour)
Root Cause:  Host CPU data loading workers starved accelerator between batches
Action:      Increase DataLoader num_workers=8 and set pin_memory=True
Impact:      Recover $967/week (+31% throughput gain)
-----------------------------------------------------------------
```

---

### 4.5 Architectural Answers to System Implementation Questions

1. **Data Collection Efficiency**:
   - Uses NVIDIA DCGM direct Unix domain socket (`/var/run/nvidia-dcgm/dcgm.sock`) and C/Rust bindings rather than spawning `nvidia-smi` subprocesses, keeping CPU overhead under 0.1%.
   - In-memory `TelemetryRingBuffer` stores 1,000 samples @ 10Hz locally in RAM for zero-overhead correlation queries without disk I/O.
   - Batches telemetry into 1-second envelopes before pushing to Pub/Sub to prevent network flooding.

2. **Data Model**:
   - Ingests traces via standard OpenTelemetry (OTLP) HTTP/JSON payloads (`resourceSpans -> scopeSpans -> spans`).
   - Publishes telemetry batches in compact JSON/Protobuf envelopes.
   - Long-term cold analytics archives are persisted in compressed columnar Apache Parquet format on GCS.

3. **Kubernetes Integration**:
   - Reads container and pod UIDs by inspecting cgroup paths (`/sys/fs/cgroup`) mounted into the DaemonSet container.
   - Correlates pod metadata via the Kubernetes Downward API (`spec.nodeName`, `metadata.namespace`).

4. **Error Handling & Graceful Degradation**:
   - The Rust Data Plane checks for DCGM socket and NVML availability at initialization.
   - If running on non-GPU nodes, development laptops, or environments without NVIDIA drivers, it gracefully activates `HardwareMode::FallbackEmulated` without crashing, preserving service uptime.

5. **Deployment**:
   - Production Helm chart provided in `deploy/helm/airun-data-plane/` and Kubernetes manifests in `deploy/kubernetes/`.
   - Node pool tolerations: `nvidia.com/gpu=present:NoSchedule` and `cloud.google.com/gke-accelerator=present:NoSchedule`.
   - Security context: Non-privileged execution with `hostPID: true`, `hostIPC: true`, read-only mounts to `/var/run/nvidia-dcgm`, `/sys`, and `/proc`.

6. **Open Core vs. SaaS Boundary**:
   - **Open Source (Apache 2.0)**: Python `@trace` SDK, CLI profiler (`airun profiler`), local Rust Data Plane agent, local SQLite store (`.airun/traces.db`).
   - **Enterprise / Cloud (Commercial)**: Multi-tenant TypeScript control plane, centralized PostgreSQL & Pub/Sub aggregator, fleet-wide cluster optimization, autonomic scheduling remediation, enterprise SSO/RBAC.

---

## 5. Architectural Decision: State vs. Telemetry Separation

### 5.1 The PostgreSQL Bloat Trap
Collecting DCGM GPU telemetry every second across a 500-GPU fleet generates:
$$\text{500 GPUs} \times \text{10 Metrics} \times \text{60 Samples/min} \times \text{60 Min} \times \text{24 Hr} = \mathbf{43.2\text{ Million Rows / Day}}$$
Dumping raw high-frequency telemetry into ordinary PostgreSQL tables results in catastrophic index maintenance overhead, table bloat, and query degradation within weeks.

### 5.2 The Architectural Rule
- **PostgreSQL holds strictly State and Decisions**:
  `organizations`, `projects`, `clusters`, `workloads`, `runs`, `policies`, `alerts`, `incidents`, `recommendations`, `cost_records`.
- **Raw Telemetry Streams via Pub/Sub to Analytics Storage**:
  High-frequency DCGM samples are batched, pushed to Pub/Sub, processed by streaming workers, and persisted in compressed Parquet format on Cloud Storage or a purpose-built time-series engine (TimescaleDB / ClickHouse).
- **Aggregated 1-Minute Rollups to PostgreSQL**:
  Only summarized rollups (min, max, average, p95) and derived economic metrics are stored in PostgreSQL for the UI.

---

## 6. The 3-Phase Evolutionary Roadmap

To ensure rapid developer adoption while building toward enterprise cloud control, `airun` evolves in three distinct phases:

### Phase 1 — Developer Platform (Current Foundation)
- **Scope**: Local-first Python SDK & CLI (`@trace`, `airun report`, `airun compare`, `airun waste`, `airun frontier`, `airun metrics`, `airun dr drill`, `airun breaker status`).
- **Storage**: Local SQLite / JSONL trace store (`.airun/traces.db`).
- **Goal**: Zero network dependencies, microsecond profiler overhead, immediate developer delight in diagnosing local scripts and agent pipelines.

### Phase 2 — Cloud Control Plane & Silicon Bridge
- **Scope**: Multi-tenant SaaS architecture connecting logical traces to physical silicon.
- **Components**:
  - `airun-collector` Real-Time Data Plane DaemonSet in Rust with in-memory ring buffering and OTLP ingestion.
  - Managed GCP Pub/Sub event bus.
  - Rust / Python background processing workers performing Time-Window Correlation.
  - PostgreSQL system of record (`deploy/postgres/schema.sql`).
  - TypeScript / Node.js control plane API and Executive Web UI (`packages/control-plane`).
- **Goal**: Fleet-wide visibility across multi-node GPU clusters, quantifying aggregate financial bleed and delivering actionable FinOps recommendations.

### Phase 3 — Infrastructure Intelligence & Autonomic Remediation
- **Scope**: Closed autonomic control loop.
- **Components**:
  - Closed-loop optimization engine converting recommendations into automated scheduling adjustments.
  - Energy-aware workload placement and spot-instance migration.
  - Automated dynamic batch sizing and PyTorch compilation injection.
- **Goal**: Autonomous AI infrastructure operating system that continually optimizes intelligence yield per dollar and per watt.

---

## 7. The Closed Autonomic Product Loop

The core differentiator of `airun` is that it does not merely alert on inefficiency—it drives a closed loop from observation to automated remediation:

```text
                               THE AUTONOMIC LOOP
                                       │
                                    OBSERVE
                          (Rust Real-Time Data Plane)
                                       │
                                       ▼
                                   UNDERSTAND
                          (Trace DAG & Critical Path)
                                       │
                                       ▼
                                MEASURE ECONOMICS
                            (Tokens/$, IPD, IPW, PUE)
                                       │
                                       ▼
                                   FIND WASTE
                          (Physics of AI Waste Engine)
                                       │
                                       ▼
                              RECOMMEND OPTIMIZATION
                         (Actionable FinOps Remediation)
                                       │
                                       ▼
                            AUTOMATICALLY REMEDIATE
                         (Workload / Scheduler Migration)
                                       │
                                       ▼
                                MEASURE RESULT
                          (airun trace comparison)
                                       │
                                       ▼
                                     LEARN
                         (Update routing & placement models)
```

> **airun doesn't merely tell you that an AI workload is slow or expensive. It tells you why, quantifies the financial impact, recommends the optimal change, and eventually executes the change automatically.**

---

## 8. Technical Specifications & Data Contracts

### 8.1 PostgreSQL Relational Schema (`deploy/postgres/schema.sql`)
The PostgreSQL schema codifies all operational state:
- `organizations (org_id, name, slug, plan_tier, created_at)`
- `projects (project_id, org_id, name, slug, monthly_budget_usd)`
- `clusters (cluster_id, org_id, name, cloud_provider, region, accelerator_type, total_gpus, hourly_rate_usd)`
- `workloads (workload_id, project_id, cluster_id, name, workload_type, model_name, parameters_billions)`
- `runs (run_id, workload_id, trace_id, status, duration_ms, critical_path_ms, total_tokens, total_cost_usd, wasted_cost_usd, mfu_pct, achieved_tflops)`
- `cost_records (record_id, run_id, accelerator, num_devices, compute_cost_usd, energy_cost_usd, financial_bleed_hourly_usd, primary_waste_category)`
- `policies (policy_id, project_id, name, policy_type, rule_config, is_active)`
- `alerts (alert_id, project_id, run_id, severity, title, message, status)`
- `incidents (incident_id, cluster_id, title, root_cause_type, total_wasted_cost_usd, causal_chain, remediation_action)`
- `recommendations (recommendation_id, workload_id, category, title, action, potential_weekly_savings_usd, potential_monthly_savings_usd, status)`

### 8.2 Pub/Sub Event Backbone Contracts
All asynchronous events follow strict schema envelopes:
- `telemetry.gpu.metrics`: Batched 1Hz DCGM metrics (SM util %, memory MB, temperature, power, PCIe TX/RX bytes, NVLink MB/s, NCCL barrier wait ms).
- `workload.waste.detected`: Emitted when hourly financial bleed exceeds threshold ($/hr).
- `workload.completed`: Summary telemetry containing total tokens, duration, cost, MFU, and Golden Signals.
- `cluster.node.health`: Hardware status, thermal throttling events, PCIe correctable/uncorrectable error counts.

### 8.3 REST API Endpoints
- `GET /healthz`: Service health and version status.
- `GET /api/traces`: List recent trace summaries.
- `GET /api/traces/:id`: Full execution trace with DAG, spans, and diagnostic findings.
- `GET /api/waste`: Physics of AI waste breakdown, MFU report, and hourly financial bleed.
- `GET /api/golden-signals`: 4-Layer Golden Signals hierarchy (Economics, Efficiency, Reliability, Infrastructure).
- `GET /api/recommendations`: Actionable FinOps optimizations with projected weekly/monthly savings.
- `GET /api/routing/frontier`: Efficient Frontier Pareto analysis across quality, cost, and latency.
- `GET /api/resilience/breaker`: Live circuit breaker statuses for all AI providers.
- `POST /api/resilience/dr-drill`: Trigger automated synthetic Disaster Recovery drill and failover audit.
- `GET /api/incidents/graph`: AI causal incident graph linking hardware degradation to compute loss.
- `GET /api/manifests/daemonset`: GKE Kubernetes DaemonSet YAML manifest.

### 8.4 GKE Kubernetes DaemonSet Configuration
- **Node Pool Taints**: `nvidia.com/gpu=present:NoSchedule`
- **Matching Tolerations**:
  ```yaml
  tolerations:
    - key: "nvidia.com/gpu"
      operator: "Exists"
      effect: "NoSchedule"
  ```
- **Security Context**: `hostPID: true`, `hostIPC: true`, read-only mount to `/var/run/nvidia-dcgm` and `/proc`.
- **Resource Limits**: Requests `50m CPU, 64Mi RAM`; Limits `250m CPU, 256Mi RAM` ensuring zero overhead on customer workloads.
