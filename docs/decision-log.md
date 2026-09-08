# Architecture Decision Records (ADRs)

---

## ADR 001: Local-First Storage (SQLite by Default)
- **Context**: AI engineers need fast, zero-configuration local tracing during development and testing without spinning up Postgres, Redis, or external SaaS collectors.
- **Decision**: Use SQLite in WAL mode with indexed trace and span tables. Support JSONL as a flat-file alternative.
- **Consequences**: Zero infrastructure dependencies, instant setup (`< 5s`), portable database files.

---

## ADR 002: Zero-Crash SDK Design
- **Context**: Profiling tools must never bring down production or test agent execution pipelines if logging or disk writing fails.
- **Decision**: All storage operations and metadata serialization steps are guarded with safe exception blocks logging to stderr.
- **Consequences**: 100% execution reliability for the host application.

---

## ADR 003: Critical-Path Latency Calculation
- **Context**: AI workflows often invoke nested, sequential, and parallel tools. Simple sum of durations does not explain the bottleneck.
- **Decision**: Implement tree-based longest non-parallelized traversal to extract exact Critical-Path duration.
- **Consequences**: Engineers immediately see which exact step dictates the user-perceived turnaround time.

---

## ADR 004: OpenTelemetry Compatibility
- **Context**: Production teams eventually export traces to enterprise monitoring systems (Datadog, Honeycomb, Jaeger).
- **Decision**: Build an OpenTelemetry OTLP JSON exporter aligning with OpenTelemetry GenAI semantic conventions.
- **Consequences**: No vendor lock-in; easy migration to central OTel collectors.

---

## ADR 005: Rust Real-Time Data Plane Collector
- **Context**: Capturing high-frequency hardware metrics (10Hz / 100ms) like NVIDIA DCGM and NVML from a Python process introduces GIL contention and unwanted CPU overhead.
- **Decision**: Implement a native Rust DaemonSet collector (`crates/airun-collector`) featuring a sub-millisecond ring buffer, native DCGM/NVML bindings with synthetic fallback, and an OTLP/HTTP receiver (`:4318`).
- **Consequences**: Zero overhead impact on the Python AI workload; deterministic high-throughput ingestion.

---

## ADR 006: Hardware Physics & Power Modeling (IPD / IPW)
- **Context**: AI inference spend is fundamentally governed by data center electrical power and hardware depreciation, not just software token rates.
- **Decision**: Calibrate hardware accelerator profiles (H100, A100, B200, TPU v5e, MI300X) with TDP ratings, utility rates ($/kWh), and standard PUE 1.20 data center overhead to calculate Intelligence per Dollar (IPD) and Intelligence per Watt (IPW).
- **Consequences**: Bridges the gap between FinOps dollar spend and physical data center thermal realities.

---

## ADR 007: AI Breaker Box & Semantic Failover
- **Context**: Model provider outages, rate limits, and silent semantic quality collapse cascade into catastrophic downstream agent failures.
- **Decision**: Introduce a 3-state circuit breaker (`CLOSED`, `OPEN`, `HALF_OPEN`) coupled with Semantic Equivalence Mapping to translate prompts and tool calling schemas across OpenAI, Anthropic, Gemini, and Local models during automated DR drills.
- **Consequences**: Guarantees business continuity and eliminates single-provider lock-in.

---

## ADR 008: Multi-Dimensional Pareto Frontier & Eval-Driven Routing
- **Context**: Hardcoded model selections force engineering teams to choose between overpaying for frontier models or risking degraded task quality.
- **Decision**: Implement a dynamic Pareto optimal frontier engine evaluating models across Quality Score, Blended Cost per 1M tokens, and Turnaround Latency, backed by continuous shadow testing.
- **Consequences**: Proven cost reductions (often >90%) with mathematical guarantees that quality thresholds remain satisfied.

---

## ADR 009: Standardized 10-Event Pub/Sub Backbone
- **Context**: A polyglot system (Python SDK, Rust Collector, TypeScript API) requires a decoupled, resilient event communication contract.
- **Decision**: Define a standardized 10-event Pub/Sub schema and typed JSON envelope (`EventEnvelope`) implemented across all three languages (`src/airun/events/pubsub.py`, `crates/airun-collector/src/pubsub.rs`, `packages/control-plane/src/events.ts`).
- **Consequences**: Type-safe event streaming and consistent event semantics across the entire distributed lifecycle.

---

## ADR 010: Hybrid Local-First + Enterprise Control Plane
- **Context**: Developers need instant local profiling without cloud accounts, but platform engineering teams require centralized cluster visibility and automated remediation.
- **Decision**: Maintain a dual-mode topology: standalone zero-dependency local CLI/SQLite for individual engineers, and a TypeScript/Express control plane with PostgreSQL for multi-node enterprise deployments.
- **Consequences**: Optimal developer experience without sacrificing enterprise observability requirements.
