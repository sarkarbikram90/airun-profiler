# Changelog

All notable changes to `airun` are documented in this file.

## [0.2.0] - 2026-09-07

### Added
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
  - Multi-stage Docker image automated publishing to `ghcr.io/sarkarbikram90/airun-tracing`.
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
