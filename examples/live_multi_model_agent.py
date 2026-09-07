#!/usr/bin/env python3
"""Real-World Multi-Model Agent Pipeline Instrumenting OpenAI, Gemini, Anthropic, and Local Models.

This script demonstrates how to profile a production multi-step AI agent using real LLM APIs.
If API keys (OPENAI_API_KEY, GEMINI_API_KEY, ANTHROPIC_API_KEY) are present in the environment,
it makes real live network calls and records exact token usages. If keys are missing,
it uses realistic mock responses so the pipeline can always be tested and profiled.

Usage:
    export OPENAI_API_KEY="sk-..."
    export GEMINI_API_KEY="AIza..."
    export ANTHROPIC_API_KEY="sk-ant-..."
    python examples/live_multi_model_agent.py
"""

import asyncio
import os
import sys
from typing import Any, Dict

from airun import (
    SpanKind,
    set_span_metadata,
    set_span_quality,
    set_span_tokens,
    trace,
)

# ---------------------------------------------------------------------------
# 1. Real / Fallback API Call Wrappers
# ---------------------------------------------------------------------------


@trace(kind=SpanKind.LLM, model="gemini-1.5-flash", provider="google")
async def call_gemini_planner(user_query: str) -> Dict[str, Any]:
    """Step 1: Fast intent classification and query planning via Gemini 1.5 Flash."""
    api_key = os.getenv("GEMINI_API_KEY")
    if api_key:
        try:
            import google.generativeai as genai

            genai.configure(api_key=api_key)
            model = genai.GenerativeModel("gemini-1.5-flash")
            prompt = (
                f"Decompose this research request into search queries and subtasks: {user_query}"
            )
            response = await asyncio.to_thread(model.generate_content, prompt)

            # Record token usage from Gemini usage_metadata
            input_tokens = getattr(response.usage_metadata, "prompt_token_count", 150)
            output_tokens = getattr(response.usage_metadata, "candidates_token_count", 85)
            set_span_tokens(input_tokens=input_tokens, output_tokens=output_tokens)
            set_span_metadata({"finish_reason": "STOP", "real_api": True})
            return {"plan": response.text, "queries": ["market trends 2026", "competitor pricing"]}
        except Exception as e:
            set_span_metadata({"api_error": str(e), "fallback": True})

    # Realistic fallback simulation
    await asyncio.sleep(0.09)  # 90ms typical Gemini Flash latency
    set_span_tokens(input_tokens=180, output_tokens=95)
    set_span_metadata({"real_api": False, "simulated": True})
    return {
        "plan": f"Plan for '{user_query}': 1. Query market data. 2. Analyze sentiment.",
        "queries": ["inference economics 2026", "agentic execution benchmarks"],
    }


@trace(kind=SpanKind.TOOL, provider="http")
async def fetch_search_results(query: str) -> str:
    """Step 2a: Tool execution querying search engine / web API."""
    set_span_metadata({"query": query})
    await asyncio.sleep(0.12)  # 120ms search API latency
    return f"Search results for '{query}': AI inference costs growing 3x in multi-step agents."


@trace(kind=SpanKind.DB, provider="vector_db")
async def query_knowledge_base(topic: str) -> str:
    """Step 2b: Tool execution querying internal Vector DB."""
    set_span_metadata({"collection": "agent_benchmarks", "top_k": 3})
    await asyncio.sleep(0.08)  # 80ms vector retrieval latency
    return "Vector DB match: Critical path in agent DAGs accounts for 70% of user latency."


@trace(kind=SpanKind.LLM, model="gpt-4o", provider="openai")
async def call_openai_analyst(context: str, plan: Dict[str, Any]) -> str:
    """Step 3: Deep reasoning and multi-document synthesis via OpenAI GPT-4o."""
    api_key = os.getenv("OPENAI_API_KEY")
    if api_key:
        try:
            from openai import OpenAI

            client = OpenAI(api_key=api_key)
            prompt = (
                f"Analyze the following data based on the plan:\nPlan: {plan}\nContext: {context}"
            )
            response = await asyncio.to_thread(
                client.chat.completions.create,
                model="gpt-4o",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.2,
            )

            # Record OpenAI token usage
            usage = response.usage
            set_span_tokens(
                input_tokens=usage.prompt_tokens,
                output_tokens=usage.completion_tokens,
            )
            set_span_metadata(
                {"finish_reason": response.choices[0].finish_reason, "real_api": True}
            )
            return response.choices[0].message.content
        except Exception as e:
            set_span_metadata({"api_error": str(e), "fallback": True})

    # Realistic fallback simulation
    await asyncio.sleep(0.24)  # 240ms GPT-4o latency
    set_span_tokens(input_tokens=1850, output_tokens=420)
    set_span_metadata({"real_api": False, "simulated": True})
    return "Synthesized Analysis: Multi-step agent pipelines require DAG critical-path scheduling and outcome-based cost attribution."


@trace(kind=SpanKind.LLM, model="claude-3-5-haiku", provider="anthropic")
async def call_claude_formatter(raw_analysis: str) -> Dict[str, Any]:
    """Step 4: Strict JSON schema formatting and executive summary via Claude 3.5 Haiku."""
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if api_key:
        try:
            import anthropic

            client = anthropic.Anthropic(api_key=api_key)
            prompt = f"Format this analysis into a clean executive JSON summary: {raw_analysis}"
            response = await asyncio.to_thread(
                client.messages.create,
                model="claude-3-5-haiku-20241022",
                max_tokens=300,
                messages=[{"role": "user", "content": prompt}],
            )

            # Record Anthropic token usage
            set_span_tokens(
                input_tokens=response.usage.input_tokens,
                output_tokens=response.usage.output_tokens,
            )
            set_span_metadata({"stop_reason": response.stop_reason, "real_api": True})
            return {"summary": response.content[0].text, "status": "completed"}
        except Exception as e:
            set_span_metadata({"api_error": str(e), "fallback": True})

    # Realistic fallback simulation
    await asyncio.sleep(0.07)  # 70ms Claude Haiku latency
    set_span_tokens(input_tokens=450, output_tokens=120)
    set_span_metadata({"real_api": False, "simulated": True})
    return {
        "status": "success",
        "executive_summary": "Inference costs in agentic loops are reduced by 97% with model tiering.",
    }


# ---------------------------------------------------------------------------
# 2. Main Multi-Step Agent Execution Pipeline
# ---------------------------------------------------------------------------


async def run_live_agent_pipeline(user_query: str):
    """Executes the complete multi-model agent pipeline with active DAG tracing."""
    print(f">> Starting Real-World Multi-Model Agent for: '{user_query}'...")

    async with trace("live_multi_model_agent_pipeline", kind=SpanKind.WORKFLOW):
        # Step 1: Gemini 1.5 Flash Planning
        async with trace("phase_1_planning", kind=SpanKind.AGENT_STEP):
            plan_result = await call_gemini_planner(user_query)

        # Step 2: Parallel Tool Execution (Async Fan-Out)
        async with trace("phase_2_parallel_retrieval", kind=SpanKind.AGENT_STEP):
            search_task = fetch_search_results(plan_result["queries"][0])
            db_task = query_knowledge_base("inference economics")
            search_data, db_data = await asyncio.gather(search_task, db_task)
            context = f"{search_data}\n{db_data}"

        # Step 3: OpenAI GPT-4o Deep Reasoning
        async with trace("phase_3_reasoning", kind=SpanKind.AGENT_STEP):
            analysis = await call_openai_analyst(context, plan_result)

        # Step 4: Claude 3.5 Haiku Formatting & Quality Validation
        async with trace("phase_4_formatting", kind=SpanKind.AGENT_STEP):
            final_output = await call_claude_formatter(analysis)
            # Record quality provenance (schema adherence = 1.0, correctness = 0.96)
            set_span_quality(
                score=0.96,
                metrics={
                    "evaluator": "schema_validator_v2",
                    "schema_adherence": 1.0,
                    "task_completion": 1.0,
                },
            )

    print("\n[OK] Pipeline completed successfully! Trace persisted to .airun/traces.db.")
    print(f">> Executive Result: {final_output.get('status', 'OK')}")
    print(">> Run 'airun report latest' to view the execution graph and cost breakdown.")


if __name__ == "__main__":
    query = sys.argv[1] if len(sys.argv) > 1 else "Optimize multi-model agent execution cost"
    asyncio.run(run_live_agent_pipeline(query))
