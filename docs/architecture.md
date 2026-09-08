# System Architecture & Design

`airun` is architected as an ultra-low-overhead, local-first **AI Infrastructure Reliability & Economics Platform**. It bridges microsecond-level application runtime profiling directly with physical GPU cluster telemetry and an enterprise control plane.

---

## 1. High-Level Distributed Data Flow

```text
               ┌─────────────────────────────────────────────────────────┐
               │              AI Workload / Agent Application            │
               │   @trace / with trace()  •  OpenAI / Claude / Gemini    │
               └────────────────────────────┬────────────────────────────┘
                                            │ OTLP / HTTP (:4318) or In-Memory
                                            ▼
┌───────────────────────────────────────────────────────────────────────────────────────────┐
│                      RUST DATA PLANE COLLECTOR (DaemonSet / Node Agent)                    │
│   • Sub-millisecond Ring Buffer (10Hz / 100ms)     • OTLP Span Ingestion (:4318)          │
│   • NVIDIA DCGM & NVML Hardware Metric Scraper     • In-Memory Circuit Breaker State      │
└───────────────────────────────────────────┬───────────────────────────────────────────────┘
                                            │ Distributed Pub/Sub Events
                                            ▼
┌───────────────────────────────────────────────────────────────────────────────────────────┐
│                     STANDARDIZED 10-EVENT PUB/SUB BACKBONE                                │
│   workload.started • workload.completed • trace.created • gpu.alert • provider.degraded  │
│   provider.failed  • dr.drill.started   • dr.drill.completed • optimization.detected/app │
└───────────────────────────┬───────────────────────────────────────────────┬───────────────┘
                            │                                               │
                            ▼                                               ▼
┌───────────────────────────────────────────────┐   ┌───────────────────────────────────────┐
│    PYTHON ANALYTICS & CORRELATION ENGINE      │   │     TYPESCRIPT CONTROL PLANE API      │
│  • Time-Window Hardware-Trace Correlation     │   │   • Express / Node.js API Gateway     │
│  • Silicon Waste, MFU & Financial Bleed       │   │   • Commercial Wedge REST Endpoints   │
│  • Pareto Optimal Frontier & Eval Routing     │   │   • Automated Remediation Dispatch    │
│  • AI Breaker Box & Semantic DR Drills        │   │   • Multi-Tenant State Contracts      │
│  • AI-Aware Causal Incident Graph             │   └───────────────────┬───────────────────┘
└───────────────────────┬───────────────────────┘                       │
                        │                                               │
                        ▼                                               ▼
┌───────────────────────────────────────────────┐   ┌───────────────────────────────────────┐
│            LOCAL PERSISTENCE LAYER            │   │         ENTERPRISE DATABASE           │
│   • SQLite WAL Mode (.airun/traces.db)        │   │   • PostgreSQL with TimescaleDB       │
│   • Line-Delimited JSON (.airun/traces/)      │   │   • Long-term cluster telemetry       │
└───────────────────────┬───────────────────────┘   └───────────────────────────────────────┘
                        │
                        ▼
┌───────────────────────────────────────────────────────────────────────────────────────────┐
│                          PRESENTATION & OPERATIONAL SURFACES                              │
│   • Rich Terminal CLI (`airun waste`, `airun report`, `airun frontier`, `airun dr`)      │
│   • Executive Command Center Web Dashboard (`airun ui` / `airun serve`)                   │
│   • OpenTelemetry 1.0 Exporters (OTLP / Honeycomb / Datadog / Jaeger)                     │
└───────────────────────────────────────────────────────────────────────────────────────────┘
```

---

## 2. Core Subsystems

### A. Instrumentation SDK (`src/airun/sdk/`)
- Utilizes Python `contextvars.ContextVar` for coroutine-safe and thread-safe span hierarchy tracking.
- **Zero-Crash Guarantee**: Telemetry capture and storage writes are wrapped in safe exception boundaries; profiling failures output a warning to `stderr` without disrupting host business logic.
- **Privacy by Default**: Automatic recursive redaction of secrets, API keys, and bearer tokens. Prompt texts and completions are never captured without explicit user opt-in.
- Supports synchronous functions, `asyncio` coroutines, and generator workflows.

### B. Rust Data Plane Collector (`crates/airun-collector/`)
- Built for sub-millisecond execution overhead and minimal resource footprint on host compute nodes.
- In-memory ring buffer capturing NVIDIA DCGM and NVML metrics at 10Hz (100ms intervals): Streaming Multiprocessor (SM) active cycles, HBM memory bandwidth, PCIe throughput, temperature, and electrical power draw (Watts).
- Built-in OTLP/HTTP receiver listening on port `4318` for standard OpenTelemetry span ingestion.
- Local circuit breaker state machine executing sub-millisecond trip decisions on provider latency spikes or errors.

### C. Standardized 10-Event Pub/Sub Backbone (`src/airun/events/pubsub.py`)
- Unifies telemetry and actions across Python, Rust, and TypeScript components with structured event envelopes.
- Emits and consumes 10 canonical event types:
  - `workload.started`, `workload.completed`
  - `trace.created`
  - `gpu.alert`
  - `provider.degraded`, `provider.failed`
  - `dr.drill.started`, `dr.drill.completed`
  - `optimization.detected`, `optimization.applied`

### D. Hardware Physics, Waste & MFU Engine (`src/airun/analysis/waste.py`, `correlation.py`)
- Correlates logical trace spans with physical accelerator metrics across concurrent execution windows.
- Quantifies Model FLOPs Utilization (MFU) and computes **Real-Time Financial Bleed** ($/hr and $/run) from 4 physical bottlenecks:
  1. *Dataloader Starvation* (GPU SM idle waiting on CPU batch assembly)
  2. *NCCL Communication Stalls* (AllReduce fabric barrier delays)
  3. *PCIe Bus Saturation* (Host RAM $\leftrightarrow$ VRAM transfer bottlenecks)
  4. *Framework Overhead* (PyTorch eager dispatch bubbles)

### E. AI Economics & Accelerator Energy Engine (`src/airun/pricing/energy.py`, `engine.py`)
- Pre-calibrated thermal, electrical, and compute specs for NVIDIA H100 SXM5/PCIe, A100, B200 Blackwell, L40S, Google TPU v5e, and AMD Instinct MI300X.
- Calculates **Intelligence per Dollar (IPD)** and **Intelligence per Watt (IPW)** under standard PUE 1.20 data center thermal models and utility electricity rates ($0.10/kWh default).

### F. The Efficient Frontier & Eval-Driven Routing (`src/airun/routing/`)
- Computes multi-dimensional Pareto optimal frontiers across Quality Score, Cost per 1M tokens, and Turnaround Latency.
- Enforces SLA-based routing tiers (`TIER_1_CRITICAL`, `TIER_2_STANDARD`, `TIER_3_ECONOMY`) with continuous background shadow testing to safely validate candidate model substitutions.

### G. The AI Breaker Box & Automated Disaster Recovery (`src/airun/resilience/`)
- 3-state circuit breakers (`CLOSED`, `OPEN`, `HALF_OPEN`) protecting agent pipelines from upstream API outages, rate limits, and semantic quality collapse.
- Semantic Equivalence Mapping engine translating system instructions and tool calling schemas across OpenAI, Anthropic, Gemini, and Local dialects.
- Automated synthetic Disaster Recovery drills auditing continuity parity, quality retention, and failover economics.

### H. TypeScript Control Plane (`packages/control-plane/`)
- Enterprise Express API Gateway supporting PostgreSQL persistence with relational state contracts.
- Exposes commercial wedge endpoints:
  - `GET /api/v1/workloads/:id/cost-reliability`
  - `POST /api/v1/recommendations/:id/apply`
  - `GET /api/v1/events`

### I. Production Deployment (`deploy/`)
- **Kubernetes Manifests (`deploy/kubernetes/`)**: GKE/EKS DaemonSet agent, PersistentVolumeClaim storage, and AWS Application Load Balancer (ALB) Ingress.
- **Helm v3 Chart (`deploy/helm/airun-data-plane/`)**: Production packaging for scalable cluster installation.
- **Docker Compose (`deploy/compose/`)**: Multi-service local testbed unifying the Python workload, Rust collector, PostgreSQL database, and TypeScript control plane.

