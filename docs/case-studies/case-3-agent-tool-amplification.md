# Case Study 3: Agent Tool Amplification, Duplicate Queries & Retry Cascades

## Executive Summary
An autonomous multi-agent research assistant was experiencing an unexpected **4x surge in operational token costs ($6,280/month in avoidable spend)** alongside frequent 20+ second turnaround times. Using `airun agent analyze`, engineers discovered that transient tool timeouts triggered unjittered retry loops, which amplified prompt context size by 3.8x and forced expensive downstream frontier LLM re-invocations.

---

## 1. Environment
- **Architecture**: Multi-Agent orchestration (Planner $\rightarrow$ Web Research $\rightarrow$ Vector Memory $\rightarrow$ Synthesis)
- **Primary Frontier Model**: Claude 3.5 Sonnet (OpenAI GPT-4o fallback)
- **Tool Protocol**: Model Context Protocol (MCP) server for document retrieval & external search
- **Runtime**: Python 3.12 async pipeline with LangGraph

---

## 2. Workload
- **Workload Type**: In-depth competitive intelligence report generation
- **Expected Turnaround**: 6.0 seconds per report, target cost < $0.05/report
- **Actual Turnaround**: 22.4 seconds per report, actual cost $0.214/report

---

## 3. Raw Execution DAG Telemetry
```text
Trace Spans:
- Root Workflow:                   research_report_generation (22.4s)
- Step 1: Agent Planning           2.1s (gpt-4o: 1,400 in / 450 out)
- Step 2: Tool Phase               14.8s total
  - Tool Call: web_search          Failed (HTTP 429 Rate Limit) at 2.4s
  - Tool Retry 1: web_search       Failed (HTTP 504 Timeout) at 5.2s
  - Tool Retry 2: web_search       Success (2.1s)
  - Duplicate Vector Query:        "market trends 2026" executed 3x across 2 sub-agents
- Step 3: Synthesis                5.5s (claude-3-5-sonnet: 14,200 in / 1,800 out)
  * Notice: Prompt context inflated from 1,400 tokens to 14,200 tokens
    due to unpruned raw HTML and stacked error tracebacks in context!
```

---

## 4. `airun agent analyze` Audit Output

```bash
$ airun agent analyze trace-agent-loop-03
```

```text
+------------------------ AGENT EFFICIENCY REPORT ------------------------+
| 64.2% of execution cost is attributable to redundant work ($0.1374).   |
| Potential critical-path latency savings: 13.60s                         |
|                                                                         |
| Top findings:                                                           |
| 1. Retry amplification & cascading backoff: Transient tool failure      |
|    triggered 2 sequential retries, blocking inference thread for 7.6s.  |
|    -> Fix: Deploy AI Breaker Box with 500ms trip threshold and fallback.|
| 2. Prompt context inflation: Raw tool outputs and error stack traces   |
|    expanded prompt token count by 3.8x (1,400 -> 14,200 tokens).        |
|    -> Fix: Sanitize and summarize tool results before passing to synth. |
| 3. Duplicate retrieval queries: Vector DB queried 3x with identical    |
|    embeddings within the same execution turn.                           |
|    -> Fix: Enable semantic query memoization with 5-minute cache TTL.   |
|                                                                         |
| MCP Server Observability:                                               |
| * search_server: 3 calls, 2 retried/failed, 9,700ms ($0.0820 waste)     |
| * vector_memory: 3 calls, 2 exact duplicates, 620ms ($0.0340 waste)     |
+-------------------------------------------------------------------------+
```

---

## 5. Before vs. After Optimization

| Metric | Before Optimization | After `airun` Fix | Delta |
| :--- | :---: | :---: | :---: |
| **Turnaround Latency** | 22.4s | **4.8s** | **-78.6%** |
| **Tokens per Report** | 16,050 tokens | **3,920 tokens** | **-75.6%** |
| **Cost per Report** | $0.214 | **$0.038** | **-82.2%** |
| **Tool Failures Propagated** | 2 / turn | **0 (Circuit-broken)**| **100% Guarded** |
| **Monthly Recoverable Spend**| $6,280 / month | **$0** | **100% Recovered** |

---

## 6. Reproduction Steps

1. Ingest sample agent execution trace:
   ```bash
   airun trace import examples/telemetry/case_studies/case3_agent_loop.json
   ```
2. Run agent efficiency analysis:
   ```bash
   airun agent analyze latest
   ```
3. Test resilience circuit breaker configuration:
   ```bash
   airun breaker status
   ```
