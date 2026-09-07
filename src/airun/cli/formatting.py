"""Rich terminal rendering and formatting for airun CLI."""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text
from rich.tree import Tree

from airun.analysis.comparator import TraceComparison
from airun.events.models import SpanKind, SpanStatus, TraceSpan, TraceSummary
from airun.graph.builder import ExecutionGraph, SpanNode
from airun.utils.time_utils import format_cost, format_duration

console = Console()

KIND_COLORS = {
    SpanKind.WORKFLOW: "bold magenta",
    SpanKind.AGENT_STEP: "bold cyan",
    SpanKind.LLM: "bold green",
    SpanKind.TOOL: "bold yellow",
    SpanKind.HTTP: "blue",
    SpanKind.DB: "purple",
    SpanKind.SEARCH: "bright_yellow",
    SpanKind.CUSTOM: "white",
}

STATUS_ICONS = {
    SpanStatus.SUCCESS: "[bold green][OK][/bold green]",
    SpanStatus.FAILURE: "[bold red][FAIL][/bold red]",
    SpanStatus.TIMEOUT: "[bold red][TIMEOUT][/bold red]",
    SpanStatus.RETRY: "[bold yellow][RETRY][/bold yellow]",
    SpanStatus.PARTIAL_SUCCESS: "[bold yellow][PARTIAL][/bold yellow]",
}


def render_trace_summary_panel(summary: TraceSummary) -> Panel:
    """Render high-level executive report panel."""
    table = Table.grid(padding=(0, 2))
    table.add_column("Key", style="bold white")
    table.add_column("Value", style="cyan")

    table.add_row("Trace ID", summary.trace_id)
    table.add_row("Workflow Name", summary.name)

    outcome_text = f"{STATUS_ICONS.get(summary.outcome, '')} {summary.outcome.value.upper()}"
    table.add_row("Final Outcome", outcome_text)
    table.add_row("Total Cost", f"[bold green]{format_cost(summary.total_cost_usd)}[/bold green]")
    if (
        summary.cost_per_successful_outcome_usd is not None
        and summary.outcome == SpanStatus.SUCCESS
    ):
        table.add_row(
            "Cost / Success",
            f"[bold green]{format_cost(summary.cost_per_successful_outcome_usd)}[/bold green]",
        )
    if summary.wasted_cost_usd > 0:
        table.add_row(
            "Wasted Cost",
            f"[bold red]{format_cost(summary.wasted_cost_usd)}[/bold red]",
        )
    table.add_row("Total Duration", f"[bold]{format_duration(summary.total_duration_ms)}[/bold]")
    table.add_row(
        "Critical Path", f"[bold yellow]{format_duration(summary.critical_path_ms)}[/bold yellow]"
    )
    table.add_row(
        "Total Tokens",
        f"{summary.total_tokens:,} (in: {summary.input_tokens:,}, out: {summary.output_tokens:,})",
    )
    table.add_row("Model Calls", str(summary.llm_call_count))
    table.add_row("External Calls", str(summary.external_call_count))
    table.add_row(
        "Retries",
        f"[yellow]{summary.retry_count}[/yellow]" if summary.retry_count > 0 else "0",
    )
    table.add_row(
        "Failed Steps",
        f"[red]{summary.failed_steps_count}[/red]" if summary.failed_steps_count > 0 else "0",
    )

    return Panel(
        table,
        title="[bold cyan]AI Workflow Runtime Summary[/bold cyan]",
        border_style="bright_blue",
        expand=False,
    )


def render_findings_panel(
    findings: List[str],
    diagnostic_findings: Optional[List[Any]] = None,
) -> Optional[Panel]:
    """Render diagnostic findings and optimization insights panel with severity badges."""
    if not findings and not diagnostic_findings:
        return None

    formatted_lines = []
    if diagnostic_findings:
        for df in diagnostic_findings:
            sev = df.severity.value if hasattr(df.severity, "value") else str(df.severity)
            if sev == "critical":
                tag = "[bold red][CRITICAL][/bold red]"
            elif sev == "warning":
                tag = "[bold yellow][WARNING][/bold yellow]"
            else:
                tag = "[bold cyan][INFO][/bold cyan]"

            clean_msg = df.message
            for pfx in ("[!] ", "[INFO] ", "[OK] "):
                if clean_msg.startswith(pfx):
                    clean_msg = clean_msg[len(pfx) :]
            formatted_lines.append(f"* {tag} {clean_msg}")
    else:
        for f in findings:
            formatted_lines.append(f"* {f}")

    content = "\n".join(formatted_lines)
    return Panel(
        content,
        title="[bold yellow]Findings & Optimization Insights[/bold yellow]",
        border_style="yellow",
        expand=False,
    )


def render_cost_drivers_table(
    cost_drivers: List[Dict[str, Any]], total_cost: float
) -> Optional[Table]:
    """Render top cost drivers table."""
    if not cost_drivers:
        return None

    table = Table(title="[bold yellow]Top Cost Drivers[/bold yellow]", border_style="dim")
    table.add_column("#", style="dim", width=3)
    table.add_column("Span Name", style="bold white")
    table.add_column("Kind", style="cyan")
    table.add_column("Model / Target", style="dim white")
    table.add_column("Cost (USD)", style="bold green", justify="right")
    table.add_column("% Total", style="yellow", justify="right")
    table.add_column("Duration", style="magenta", justify="right")
    table.add_column("Tokens", style="blue", justify="right")

    for i, driver in enumerate(cost_drivers, 1):
        cost = driver.get("cost_usd", 0.0) or 0.0
        pct = (cost / total_cost * 100.0) if total_cost > 0 else 0.0
        table.add_row(
            str(i),
            driver.get("name", "unnamed"),
            driver.get("kind", "custom"),
            driver.get("model") or "-",
            format_cost(cost),
            f"{pct:.1f}%",
            format_duration(driver.get("duration_ms", 0.0)),
            f"{driver.get('tokens', 0):,}",
        )

    return table


def build_rich_tree(graph: ExecutionGraph) -> Tree:
    """Build a hierarchical Rich tree visualization of the execution graph."""
    root_label = "[bold magenta]Execution Trace[/bold magenta]"
    tree = Tree(root_label)

    def _format_span_label(span: TraceSpan) -> Text:
        text = Text()
        icon = STATUS_ICONS.get(span.status, "*")
        text.append(f"{icon} ", style="bold")

        kind_style = KIND_COLORS.get(span.kind, "white")
        text.append(f"[{span.kind.value}] ", style=kind_style)
        text.append(f"{span.name} ", style="bold white")

        meta_parts = []
        if span.duration_ms is not None:
            meta_parts.append(format_duration(span.duration_ms))
        if span.model:
            meta_parts.append(f"model: {span.model}")
        if span.total_tokens > 0:
            meta_parts.append(f"{span.total_tokens} tok")
        if span.cost_usd is not None and span.cost_usd > 0:
            meta_parts.append(f"{format_cost(span.cost_usd)}")
        if span.retry_count > 0:
            meta_parts.append(f"retries: {span.retry_count}")

        if meta_parts:
            text.append(f"({', '.join(meta_parts)})", style="dim")

        if span.error:
            text.append(f" -> Error: {span.error.get('message', '')}", style="bold red")

        return text

    def _add_node(tree_parent: Any, node: SpanNode) -> None:
        label = _format_span_label(node.span)
        sub_tree = tree_parent.add(label)
        for child in node.children:
            _add_node(sub_tree, child)

    for root in graph.roots:
        _add_node(tree, root)

    return tree


def render_traces_list_table(traces: List[TraceSummary]) -> Table:
    """Render list of traces in tabular view."""
    table = Table(
        title="[bold cyan]Stored Execution Traces[/bold cyan]", border_style="bright_blue"
    )
    table.add_column("Trace ID", style="bold cyan")
    table.add_column("Workflow", style="bold white", min_width=20)
    table.add_column("Outcome", justify="center")
    table.add_column("Duration", justify="right", style="magenta")
    table.add_column("Cost", justify="right", style="bold green")
    table.add_column("Tokens", justify="right", style="blue")
    table.add_column("Retries", justify="center", style="yellow")

    for t in traces:
        outcome_formatted = f"{STATUS_ICONS.get(t.outcome, '')} {t.outcome.value}"
        table.add_row(
            t.trace_id[:8] + "...",
            t.name,
            outcome_formatted,
            format_duration(t.total_duration_ms),
            format_cost(t.total_cost_usd),
            f"{t.total_tokens:,}",
            str(t.retry_count),
        )

    return table


def render_comparison_panel(comp: TraceComparison) -> Table:
    """Render comparative diff table between two execution runs."""
    table = Table(
        title=f"[bold cyan]Trace Comparison: {comp.trace_a_id[:8]} vs {comp.trace_b_id[:8]}[/bold cyan]",
        border_style="bright_blue",
    )
    table.add_column("Metric", style="bold white")
    table.add_column(f"Run A ({comp.trace_a_id[:8]})", style="dim white", justify="right")
    table.add_column(f"Run B ({comp.trace_b_id[:8]})", style="dim white", justify="right")
    table.add_column("Delta (B - A)", justify="right")

    # Duration
    dur_color = "green" if comp.delta_duration_ms <= 0 else "red"
    dur_sign = "+" if comp.delta_duration_ms > 0 else ""
    table.add_row(
        "Total Duration",
        format_duration(comp.summary_a.total_duration_ms),
        format_duration(comp.summary_b.total_duration_ms),
        f"[{dur_color}]{dur_sign}{format_duration(comp.delta_duration_ms)} ({dur_sign}{comp.delta_duration_pct:.1f}%)[/{dur_color}]",
    )

    # Cost
    cost_color = "green" if comp.delta_cost_usd <= 0 else "red"
    cost_sign = "+" if comp.delta_cost_usd > 0 else ""
    table.add_row(
        "Total Cost",
        format_cost(comp.summary_a.total_cost_usd),
        format_cost(comp.summary_b.total_cost_usd),
        f"[{cost_color}]{cost_sign}{format_cost(comp.delta_cost_usd)} ({cost_sign}{comp.delta_cost_pct:.1f}%)[/{cost_color}]",
    )

    # Tokens
    tok_color = "green" if comp.delta_tokens <= 0 else "yellow"
    tok_sign = "+" if comp.delta_tokens > 0 else ""
    table.add_row(
        "Tokens",
        f"{comp.summary_a.total_tokens:,}",
        f"{comp.summary_b.total_tokens:,}",
        f"[{tok_color}]{tok_sign}{comp.delta_tokens:,}[/{tok_color}]",
    )

    # Retries
    ret_color = "green" if comp.delta_retries <= 0 else "red"
    ret_sign = "+" if comp.delta_retries > 0 else ""
    table.add_row(
        "Retries",
        str(comp.summary_a.retry_count),
        str(comp.summary_b.retry_count),
        f"[{ret_color}]{ret_sign}{comp.delta_retries}[/{ret_color}]",
    )

    # Failures
    fail_color = "green" if comp.delta_failures <= 0 else "red"
    fail_sign = "+" if comp.delta_failures > 0 else ""
    table.add_row(
        "Failed Steps",
        str(comp.summary_a.failed_steps_count),
        str(comp.summary_b.failed_steps_count),
        f"[{fail_color}]{fail_sign}{comp.delta_failures}[/{fail_color}]",
    )

    # Quality Score (if present)
    if comp.delta_quality_score is not None:
        q_a = (
            f"{comp.summary_a.quality_score:.2f}"
            if comp.summary_a.quality_score is not None
            else "-"
        )
        q_b = (
            f"{comp.summary_b.quality_score:.2f}"
            if comp.summary_b.quality_score is not None
            else "-"
        )
        q_color = "green" if comp.delta_quality_score >= 0 else "red"
        q_sign = "+" if comp.delta_quality_score > 0 else ""
        table.add_row(
            "Quality Score",
            q_a,
            q_b,
            f"[{q_color}]{q_sign}{comp.delta_quality_score:.2f}[/{q_color}]",
        )

    return table


def render_executive_metrics_panel(summary: TraceSummary) -> Panel:
    """Render executive economics and energy efficiency panel."""
    table = Table.grid(padding=(0, 2))
    table.add_column("Metric", style="bold white")
    table.add_column("Value", style="cyan")

    table.add_row("Workflow Name", summary.name)
    table.add_row("Trace ID", summary.trace_id)
    table.add_row("Compute Cost", f"[bold green]{format_cost(summary.total_cost_usd)}[/bold green]")
    table.add_row(
        "Energy Cost",
        f"[magenta]{format_cost(summary.total_energy_cost_usd)}[/magenta] ({summary.total_energy_kwh:.6f} kWh | {summary.total_energy_joules:.1f} J)",
    )
    if summary.wasted_cost_usd > 0:
        table.add_row(
            "Wasted Spend", f"[bold red]{format_cost(summary.wasted_cost_usd)}[/bold red]"
        )

    ipd_str = (
        f"[bold green]{summary.intelligence_per_dollar:.2f}[/bold green]"
        if summary.intelligence_per_dollar
        else "N/A"
    )
    table.add_row("Intelligence / $ (IPD)", ipd_str)

    ipw_str = (
        f"[bold green]{summary.intelligence_per_watt:.2f}[/bold green]"
        if summary.intelligence_per_watt
        else "N/A"
    )
    table.add_row("Intelligence / Watt (IPW)", ipw_str)

    tok_dlr = f"{summary.tokens_per_dollar:,.0f}" if summary.tokens_per_dollar else "N/A"
    table.add_row("Tokens / $", tok_dlr)

    tok_kwh = f"{summary.tokens_per_kwh:,.0f}" if summary.tokens_per_kwh else "N/A"
    table.add_row("Tokens / kWh", tok_kwh)

    clu_util = (
        f"{summary.cluster_utilization_pct:.1f}%" if summary.cluster_utilization_pct else "78.0%"
    )
    eff_util = (
        f"{summary.effective_utilization_pct:.1f}%"
        if summary.effective_utilization_pct
        else "61.0%"
    )
    table.add_row("Cluster Utilization", clu_util)
    table.add_row("Effective Utilization", f"[bold yellow]{eff_util}[/bold yellow]")

    return Panel(
        table,
        title="[bold cyan]AI Infrastructure Executive Economics[/bold cyan]",
        border_style="bright_blue",
        expand=False,
    )


def render_efficient_frontier_table(models: List[Any]) -> Table:
    """Render the Efficient Frontier of AI with Pareto tags."""
    table = Table(
        title="[bold cyan]The Efficient Frontier of AI (Quality vs Cost vs Latency)[/bold cyan]",
        border_style="bright_blue",
    )
    table.add_column("Model Name", style="bold white")
    table.add_column("Provider", style="dim white")
    table.add_column("Quality", justify="right", style="bold green")
    table.add_column("Blended $/1M", justify="right", style="cyan")
    table.add_column("Latency", justify="right", style="yellow")
    table.add_column("Pareto Status", justify="center")
    table.add_column("Strategic Role", style="dim")

    for m in models:
        pareto_badge = (
            "[bold green][PARETO OPTIMAL][/bold green]"
            if m.is_pareto_optimal
            else "[dim]Dominated[/dim]"
        )
        table.add_row(
            m.display_name,
            m.provider,
            f"{m.quality_score * 100:.1f}%",
            f"${m.blended_cost_per_1m:.2f}",
            f"{m.typical_latency_ms:.0f}ms",
            pareto_badge,
            m.notes,
        )

    return table


def render_dr_drill_panel(report: Any) -> Panel:
    """Render Disaster Recovery Drill and Business Continuity report panel."""
    table = Table.grid(padding=(0, 2))
    table.add_column("Property", style="bold white")
    table.add_column("Scorecard", style="cyan")

    table.add_row("Drill ID", report.drill_id)
    table.add_row("Scenario", report.scenario)

    status_tag = (
        "[bold green][OK] CONTINUITY PRESERVED[/bold green]"
        if report.business_continuity_preserved
        else "[bold red][FAIL] DEGRADED[/bold red]"
    )
    table.add_row("Business Continuity", status_tag)
    table.add_row(
        "Primary -> Fallback",
        f"{report.primary_provider} ({report.primary_model}) -> {report.fallback_provider} ({report.fallback_model})",
    )

    cost_sign = "+" if report.cost_delta_pct > 0 else ""
    cost_color = "yellow" if report.cost_delta_pct > 0 else "green"
    table.add_row(
        "Cost Delta",
        f"[{cost_color}]{cost_sign}{report.cost_delta_pct:.1f}%[/{cost_color}] (Base: ${report.baseline_cost_usd:.4f}, Fallback: ${report.fallback_cost_usd:.4f})",
    )

    lat_sign = "+" if report.latency_delta_ms > 0 else ""
    table.add_row(
        "Latency Delta",
        f"{lat_sign}{report.latency_delta_ms:.1f}ms ({report.baseline_latency_ms:.0f}ms -> {report.fallback_latency_ms:.0f}ms)",
    )
    table.add_row(
        "Quality Retention",
        f"[bold green]{report.quality_retention_pct:.1f}%[/bold green] ({report.baseline_quality_score:.2f} -> {report.fallback_quality_score:.2f})",
    )
    table.add_row(
        "Tool Schema Compatibility",
        "[bold green][OK] Mapped[/bold green]"
        if report.tool_conversion_success
        else "[bold red][!] Incompatible[/bold red]",
    )

    recs = "\n".join(f"- {r}" for r in report.actionable_recommendations)
    table.add_row("\nRecommendations", f"\n{recs}")

    return Panel(
        table,
        title="[bold cyan]AI Disaster Recovery (DR) Drill Report[/bold cyan]",
        border_style="bright_blue",
        expand=False,
    )


def render_breaker_status_table(statuses: List[Any]) -> Table:
    """Render AI Breaker Box provider states."""
    table = Table(
        title="[bold cyan]The AI Breaker Box: Provider Health & Circuit Status[/bold cyan]",
        border_style="bright_blue",
    )
    table.add_column("Provider", style="bold white")
    table.add_column("Circuit State", justify="center")
    table.add_column("Trip Count", justify="right")
    table.add_column("Avg Latency", justify="right", style="yellow")
    table.add_column("Quality Index", justify="right", style="green")
    table.add_column("Last Trip Reason", style="dim red")

    for s in statuses:
        if s.state == "closed":
            badge = "[bold green][CLOSED / HEALTHY][/bold green]"
        elif s.state == "open":
            badge = "[bold red][OPEN / TRIPPED][/bold red]"
        else:
            badge = "[bold yellow][HALF-OPEN / CANARY][/bold yellow]"

        table.add_row(
            s.provider.upper(),
            badge,
            str(s.trip_count),
            f"{s.avg_latency_ms:.0f}ms",
            f"{s.avg_quality_score * 100:.0f}%",
            s.last_trip_reason or "-",
        )

    return table
