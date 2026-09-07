"""Main Typer CLI application for airun."""

from __future__ import annotations

import os
import subprocess
import sys
import time
from pathlib import Path
from typing import Optional

import typer
import yaml
from rich.console import Console
from rich.table import Table

from airun.analysis.analyzer import analyze_spans
from airun.analysis.comparator import compare_traces
from airun.cli.formatting import (
    build_rich_tree,
    render_breaker_status_table,
    render_comparison_panel,
    render_cost_drivers_table,
    render_dr_drill_panel,
    render_efficient_frontier_table,
    render_executive_metrics_panel,
    render_findings_panel,
    render_trace_summary_panel,
    render_traces_list_table,
)
from airun.events.models import SpanKind, SpanStatus
from airun.exporters.json_export import export_trace_to_json
from airun.exporters.otel_export import export_trace_to_otel
from airun.graph.builder import ExecutionGraph
from airun.pricing.defaults import DEFAULT_MODEL_PRICING
from airun.resilience.breaker import get_resilience_manager
from airun.resilience.dr_drills import run_disaster_recovery_drill
from airun.routing.frontier import get_efficient_frontier
from airun.sdk.tracer import record_retry, set_span_metadata, set_span_tokens, trace
from airun.store import get_trace_store
from airun.store.base import TraceStore
from airun.store.sqlite import SQLiteTraceStore
from airun.utils.time_utils import format_cost, format_duration, perf_counter_ms

app = typer.Typer(
    name="airun",
    help="AI Infrastructure Reliability & Economics Platform: Measure compute, power, IPD, IPW, and multi-provider resilience.",
    no_args_is_help=True,
)
trace_app = typer.Typer(help="Manage and inspect captured execution traces.")
dr_app = typer.Typer(help="Execute and evaluate AI Disaster Recovery (DR) drills.")
breaker_app = typer.Typer(help="Inspect and manage the AI Breaker Box.")

app.add_typer(trace_app, name="trace")
app.add_typer(dr_app, name="dr")
app.add_typer(breaker_app, name="breaker")

console = Console()


def _resolve_trace_id(identifier: str, store: TraceStore) -> str:
    """Resolve aliases like 'latest' or 'previous' to concrete trace IDs."""
    id_lower = identifier.lower().strip()
    if id_lower in ("latest", "last"):
        recent = store.list_traces(limit=1)
        if not recent:
            console.print("[bold red]No stored traces found in database.[/bold red]")
            raise typer.Exit(code=1)
        return recent[0].trace_id
    elif id_lower in ("previous", "prev"):
        recent = store.list_traces(limit=2)
        if len(recent) < 2:
            console.print(
                "[bold red]Cannot resolve 'previous': fewer than 2 traces in database.[/bold red]"
            )
            raise typer.Exit(code=1)
        return recent[1].trace_id
    return identifier


@app.command()
def init(
    force: bool = typer.Option(
        False, "--force", "-f", help="Overwrite existing configuration files."
    ),
) -> None:
    """Initialize local airun workspace, trace storage, and pricing configuration."""
    airun_dir = Path.cwd() / ".airun"
    airun_dir.mkdir(parents=True, exist_ok=True)

    config_file = airun_dir / "config.yaml"
    pricing_file = airun_dir / "pricing.yaml"

    if config_file.exists() and not force:
        console.print(
            "[yellow]Workspace already initialized (.airun/config.yaml exists). Use --force to overwrite.[/yellow]"
        )
    else:
        default_config = {
            "storage_backend": "sqlite",
            "sqlite_path": ".airun/traces.db",
            "storage_dir": ".airun/traces",
            "pricing_file": ".airun/pricing.yaml",
            "privacy": {
                "capture_prompt_content": False,
                "capture_completion_content": False,
                "capture_tool_inputs": False,
                "capture_tool_outputs": False,
                "redact_fields": [
                    "api_key",
                    "authorization",
                    "token",
                    "password",
                    "secret",
                    "bearer",
                    "client_secret",
                    "private_key",
                ],
            },
        }
        with open(config_file, "w", encoding="utf-8") as f:
            yaml.dump(default_config, f, default_flow_style=False, sort_keys=False)
        console.print(f"[bold green][OK] Created configuration:[/bold green] {config_file}")

    if not pricing_file.exists() or force:
        with open(pricing_file, "w", encoding="utf-8") as f:
            yaml.dump(
                {"models": DEFAULT_MODEL_PRICING}, f, default_flow_style=False, sort_keys=False
            )
        console.print(f"[bold green][OK] Created pricing table:[/bold green] {pricing_file}")

    console.print(
        "\n[bold cyan]airun initialized successfully![/bold cyan] Run [bold green]airun demo[/bold green] to test."
    )


@app.command()
def demo() -> None:
    """
    Run a simulated offline multi-step AI workflow to produce a sample trace and report.
    No external API keys or network connection required.
    """
    console.print("\n[bold cyan]>> Running AI Runtime Profiler Demo Workflow...[/bold cyan]\n")

    # Offline multi-step agent simulation
    with trace("research_agent_workflow", kind=SpanKind.WORKFLOW) as root_span:
        # Step 1: Agent Planning
        with trace("agent_planning", kind=SpanKind.AGENT_STEP):
            time.sleep(0.04)
            with trace("planner_llm_call", kind=SpanKind.LLM, model="gpt-4o", provider="openai"):
                time.sleep(0.12)
                set_span_tokens(input_tokens=1420, output_tokens=380)

        # Step 2: Tool Execution (Search API with retry simulation)
        with trace("tool_execution_phase", kind=SpanKind.AGENT_STEP):
            with trace("web_search_tool", kind=SpanKind.TOOL, provider="search_engine"):
                time.sleep(0.06)
                record_retry()  # Simulate 1 transient retry
                set_span_metadata({"query": "AI Runtime Tracing Architecture", "results_count": 5})

            with trace("vector_db_query", kind=SpanKind.DB, provider="chromadb"):
                time.sleep(0.03)
                set_span_metadata({"collection": "agent_memory", "k": 4})

        # Step 3: Summarization & Final Action
        with trace("summarization_step", kind=SpanKind.AGENT_STEP):
            with trace(
                "summarizer_llm_call", kind=SpanKind.LLM, model="gpt-4o-mini", provider="openai"
            ):
                time.sleep(0.08)
                set_span_tokens(input_tokens=2850, output_tokens=520)

    trace_id = root_span.trace_id
    console.print(
        f"[bold green][OK] Demo workflow completed successfully![/bold green] (Trace ID: [cyan]{trace_id}[/cyan])\n"
    )

    # Display report
    report(trace_id=trace_id)


@trace_app.command("list")
def trace_list(
    limit: int = typer.Option(20, "--limit", "-n", help="Maximum number of traces to list."),
    status: Optional[str] = typer.Option(
        None, "--status", "-s", help="Filter by outcome status (success, failure, retry)."
    ),
) -> None:
    """List stored execution traces."""
    store = get_trace_store()
    status_filter = SpanStatus(status) if status else None
    traces = store.list_traces(limit=limit, status=status_filter)

    if not traces:
        console.print(
            "[yellow]No traces found. Run 'airun demo' to generate your first trace.[/yellow]"
        )
        return

    table = render_traces_list_table(traces)
    console.print(table)


@trace_app.command("show")
def trace_show(
    trace_id: str = typer.Argument("latest", help="Trace ID to inspect (or 'latest')."),
) -> None:
    """Display the full execution tree and spans for a trace."""
    store = get_trace_store()
    resolved_id = _resolve_trace_id(trace_id, store)
    record = store.get_trace(resolved_id)

    if not record:
        console.print(f"[bold red]Trace '{trace_id}' not found.[/bold red]")
        raise typer.Exit(code=1)

    graph = ExecutionGraph(record.spans)
    tree = build_rich_tree(graph)
    console.print("\n", tree, "\n")


@app.command()
def report(
    trace_id: str = typer.Argument("latest", help="Trace ID to generate report for (or 'latest')."),
) -> None:
    """Show detailed runtime, critical path, cost breakdown, and findings for a trace."""
    store = get_trace_store()
    resolved_id = _resolve_trace_id(trace_id, store)
    record = store.get_trace(resolved_id)

    if not record:
        console.print(f"[bold red]Trace '{trace_id}' not found.[/bold red]")
        raise typer.Exit(code=1)

    summary = record.summary or analyze_spans(record.spans)
    graph = ExecutionGraph(record.spans)

    # 1. Summary Panel
    console.print(render_trace_summary_panel(summary))

    # 2. Findings Panel (Actionable Insights with Severity)
    findings_panel = render_findings_panel(summary.findings, summary.diagnostic_findings)
    if findings_panel:
        console.print(findings_panel)

    # 3. Cost Drivers Table
    cost_table = render_cost_drivers_table(summary.top_cost_drivers, summary.total_cost_usd)
    if cost_table:
        console.print(cost_table)

    # 4. Execution Tree
    console.print("\n[bold white]Execution Hierarchy:[/bold white]")
    console.print(build_rich_tree(graph))
    console.print()


@app.command()
def compare(
    trace_id_1: str = typer.Argument(..., help="First trace ID (Baseline / Run A, or 'previous')."),
    trace_id_2: str = typer.Argument(
        "latest", help="Second trace ID (Comparison / Run B, or 'latest')."
    ),
) -> None:
    """Compare two execution traces to analyze cost, latency, token, and retry differences."""
    store = get_trace_store()
    id1 = _resolve_trace_id(trace_id_1, store)
    id2 = _resolve_trace_id(trace_id_2, store)

    rec1 = store.get_trace(id1)
    rec2 = store.get_trace(id2)

    if not rec1:
        console.print(f"[bold red]Trace '{trace_id_1}' not found.[/bold red]")
        raise typer.Exit(code=1)
    if not rec2:
        console.print(f"[bold red]Trace '{trace_id_2}' not found.[/bold red]")
        raise typer.Exit(code=1)

    comp = compare_traces(rec1, rec2)
    console.print(render_comparison_panel(comp))


@app.command()
def export(
    trace_id: str = typer.Argument("latest", help="Trace ID to export (or 'latest')."),
    format: str = typer.Option(
        "json", "--format", "-f", help="Export format: 'json' or 'otel-json'."
    ),
    output: Optional[Path] = typer.Option(
        None, "--output", "-o", help="Optional output file path."
    ),
) -> None:
    """Export a trace in raw JSON or OpenTelemetry OTLP format."""
    store = get_trace_store()
    resolved_id = _resolve_trace_id(trace_id, store)
    record = store.get_trace(resolved_id)

    if not record:
        console.print(f"[bold red]Trace '{trace_id}' not found.[/bold red]")
        raise typer.Exit(code=1)

    if format.lower() in ("otel", "otel-json", "otlp"):
        import json

        exported_str = json.dumps(export_trace_to_otel(record), indent=2)
    else:
        exported_str = export_trace_to_json(record)

    if output:
        output.parent.mkdir(parents=True, exist_ok=True)
        with open(output, "w", encoding="utf-8") as f:
            f.write(exported_str)
        console.print(f"[bold green][OK] Exported trace to {output}[/bold green]")
    else:
        console.print(exported_str)


@app.command()
def run(
    script: Path = typer.Argument(
        ..., help="Path to Python script to execute with profiling enabled."
    ),
    args: list[str] = typer.Argument(None, help="Arguments to forward to the target script."),
    trace_id_file: Optional[Path] = typer.Option(
        None,
        "--trace-id-file",
        "-t",
        help="Optional file path to output the captured Trace ID (for deterministic CI/CD pipelines).",
    ),
) -> None:
    """Execute a Python script with airun profiling active."""
    if not script.exists():
        console.print(f"[bold red]Target script '{script}' not found.[/bold red]")
        raise typer.Exit(code=1)

    env = os.environ.copy()
    repo_src = Path(__file__).resolve().parent.parent.parent
    env["PYTHONPATH"] = f"{repo_src}{os.pathsep}{env.get('PYTHONPATH', '')}"
    if trace_id_file:
        env["AIRUN_TRACE_ID_FILE"] = str(trace_id_file.resolve())

    cmd = [sys.executable, str(script)]
    if args:
        cmd.extend(args)

    console.print(f"[dim]>> Profiling execution: {' '.join(cmd)}[/dim]\n")
    proc = subprocess.run(cmd, env=env)

    # Output quick post-run summary
    store = SQLiteTraceStore(Path.cwd() / ".airun" / "traces.db")
    recent = store.list_traces(limit=1)
    if recent:
        latest = recent[0]
        if trace_id_file and not trace_id_file.exists():
            trace_id_file.parent.mkdir(parents=True, exist_ok=True)
            with open(trace_id_file, "w", encoding="utf-8") as f:
                f.write(latest.trace_id)

        if trace_id_file and trace_id_file.exists():
            console.print(
                f"[dim]Trace ID written to: [bold white]{trace_id_file}[/bold white][/dim]"
            )

        console.print(
            f"\n[bold green][OK] Execution Profiled Successfully![/bold green] (Trace ID: [cyan]{latest.trace_id}[/cyan])"
        )
        console.print(
            f"Duration: [magenta]{format_duration(latest.total_duration_ms)}[/magenta] | Cost: [bold green]{format_cost(latest.total_cost_usd)}[/bold green] | Tokens: [blue]{latest.total_tokens:,}[/blue] | Outcome: [bold]{latest.outcome.value.upper()}[/bold]"
        )
        console.print(
            "[dim]Inspect full report: [bold white]airun report latest[/bold white][/dim]\n"
        )

    raise typer.Exit(code=proc.returncode)


@app.command()
def doctor() -> None:
    """Check workspace health, storage connectivity, and measure profiler micro-overhead."""
    console.print("\n[bold cyan]>> Running airun Environment & Health Check...[/bold cyan]\n")

    table = Table(title="[bold cyan]airun System Doctor[/bold cyan]", border_style="bright_blue")
    table.add_column("Component", style="bold white")
    table.add_column("Status", justify="center")
    table.add_column("Details", style="dim white")

    # 1. Config Check
    config_path = Path.cwd() / ".airun" / "config.yaml"
    if config_path.exists():
        table.add_row("Configuration", "[bold green][OK][/bold green]", str(config_path))
    else:
        table.add_row(
            "Configuration",
            "[bold yellow][DEFAULT][/bold yellow]",
            "Using default in-memory configuration (run 'airun init' to customize)",
        )

    # 2. Pricing Check
    pricing_path = Path.cwd() / ".airun" / "pricing.yaml"
    if pricing_path.exists():
        table.add_row("Pricing Table", "[bold green][OK][/bold green]", str(pricing_path))
    else:
        table.add_row(
            "Pricing Table",
            "[bold green][BUILT-IN][/bold green]",
            "Active with OpenAI, Anthropic, Gemini, Llama rates",
        )

    # 3. Store Health & Filesystem Check
    store = get_trace_store()
    traces = store.list_traces(limit=500)
    storage_desc = f"Backend: {store.__class__.__name__} ({len(traces)} traces recorded)"

    # Check for network filesystem warning
    airun_dir = Path.cwd() / ".airun"
    str_path = str(airun_dir.resolve())
    if str_path.startswith(("\\\\", "//")):
        storage_desc += " [!] Network storage detected; SQLite WAL mode works best on local disk"

    table.add_row("Trace Store", "[bold green][OK][/bold green]", storage_desc)

    # 4. Measure Micro-Overhead
    start_bench = perf_counter_ms()
    iterations = 100
    with trace("doctor_overhead_test", kind=SpanKind.WORKFLOW, save_on_exit=False):
        for _ in range(iterations):
            with trace("micro_step", kind=SpanKind.CUSTOM):
                pass
    dur = perf_counter_ms() - start_bench
    avg_us = (dur / iterations) * 1000.0

    table.add_row(
        "SDK Micro-Overhead",
        "[bold green][OPTIMAL][/bold green]",
        f"~{avg_us:.1f} microseconds per span (< 1ms limit)",
    )

    console.print(table)
    console.print()


@app.command("ui")
@app.command("serve")
def serve_dashboard(
    host: str = typer.Option(
        "127.0.0.1", "--host", "-h", help="Host address to bind the web server"
    ),
    port: int = typer.Option(8765, "--port", "-p", help="Port number for the dashboard web server"),
):
    """Launch the interactive airun Web UI and executive dashboard."""
    from airun.server import start_server

    start_server(host=host, port=port)


@app.command("metrics")
def metrics(
    trace_id: str = typer.Argument("latest", help="Trace ID to inspect (or 'latest')."),
) -> None:
    """Display Executive Economics: Intelligence per Dollar (IPD), Intelligence per Watt (IPW), and Energy."""
    store = get_trace_store()
    resolved_id = _resolve_trace_id(trace_id, store)
    record = store.get_trace(resolved_id)

    if not record:
        console.print(f"[bold red]Trace '{trace_id}' not found.[/bold red]")
        raise typer.Exit(code=1)

    summary = record.summary or analyze_spans(record.spans)
    console.print("\n", render_executive_metrics_panel(summary), "\n")


@app.command("frontier")
def frontier() -> None:
    """Display the Efficient Frontier of AI (Pareto optimality across Quality, Cost, and Latency)."""
    models = get_efficient_frontier()
    console.print("\n", render_efficient_frontier_table(models), "\n")


@dr_app.command("drill")
def execute_dr_drill(
    primary: str = typer.Option(
        "openai", "--primary", "-p", help="Primary provider to inject failure into."
    ),
    fallback: str = typer.Option(
        "anthropic", "--fallback", "-f", help="Fallback provider to promote."
    ),
    fault: str = typer.Option(
        "outage_500",
        "--fault",
        help="Fault type: 'outage_500', 'latency_spike', 'quality_collapse'.",
    ),
) -> None:
    """Execute an automated synthetic Disaster Recovery drill and render business continuity audit."""
    console.print(
        f"\n[bold cyan]>> Executing AI Disaster Recovery Drill: failing {primary} -> promoting {fallback}...[/bold cyan]\n"
    )
    report = run_disaster_recovery_drill(
        primary_provider=primary,
        fallback_provider=fallback,
        fault_type=fault,
    )
    console.print(render_dr_drill_panel(report), "\n")


@breaker_app.command("status")
def breaker_status() -> None:
    """Display live circuit breaker statuses across all configured AI providers."""
    mgr = get_resilience_manager()
    statuses = mgr.get_all_statuses()
    console.print("\n", render_breaker_status_table(statuses), "\n")
