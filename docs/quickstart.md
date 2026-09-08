# 5-Minute Quickstart Guide

`airun` is a lightweight, local-first profiler for AI workloads that answers:
> **"What exactly happened during this AI workload, and what did it cost?"**

---

## 1. Installation

Install `airun` via `pip`:

```bash
pip install airun-profiler
```

Or from source:

```bash
git clone https://github.com/sarkarbikram90/airun-tracing.git
cd airun-tracing
pip install -e .
```

---

## 2. Instant Demo & Health Check (Zero Setup)

Run the environment health check and simulated agent workflow without external API keys:

```bash
# Verify SQLite WAL mode and local environment
airun doctor

# Run instant offline demo trace
airun demo
```

You will see:
- High-level executive summary (outcome, total USD cost, tokens, latency, retries)
- Top cost drivers breakdown
- Visual execution tree hierarchy

---

## 3. Instrumenting Your Code

### Using the `@trace` Decorator

```python
from airun import trace, set_span_tokens, SpanKind

@trace(kind=SpanKind.LLM, model="gpt-4o", provider="openai")
def call_planner(task: str) -> str:
    # Your model call
    response = openai_client.chat.completions.create(...)
    set_span_tokens(input_tokens=1200, output_tokens=300)
    return response.choices[0].message.content
```

### Using Context Managers

```python
from airun import trace, SpanKind

with trace("customer_agent", kind=SpanKind.WORKFLOW) as root:
    # Step 1
    with trace("planning_step", kind=SpanKind.AGENT_STEP):
        plan = call_planner("Analyze quarterly revenue")

    # Step 2
    with trace("search_tool", kind=SpanKind.TOOL):
        data = search_web("Q3 2026 earnings")
```

---

## 4. CLI Inspection & Platform Commands

### Basic Tracing & Reports
```bash
# List captured traces
airun trace list

# Inspect execution hierarchy
airun trace show latest

# Generate detailed report with severity findings
airun report latest

# Compare two runs side-by-side (regression detection)
airun compare <baseline_trace_id> <optimized_trace_id>

# Export trace to OpenTelemetry OTLP JSON
airun export latest --format otel-json --output otel_trace.json
```

### Executive Command Center Web UI
```bash
# Launch interactive local web dashboard on http://localhost:8080
airun ui --port 8080
```

### Physics of AI Waste & Financial Bleed
```bash
# Analyze hardware stalls (Dataloader starvation, NCCL stalls, PCIe saturation, eager dispatch)
airun waste --hardware

# Inspect multi-agent spend attribution and model optimization deltas
airun waste --workload
```

### The Efficient Frontier & Eval Routing
```bash
# Render Pareto-optimal frontier table across Quality, Cost, and Latency
airun frontier
```

### AI Breaker Box & Disaster Recovery (DR)
```bash
# Check live circuit breaker states across AI providers
airun breaker status

# Run synthetic disaster recovery failover drill
airun dr drill
```

### Distributed Pipeline Verification
```bash
# Validate complete 6-tier distributed data pipeline
airun pipeline run
```
