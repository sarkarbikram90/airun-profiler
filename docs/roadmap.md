# Post-MVP Evolution Roadmap

Following the strategic progression ladder:
```text
Observe → Explain → Optimize → Control → Automate
```

---

## Phase 1: Foundation & Observability (v0.1.0 – v0.1.2) — COMPLETED
- [x] Python SDK with `@trace` and `with trace()` (<20µs in-memory overhead)
- [x] Local SQLite / JSONL trace store with WAL mode
- [x] Directed execution graph (DAG) & interval critical-path analysis
- [x] Multi-provider token pricing engine (OpenAI, Anthropic, Gemini, Local)
- [x] Severity-graded terminal reports & side-by-side run comparator (`airun compare`)
- [x] OpenTelemetry 1.0 OTLP JSON export
- [x] Deterministic fixtures & benchmark test suite

---

## Phase 2: AI Infrastructure Reliability & Economics Platform (v0.1.3 – v0.1.4) — COMPLETED
- [x] **Rust Real-Time Data Plane (`crates/airun-collector`)**: High-throughput DaemonSet with 10Hz ring buffer, OTLP ingestion (`:4318`), and NVIDIA DCGM/NVML metric scraping.
- [x] **Hardware Economics & Energy Engine**: Intelligence per Dollar (IPD), Intelligence per Watt (IPW), and PUE 1.20 data center thermal modeling across H100, A100, B200, TPU v5e, and MI300X.
- [x] **Physics of AI Waste & MFU Engine**: Identification of the 4 canonical stalls (Dataloader, NCCL, PCIe, Eager mode) and Real-Time Financial Bleed ($/hr).
- [x] **The Efficient Frontier & Eval-Driven Routing**: Multi-dimensional Pareto optimal frontier and continuous background shadow testing.
- [x] **The AI Breaker Box & Automated Disaster Recovery (DR)**: 3-state circuit breakers, Semantic Equivalence Mapping across model dialects, and synthetic continuity drills.
- [x] **AI-Aware Causal Incident Graph**: Discrete root-cause graph linking physical hardware stalls to financial compute loss.
- [x] **Standardized 10-Event Pub/Sub Backbone**: Cross-service event envelopes unifying Python, Rust, and TypeScript.
- [x] **TypeScript Control Plane & PostgreSQL Integration (`packages/control-plane`)**: Commercial wedge REST API endpoints and remediation dispatch.
- [x] **Executive Command Center Dashboard (`airun ui`)**: Multi-tab live interface with Pareto visualization, golden signals, and DR simulation.
- [x] **Production Deployment Artifacts**: Kubernetes GKE/EKS manifests, Helm v3 charts, and Docker Compose testbed.

---

## Phase 2.5: Enterprise Standards & Closed-Loop Remediation (v0.1.5) — COMPLETED
- [x] **Native Prometheus / OpenMetrics Exporters (`/metrics`)**: Port 9445 DaemonSet HTTP exporter for DCGM metrics and Python `/metrics` gauge exporter.
- [x] **Standard OTLP Trace Ingestion Receiver (`POST /v1/traces`)**: Native OpenTelemetry collector endpoint in both Python and TypeScript control plane.
- [x] **Real-Time Live Streaming (WebSockets & SSE)**: Live WebSocket broadcast server (`/ws/live`) and Server-Sent Events (`/api/live/stream`).
- [x] **Automated Closed-Loop Remediation Policy Engine**: Active autonomous optimization with Pareto routing shifts, circuit breaker trips, and webhook alerts (`airun policy [list|evaluate]`).
- [x] **High-Throughput Concurrency & Load Benchmark Suite**: Multi-threaded stress testing (50 threads / 1,050 spans, p99 < 1.5ms) and 100k samples Rust ring buffer.

---

## Phase 3: Distributed Agent Fleets & Cluster Autonomics (v0.2.0) — COMPLETED
- [x] **In-Kernel eBPF Network Fabric Tracing**: Kernel tracepoint probes (`kfree_skb`, `net_dev_xmit`, `rdma_retransmit`) for RoCE/InfiniBand packet drops, PFC pause frame storms, and NCCL buffer queue inspection in Rust and Python.
- [x] **Multi-Cluster Cross-Cloud Federation**: Centralized control-plane state aggregation and intelligent MFU-per-dollar placement across hybrid multi-cloud clusters (GCP GKE + AWS EKS + Azure AKS + on-premise DGX SuperPOD).
- [x] **Live Silicon CI Hardware Testing**: Physical NVIDIA H100/A100 GPU hardware verification test suite, Kubernetes GPU self-hosted runner manifest (`deploy/ci/gpu-runner.yaml`), and dedicated GitHub Actions workflow (`.github/workflows/gpu-hardware-ci.yml`).
- [ ] **Automated Remediation Loop**: Autonomic worker scaling, automated `torch.compile` injection, and dynamic batch size tuning.
- [ ] **Prompt Prefix Cache Optimizer**: Predictive ROI modeling for OpenAI and Anthropic prefix cache hits.
- [ ] **LangChain, LlamaIndex, CrewAI, and AutoGen Native Hooks**: Zero-code automatic callback instrumentation.

---

## Phase 4: Enterprise Commercial Platform (v0.3.0+)
- [ ] Multi-tenant RBAC with SSO/SAML authentication.
- [ ] FinOps budget allocation & chargeback tagging by business unit/team.
- [ ] SOC2 Type II compliance audit logs and cryptographic trace attestations.

