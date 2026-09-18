# Changelog

All notable changes to `airun` are documented in this file.

## [0.1.6] - 2026-09-18

### Added
- **In-Kernel eBPF Fabric Tracing**:
  - Rust DaemonSet (`crates/airun-collector/src/ebpf.rs`): Kernel-level InfiniBand/RoCE packet drops (`kfree_skb`), PFC pause frame counters, and NCCL buffer queue inspection with Linux tracepoints, sysfs, and mock fallback.
  - Rust Collector OpenMetrics metrics: `airun_fabric_packet_drops_total`, `airun_fabric_pfc_pause_frames_total`, `airun_nccl_buffer_queue_depth_bytes`.
  - Python Analytics (`src/airun/analysis/correlation.py`): Sub-millisecond correlation of eBPF network fabric congestion events directly with distributed NCCL synchronization stalls and financial waste.
- **Multi-Cluster Cross-Cloud Federation**:
  - TypeScript Control Plane (`packages/control-plane/src/db.ts` & `src/index.ts`): Federated cluster registry and placement engine across GCP GKE, AWS EKS, Azure AKS, and on-premise DGX SuperPODs.
  - Endpoints: `GET /api/v1/federation/clusters`, `GET /api/v1/federation/overview`, `POST /api/v1/federation/clusters`, `POST /api/v1/federation/placement`.
  - Python Typer CLI (`airun cluster`):
    - `airun cluster list [--provider] [--accelerator]`: Renders rich multi-cloud cluster table.
    - `airun cluster overview`: Displays global GPU footprint, aggregate spend, and total financial bleed.
    - `airun cluster recommend <workload> [--gpus] [--accelerator] [--max-rate]`: Multi-cloud workload placement optimized for MFU-per-dollar efficiency.
- **Live Silicon CI Hardware Testing**:
  - Physical GPU Hardware Test Suite (`tests/hardware/test_silicon_hardware.py`): Queries device name, driver version, memory, SM utilization, thermal temperatures, and power draw using `nvidia-smi` and `pynvml`, with graceful degradation in virtualized/CPU-only CI environments.
  - Self-Hosted GPU Runner Manifest (`deploy/ci/gpu-runner.yaml`): Kubernetes deployment for running GitHub Actions self-hosted runners on NVIDIA H100/A100 nodes with DCGM, InfiniBand, and tracepoint volume mounts.
  - Dedicated Hardware CI Workflow (`.github/workflows/gpu-hardware-ci.yml`): Continuous testing against live silicon hardware runners.
- **1-Click Web UI Example Data Seeding (`POST /api/demo`)**:
  - Added a prominent **"⚡ Load Example Data"** button directly to the Web UI (`airun ui`) navigation bar and empty states.
  - In-browser seeding endpoint (`POST /api/demo` & `GET /api/demo`): Instantly generates 4 realistic AI workloads (Multi-Agent Research Pipeline with Claude 3.5 Sonnet & GPT-4o, Customer Support RAG with Cohere reranking, Distributed 8x H100 Pretraining with hardware energy metrics, and Resilience Drill with transient retry recovery).


## [0.1.5] - 2026-09-18

### Added
- **Native Prometheus & OpenMetrics Exporters (`/metrics`)**:
  - Rust DaemonSet (`crates/airun-collector`): Dedicated HTTP server on port `9445` exporting live DCGM GPU silicon metrics (`airun_gpu_sm_utilization_pct`, `airun_gpu_memory_used_bytes`, `airun_gpu_power_watts`, `airun_gpu_temperature_celsius`, `airun_collector_samples_total`).
  - Python Runtime (`src/airun/server`): Standard Prometheus gauge and counter exporter at `GET /metrics` (`airun_traces_total`, `airun_cost_usd_total`, `airun_tokens_total`, `airun_wasted_cost_usd_total`, `airun_circuit_breaker_state`).
- **Standard OTLP Trace Ingestion Receiver (`POST /v1/traces`)**:
  - Full ingestion compatibility with LangChain, vLLM, LiteLLM, and OpenLLMetry.
  - Python: `otlp_payload_to_trace_records()` in `src/airun/exporters/otlp.py` mapping `resourceSpans`, model parameters, token usage, and span hierarchies. Exposed at `POST /v1/traces` and `POST /api/traces`.
  - TypeScript: Ingestion receiver at `POST /v1/traces` in `packages/control-plane/src/index.ts` streaming external spans directly into PostgreSQL / in-memory state.
- **Real-Time Live Streaming (WebSockets & SSE)**:
  - TypeScript Control Plane: Real-time WebSocket server at `/ws/live` broadcasting all distributed pub/sub events (`AirunEventEnvelope`) to connected dashboards.
  - Python Web Server: Live Server-Sent Events stream at `GET /api/live/stream`.
- **Automated Closed-Loop Remediation Policy Engine**:
  - `src/airun/resilience/remediation_engine.py`: Autonomously evaluates live trace findings and hardware telemetry against declarative policies.
  - Interventions: Pareto-optimal model routing shifts (`ROUTING_SHIFT`), automated circuit breaker trips (`CIRCUIT_BREAKER_TRIP`), webhook alerts (`WEBHOOK_DISPATCH`), and structured audit logging (`LOG_AUDIT`).
  - Rich CLI commands: `airun policy list` and `airun policy evaluate [trace_id]`.
- **High-Throughput Concurrency & Load Benchmark Suite**:
  - Python: `tests/benchmarks/test_load_concurrency.py` benchmarking 50 concurrent threads executing 1,050 spans (verified p99 latency < 1.5ms and zero deadlocks) and 100 concurrent async coroutines.
  - Rust: `test_ring_buffer_high_throughput` benchmarking 100,000 samples through the lock-free ring buffer exceeding 500,000 ops/sec.

## [0.1.4] - 2026-09-07

### Added
- **Distributed Pipeline Engine (`airun pipeline run`)**: Validates the complete 6-tier distributed data path (Python Workload -> Rust Collector -> Pub/Sub -> Python Analytics -> PostgreSQL -> TypeScript API).
- **Standardized 10-Event Pub/Sub Backbone**: Codified distributed event schemas and envelopes across Python (`src/airun/events/pubsub.py`), Rust (`crates/airun-collector/src/pubsub.rs`), and TypeScript (`packages/control-plane/src/events.ts`):
  - `workload.started`, `workload.completed`, `trace.created`, `gpu.alert`, `provider.degraded`, `provider.failed`, `dr.drill.started`, `dr.drill.completed`, `optimization.detected`, `optimization.applied`.
- **The Commercial Wedge API & Scorecard**:
  - `GET /api/v1/workloads/:id/cost-reliability` answering: *"What is my AI app costing me, where is it wasting money/latency, and what should I change?"*
  - `POST /api/v1/recommendations/:id/apply` executing automated remediation with Pub/Sub event dispatch.
  - `GET /api/v1/events` serving the distributed event feed.
- **PyPI Discoverability & Presentation**:
  - PEP 621 `[project.urls]` navigation buttons in PyPI sidebar (Homepage, Documentation, Repository, Issue Tracker, Changelog, Specification).
  - High-intent search keywords (`nvidia-dcgm`, `gpu-optimization`, `finops`, `h100`, `mfu`, `cuda`, `pytorch-profiler`, `silicon-waste`).
  - Trove classifiers and live download/star badges.

## [0.1.3] - 2026-09-07

### Added
- **Rust Real-Time Data Plane (`crates/airun-collector`)**: High-throughput DaemonSet with in-memory ring buffer (10Hz / 100ms), OTLP span ingestion (`:4318`), DCGM/NVML scraping with graceful fallback, and sub-millisecond circuit breaker state machine.
- **Time-Window Correlation Engine (`src/airun/analysis/correlation.py`)**: Connects logical trace spans directly to physical GPU silicon stalls (SM active cycles, PCIe TX/RX saturation, true power draw).
- **Terrifyingly Specific Hardware Bleed Reporting (`airun waste --hardware`)**: Exact dollar loss per week, hardware symptoms, root causes, and actionable configuration fixes.
- **Workload Economics & FinOps Optimization (`airun waste --workload`)**: Multi-agent spend attribution and projected cost, latency, and quality improvements from model routing.
- **TypeScript Control Plane API Gateway (`packages/control-plane`)**: Express API with PostgreSQL state contracts and Pub/Sub event schemas.
- **Production Kubernetes & Helm Deployment Artifacts (`deploy/helm/airun-data-plane/`, `deploy/kubernetes/daemonset-agent.yaml`)**.
- **AI Infrastructure Command Center (`airun ui` / `airun serve`)**:
  - Executive KPI Command Center displaying Compute Cost, Energy Spend, Cluster & Effective Utilization, Intelligence / $, Intelligence / Watt, and Wasted Compute.
  - Interactive top bottleneck incident banner with daily projected savings and remediation recommendations.
  - Efficient Frontier visualizer plotting models across Quality vs Cost vs Latency with Pareto status.
  - The AI Breaker Box provider status cards with live state indicators (`CLOSED`, `OPEN`, `HALF-OPEN`) and one-click Disaster Recovery (DR) simulation.
  - AI-Aware Causal Incident Graph inspector mapping physical silicon, fabric stalls, and barrier timeouts to wasted compute dollars.
- **Hardware Accelerator Power & Energy Economics Engine (`src/airun/pricing/energy.py`)**:
  - Electrical specifications and TDP profiles for NVIDIA H100 (SXM & PCIe), A100, B200 Blackwell, L40S, Google TPU v5e, AMD MI300X, and Apple Silicon.
  - Data center PUE (1.20) and utility electricity schedule modeling ($/kWh).
  - Formulas for **Intelligence per Dollar (IPD)**, **Intelligence per Watt (IPW)**, Tokens/$, and Tokens/kWh.
- **The Efficient Frontier of AI & Eval-Driven Routing (`src/airun/routing/`)**:
  - Multi-dimensional Pareto frontier calculator across Quality Score, Blended Cost per 1M tokens, and Typical Latency.
  - Tier-based routing policy engine (`TIER_1_CRITICAL`, `TIER_2_STANDARD`, `TIER_3_ECONOMY`).
  - Continuous shadow testing simulator to evaluate cheaper candidate models on live traffic without SLA violation.
- **The AI Breaker Box & AI Disaster Recovery (DR) Continuity (`src/airun/resilience/`)**:
  - Resilient circuit breaker state machine (`CLOSED`, `OPEN`, `HALF-OPEN`) protecting against API outages, latency spikes, and silent semantic quality collapse.
  - Semantic Equivalence Mapping engine translating system prompts, parameter bounds, and tool schemas across OpenAI, Anthropic, Google Gemini, and Local dialects.
  - Automated synthetic Disaster Recovery drills (`airun dr drill`) measuring capability parity, quality retention, and economic delta.
- **AI-Aware Causal Incident Graph (`src/airun/incident/`)**:
  - Discrete causal graph linking hardware degradations (GPU Xid 79, PCIe Gen1 throttling), network fabric deadlocks (PFC buffer overruns), and AllReduce barrier stalls to financial compute loss.
- **New CLI Commands (`src/airun/cli/`)**:
  - `airun metrics [trace_id]`: Executive Economics panel showing IPD, IPW, energy consumption, and cluster efficiency.
  - `airun frontier`: Displays the Efficient Frontier table and Pareto-optimal models.
  - `airun dr drill`: Runs automated synthetic DR drill and prints the continuity audit scorecard.
  - `airun breaker status`: Renders live AI Breaker Box circuit states across providers.
- **New Executable Workloads (`examples/`)**:
  - `examples/eval_routed_workflow.py`: Eval-driven routing and shadow testing.
  - `examples/disaster_recovery_drill.py`: Fault injection, AI Breaker trip, and semantic failover.
  - `examples/energy_and_power_profiling.py`: H100 TDP power profiling and Intelligence per Watt metrics.

## [0.1.2] - 2026-08-30

### Added
- **Interactive Executive Web Dashboard (`airun ui` / `airun serve`)**:
  - Built-in modern dark-mode single-page Web UI displaying high-level FinOps KPIs, execution trace tables, and DAG waterfall timelines.
  - Severity-graded diagnostic findings panel (`[CRITICAL]`, `[WARNING]`, `[INFO]`) highlighting cost concentration, retry storms, and context bloat.
  - Zero-dependency HTTP REST API endpoints (`/api/traces`, `/api/traces/<id>`, `/api/summary`, `/api/compare`, `/healthz`).
  - Resilient networking with automatic port fallback (defaulting to `127.0.0.1:8765`) to prevent Windows socket permission collisions (`WinError 10013`).
- **Real-World Multi-Model Agent Pipeline**:
  - `examples/live_multi_model_agent.py` demonstrating live production agent profiling across Google Gemini (1.5 Flash), OpenAI (GPT-4o), Anthropic (Claude 3.5 Haiku), and Vector DB tools.
  - Automatic fallback simulation when live API keys are not exported in the environment.
- **AWS EKS Deployment Blueprint**:
  - Production-ready Kubernetes manifests in `deploy/kubernetes/` (`pvc.yaml`, `deployment.yaml`, `service.yaml`, `ingress.yaml`, `kustomization.yaml`).
  - AWS Application Load Balancer (ALB) and AWS EBS `gp3` persistent volume configuration.
  - Step-by-step deployment guide in `docs/aws-eks-deployment-guide.md`.
- **GitHub Container Registry (GHCR) Packages Automation**:
  - Multi-stage Docker image automated publishing to `ghcr.io/sarkarbikram90/airun-profiler`.
  - Future release and publishing runbook in `docs/release-guide.md`.

## [0.1.1] - 2026-08-29

### Added
- **`airun run`**: Transparent execution runner that profiles scripts and outputs a post-run summary immediately.
- **`airun doctor`**: Workspace diagnostic command that checks config, storage health, trace count, and micro-overhead.
- **Trace ID Aliases**: `latest`, `last`, `previous`, and `prev` supported across all CLI commands (`report`, `show`, `compare`, `export`).
- **Concurrent DAG Critical Path**: Interval DAG dynamic programming scheduler for accurate critical-path computation across overlapping sibling spans.
- **Actionable Diagnostic Findings**: Rule-based economic and performance insights generated in `airun report` (cost concentration, retry storms, token bloat, over-provisioned models).
- **Cost / Success vs Wasted Cost**: Explicit outcome-based cost attribution calculating wasted dollars on failed/interrupted runs.
- **Trace ID Prefix Matching**: Convenient sub-string lookups for trace IDs in SQLite and JSONL backends.
- **AI Workload Laboratory**: 5 representative agent archetypes in `examples/lab/` with cross-workload comparison runner.
- **External Validation Kit**: Standardized invitation template, checklist, feedback questionnaire, and sample workloads in `validation/`.

## [0.1.0] - 2026-08-29

### Added
- Initial MVP release of `airun`.
- Python SDK with `@trace` decorator and `with trace()` context manager.
- Local SQLite and JSONL trace stores with zero network requirements.
- Cost engine with multi-model pricing (OpenAI, Anthropic, Gemini, local GPU).
- OpenTelemetry OTLP JSON trace exporter.
- Typer CLI with `init`, `demo`, `trace list`, `trace show`, `report`, `compare`, `export`.
- Dockerfile, docker-compose, CI/CD GitHub Actions workflows.
