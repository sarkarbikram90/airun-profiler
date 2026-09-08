# `agent.md` — AI Runtime Profiler (`airun`) Developer & AI Agent Guide

> **Welcome AI Agents & Engineers**: This file provides an architectural blueprint, design invariants, codebase layout, testing workflows, and operating protocols for `airun`. Use this as your primary context when exploring, evaluating, extending, or testing the repository.

---

## 1. Executive Summary & Strategic Thesis

### What is `airun`?
`airun` is an open-source, local-first **AI Runtime Profiler and Economic Measurement Layer** for Python 3.11+. It answers one core question:
> **"What exactly happened during this AI workload, and what did it cost?"**

### Strategic Progression
```text
Observe → Explain → Optimize → Control → Automate
```
- **v0.1.x**: **Observe & Explain** — Zero-overhead DAG tracing, token pricing engine, interval critical-path analysis, and severity-graded diagnostic findings.
- **v0.1.4 (Current)**: **AI Infrastructure Reliability & Economics Platform** (as specified in `spec.md`):
  1. *Intelligence per Dollar (IPD) & Watt (IPW)* with hardware accelerator power modeling (H100, A100, B200, TPU).
  2. *The Efficient Frontier of AI & Eval-Driven Routing* with Pareto optimality and background shadow testing.
  3. *The AI Breaker Box & Automated Disaster Recovery (DR)* with Semantic Equivalence Mapping across providers.
  4. *AI-Aware Causal Incident Graph* linking physical silicon and fabric stalls to unrecoverable compute dollars.
  5. *Executive Command Center Web UI* (`airun ui`) and rich CLI commands (`metrics`, `frontier`, `dr`, `breaker`).

---

## 2. System Architecture & Directory Layout

```text
airun-tracing/
├── src/airun/                      # Core Package (18 modules, 83% test coverage)
│   ├── __init__.py                 # Top-level exports: trace, SpanKind, calculate_energy, EvalRouter, etc.
│   ├── __main__.py                 # CLI entrypoint for 'python -m airun'
│   ├── config.py                   # Pydantic configuration loader (.airun/config.yaml)
│   ├── sdk/                        # Instrumentation SDK
│   │   ├── tracer.py               # Universal @trace decorator & TraceContext manager
│   │   ├── context.py              # ContextVar-based trace & span stack management
│   │   ├── redaction.py            # Automatic API key & secret redaction engine
│   │   └── wrappers.py             # Client wrappers (OpenAI client auto-instrumentation)
│   ├── events/                     # Data Models
│   │   └── models.py               # TraceSpan, TraceSummary (with Energy, IPD, IPW telemetry)
│   ├── store/                      # Persistence Layer
│   │   ├── base.py                 # Abstract TraceStore interface
│   │   ├── sqlite.py               # Local SQLite store with WAL mode & prefix queries
│   │   └── jsonl.py                # Line-delimited JSON fallback store
│   ├── graph/                      # DAG Execution Graph Engine
│   │   ├── builder.py              # SpanNode & ExecutionGraph (fan-out, joins, descendants)
│   │   └── critical_path.py        # Interval dynamic programming critical-path calculator
│   ├── analysis/                   # Economic & Diagnostic Intelligence
│   │   ├── analyzer.py             # Energy, IPD/IPW, aggregations, wasted cost, severity findings
│   │   └── comparator.py           # Trace comparison engine & regression diffing
│   ├── pricing/                    # Pricing & Electrical Energy Engine
│   │   ├── defaults.py             # Built-in model rates (OpenAI, Anthropic, Gemini, Llama)
│   │   ├── energy.py               # Hardware accelerator power draw (TDP), Joules, kWh, IPD, IPW
│   │   └── engine.py               # Integrated token + infra + energy cost calculator
│   ├── routing/                    # Eval-Driven Routing & The Efficient Frontier of AI
│   │   ├── frontier.py             # Multi-dimensional Pareto optimal frontier calculator
│   │   └── eval_router.py          # Tier-based routing policy & background shadow testing
│   ├── resilience/                 # AI Disaster Recovery & The AI Breaker Box
│   │   ├── breaker.py              # Circuit breakers (CLOSED, OPEN, HALF_OPEN) for AI providers
│   │   ├── semantic_mapper.py      # Schema & prompt translator (OpenAI, Anthropic, Gemini, Local)
│   │   └── dr_drills.py            # Automated synthetic Disaster Recovery drills & continuity audits
│   ├── incident/                   # AI-Aware Causal Incident Graph
│   │   └── graph.py                # Discrete causal graph linking silicon & fabric stalls to waste
│   ├── server/                     # Executive Command Center Web UI & REST APIs
│   │   └── __init__.py             # Multi-tab Executive Command Center, Pareto visualizer, REST API
│   ├── cli/                        # Rich Terminal CLI
│   │   ├── main.py                 # Typer app (doctor, run, report, compare, metrics, frontier, dr, breaker)
│   │   └── formatting.py           # Rich panels, Pareto tables, DR drill scorecards, DAG trees
│   └── utils/                      # Utilities
│       └── time_utils.py           # Sub-millisecond timing, ISO formatters, currency formatting
├── examples/                       # Executable Examples & AI Workload Laboratory
│   ├── simple_workflow.py          # Basic linear workflow
│   ├── agent_with_tools.py         # Multi-step agent with parallel tools
│   ├── failing_workflow.py         # Injected failure with wasted cost demonstration
│   └── lab/                        # AI Workload Laboratory (10 Economic Archetypes)
│       ├── chat_workload.py        # Archetype 1: Simple LLM Assistant
│       ├── rag_workload.py         # Archetype 2: RAG Retrieval & Synthesis
│       ├── tool_agent_workload.py  # Archetype 3: Tool Agent with Retries & Concurrency
│       ├── coding_agent_workload.py# Archetype 4: Debugger Loop (Partial Success)
│       ├── multi_agent_workload.py # Archetype 5: Multi-Agent Synthesis Pipeline
│       ├── comparison_workload.py  # Archetype 6: Cost & Latency Regression Lab
│       └── run_all.py              # Batch runner for cross-archetype comparative table
├── tests/                          # 38 Passing Unit, Integration, and Benchmark Tests
│   ├── unit/                       # Models, graph DAG, pricing, analyzer, redaction, store
│   ├── integration/                # CLI commands, doctor, demo, trace-id-file, OTel exports
│   └── benchmarks/                 # Micro-overhead validation (<20µs in-memory, <1ms disk)
├── validation/                     # External Validation & Discovery Kit (AIRUN-100)
│   ├── AIRUN-100.md                # Milestone charter, archetype matrix, operating rules
│   ├── invitation.md               # Zero-pitch outreach message template
│   ├── quickstart-checklist.md     # 4-step onboarding checklist (< 3 minutes)
│   ├── feedback-form.md            # 9-point feedback form with counterfactual questions
│   ├── sample-workloads/           # 4 standalone user test scripts
│   └── results/                    # Campaign tracking: users.md, friction-log.md, pain-ranking.md
├── pyproject.toml                  # Packaging specification (airun-profiler 0.1.1)
├── Dockerfile                      # Self-contained container environment
├── docker-compose.yml              # Multi-container lab composition
└── Makefile                        # Standard developer targets (test, lint, lab, doctor)
```

---

## 3. Core Primitives & Invariant Design Rules

When implementing or modifying code, **always uphold these five invariants**:

### Rule 1: The Zero-Crash Guarantee
Instrumentation code must **never** crash or disrupt the host application.
- All tracer exit handlers wrap disk operations in `try...except Exception`.
- If storage write fails, an error is written to `sys.stderr` and execution proceeds uninterrupted.

### Rule 2: Ultra-Low Overhead Ceiling
- **In-Memory Spans**: Overhead is measured at $< 20\mu\text{s}$ per span.
- **Disk Persistence**: Total SQLite transaction duration must remain $< 1\text{ms}$ per workflow.
- Ephemeral benchmarks and doctor diagnostics must pass `save_on_exit=False` to avoid disk I/O pollution.

### Rule 3: Privacy by Default
- Prompt text and completion contents are **never** recorded unless explicitly configured.
- Sensitive keys (`api_key`, `authorization`, `token`, `bearer`, `password`, `secret`) are automatically redacted via recursive masking in [`src/airun/sdk/redaction.py`](file:///c:/Users/bikrams/airun-tracing/airun-tracing/src/airun/sdk/redaction.py).

### Rule 4: Windows Console ASCII Compatibility
- Console formatters must strictly use ASCII-safe status tags (`[OK]`, `[!]`, `[INFO]`, `*`) rather than raw Unicode emojis to prevent `cp1252` encoding crashes on Windows cmd/PowerShell.

### Rule 5: True Directed Acyclic Graph (DAG) Execution Model
- Traces model parallel executions using reciprocal linkages (`parents`, `children`, `parent_ids`, `child_ids`).
- Concurrency speedups and critical-path durations are computed using interval scheduling dynamic programming in [`src/airun/graph/critical_path.py`](file:///c:/Users/bikrams/airun-tracing/airun-tracing/src/airun/graph/critical_path.py).

---

## 4. Key Models & Diagnostic Concepts

### 1. `TraceSpan` & `TraceSummary` ([`src/airun/events/models.py`](file:///c:/Users/bikrams/airun-tracing/airun-tracing/src/airun/events/models.py))
- **`wasted_cost_usd`**: 100% of total spend for failed/timeout workflows; cost of failed steps for partial successes.
- **`cost_per_successful_outcome_usd`**: Total spend attributed only to successful completions.
- **`quality_score`** (0.0 to 1.0) & **`evaluation_metrics`** (dict): Evaluation provenance tracking to prove economic optimizations preserve outcome quality.

### 2. Severity-Graded Diagnostic Findings
- **`CRITICAL`** (Red): Workflow failures (100% wasted cost), cost concentration $\ge 50\%$, retry storms ($\ge 3$ attempts or $> 1.0\text{s}$ delay).
- **`WARNING`** (Yellow): Cost concentration $30-50\%$, $1-2$ retries, token context growth $\ge 2.5\times$, step failures.
- **`INFO`** (Cyan): Over-provisioned model candidates (output $< 100$ tokens, latency $< 400\text{ms}$), local inference zero-cost credits, parallel tool speedups, unknown custom model pricing rates.

---

## 5. Developer & AI Agent Command Reference

### Running Tests & Quality Checks
```bash
# Run full pytest test suite with coverage report
pytest -v --cov=airun --cov-report=term-missing

# Run linter and code style checks
ruff check src tests examples validation
ruff format src tests examples validation

# Build packaging distribution & verify PyPI metadata
python -m build
twine check dist/*
```

### CLI Operations
```bash
# Run workspace & SQLite WAL connectivity health check
airun doctor

# Run offline demo simulation
airun demo

# Profile a Python script with deterministic CI trace capture
airun run --trace-id-file .airun/trace_id examples/agent_with_tools.py

# Inspect detailed report with severity-graded findings
airun report latest

# Compare two runs side-by-side (delta in duration, cost, tokens, quality)
airun compare previous latest

# Export trace to OpenTelemetry OTLP format
airun export latest --format otel-json
```

### Running the AI Workload Laboratory
```bash
# Execute all 6 laboratory archetypes and render cross-workload comparison table
python examples/lab/run_all.py
```

---

## 6. How to Instrument Code

### Synchronous Tracing
```python
from airun import trace, SpanKind, set_span_tokens, set_span_quality

@trace(kind=SpanKind.LLM, model="gpt-4o", provider="openai")
def generate_summary(prompt: str) -> str:
    # LLM inference call...
    set_span_tokens(input_tokens=1200, output_tokens=350)
    set_span_quality(0.95, {"correctness": 0.96, "evaluator": "human_curated"})
    return "Summary result"

with trace("document_pipeline", kind=SpanKind.WORKFLOW):
    result = generate_summary("Analyze document")
```

### Asynchronous Parallel Tool Tracing
```python
import asyncio
from airun import trace, SpanKind, record_retry, set_span_metadata

async def fetch_web_data():
    async with trace("search_tool", kind=SpanKind.TOOL):
        record_retry()  # Records retry if flaky
        set_span_metadata({"query": "AI Runtime", "count": 5})

async def fetch_database():
    async with trace("db_tool", kind=SpanKind.DB):
        set_span_metadata({"table": "users", "rows": 10})

async with trace("agent_workflow", kind=SpanKind.WORKFLOW):
    async with trace("parallel_fetch", kind=SpanKind.AGENT_STEP):
        await asyncio.gather(fetch_web_data(), fetch_database())
```

---

## 7. Milestone AIRUN-100 Validation Protocol

During the validation campaign, follow these rules:
1. **Feature Freeze**: No new speculative features. Only validation-blocking defect fixes.
2. **Record Every Friction Point**: Log all setup, concept, trust, and action friction in [`validation/results/friction-log.md`](file:///c:/Users/bikrams/airun-tracing/airun-tracing/validation/results/friction-log.md).
3. **Capture Existing Workarounds**: In [`validation/results/pain-ranking.md`](file:///c:/Users/bikrams/airun-tracing/airun-tracing/validation/results/pain-ranking.md), document what teams currently do (e.g. custom scripts, billing alerts, regex message pruning).
4. **Rank Opportunities Using 4D Formula**:
   $$\text{Opportunity Score} = \text{Frequency} \times \text{Severity} \times \text{Willingness to Pay} \times \text{Technical Feasibility}$$
5. **Probe the "So What?" Question**: For every finding, discover whether the engineer *acted*, *couldn't fix*, or *ignored*.
