# AIRUN-100 Campaign: Outreach & Distribution Playbook

This playbook contains channel-specific copy and execution steps for the **AIRUN-100 Validation Campaign**.

---

## Channel 1: Hacker News & Reddit (r/MachineLearning, r/LocalLLaMA, r/ExperiencedDevs)

**Target Persona**: Systems engineers, backend architects, autonomous agent builders.

### Post Template

**Title**: `Show HN: airun – An open-source runtime profiler for agentic AI execution graphs and inference economics`

**Body**:
```markdown
Hey HN,

Over the past few months building multi-step LLM agents, we kept running into the same frustration: traditional APMs don't understand LLM tokens or execution DAGs, and cloud billing dashboards only show aggregate monthly dollar totals without explaining why a run was slow or expensive.

When an agent fails at step 8 of 10, the 7 preceding LLM calls cost real money, but that failure is completely invisible in provider dashboards. Similarly, unhandled tool timeouts trigger silent retry storms that spike token usage with zero business value.

We built **`airun`** (Apache 2.0) to solve this:
- **Zero-Friction Profiling**: Instrument functions or coroutines with `@trace` or prefix commands with `airun run`.
- **True DAG Critical-Path Engine**: Uses interval scheduling to compute exact critical paths across parallel `asyncio.gather()` tool calls without double-counting.
- **Outcome-Based Economics**: Explicitly separates **Cost per Successful Outcome** from **Wasted Cost** on failed/timeout branches.
- **Diagnostic Findings Engine**: Automatically tags cost concentration, retry loops, and over-provisioned models with `[CRITICAL]`, `[WARNING]`, and `[INFO]` badges.
- **Local-First & Private**: In-memory span overhead is $<20µs$, total disk persistence $<1ms$ in local SQLite WAL. Sensitive credentials are auto-redacted; no data leaves your machine.

**The Benchmark**:
We benchmarked a multi-step research agent before and after profiling. By converting sequential tool lookups into an async DAG fan-out and swapping the planner model to `gpt-4o-mini`, we achieved:
- **58.4% lower latency** (425ms → 177ms)
- **97.4% lower cost** ($0.03 → $0.0007)
- **Quality preserved** (0.94 → 0.95 eval score)

**We're doing 5 free pipeline teardowns**:
If you're running multi-step agents in staging or production, run 5 traces through `airun run` and I'll personally send you back a custom execution graph teardown showing your critical-path bottlenecks and wasted spend.

GitHub: https://github.com/sarkarbikram90/airun-profiler
Docs & Lab: https://github.com/sarkarbikram90/airun-profiler#readme

Feedback and teardown requests welcome below!
```

---

## Channel 2: LinkedIn & Twitter / X

**Target Persona**: VPs of Engineering, AI Platform Leads, FinOps Directors.

### Post Template

```markdown
Your AI agents are burning token budgets on silent retry storms. Here is the execution graph to prove it. 📉

As AI systems move from single-turn chat to autonomous multi-step loops, inference costs no longer scale linearly with users — they scale combinatorially with agentic depth.

Three things we routinely see in production agent architectures:
1. A 10-step agent fails at step 9 due to a database schema error. The 9 preceding LLM calls cost $4.20, but it shows up as "normal usage" on provider dashboards (100% wasted spend).
2. Sibling search tools are executed sequentially instead of in parallel async DAGs, adding 60% unnecessary latency.
3. Frontier models ($2.50+/1M tokens) are invoked for routine JSON extraction steps that a $0.15/1M model can handle with identical quality.

We built `airun`, an open-source, local-first runtime profiler and economic measurement layer for AI systems.

Benchmarking the same workload before and after `airun` profiling:
⚡ 58.4% faster latency
💰 97.4% lower inference cost
🎯 0.95 quality score preserved

As part of our AIRUN-100 campaign, we are doing complimentary 15-minute AI Execution Teardowns for engineering teams running multi-step pipelines.

If you'd like a custom execution graph teardown of your agent pipeline, comment "Teardown" or DM me.

Repo: https://github.com/sarkarbikram90/airun-profiler
```

---

## Channel 3: Direct Outbound (1-to-1 Cold Outreach)

**Subject**: `The execution graph for [Company]'s AI agents (and silent retry costs)`

```text
Hi [Name],

I'm building airun, an open-source runtime profiler for agentic AI workflows. We recently profiled a multi-step research agent and found that converting sequential tool calls into an async DAG fan-out, combined with model tiering, reduced inference costs by 97.4% while maintaining a 0.95 quality score.

I'm offering 10 complimentary "Pipeline Teardowns" this month for engineering teams operating multi-step agents. If you profile 5 traces of your staging agent with our zero-setup CLI (airun run), I will analyze your execution graph and send you back a custom report showing your critical-path bottlenecks, wasted spend on failed loops, and model optimization deltas.

No production access or code changes required — data stays 100% local on your machine.

Open to a 15-minute teardown this week?

Best,
Bikram Sarkar
Maintainer, airun
https://github.com/sarkarbikram90/airun-profiler
```

---

## Channel 4: Fulfillment Flow

1. **Prospect Accepts Teardown**: Send [`validation/quickstart-checklist.md`](quickstart-checklist.md).
2. **Prospect Shares Traces or Terminal Report**: Ingest the trace summary and execution tree.
3. **Generate Custom Teardown**: Populate [`validation/teardown-template.md`](teardown-template.md) with specific data points.
4. **Log Signal**: Record friction in [`validation/results/friction-log.md`](results/friction-log.md), user details in [`validation/results/users.md`](results/users.md), and pain points in [`validation/results/pain-ranking.md`](results/pain-ranking.md).
