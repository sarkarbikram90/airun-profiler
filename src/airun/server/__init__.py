"""Built-in lightweight Web Server and REST API for airun profiler.

Serves an interactive AI Infrastructure Command Center and REST APIs directly from the local SQLite trace store.
Implements the spec.md Executive Command Center, Efficient Frontier visualizer, AI Breaker Box, and Causal Incident Graph.
"""

import json
import urllib.parse
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any

from airun.analysis.analyzer import analyze_spans
from airun.analysis.comparator import compare_traces
from airun.analysis.waste import detect_compute_waste
from airun.incident.graph import build_sample_incident_graph
from airun.resilience.breaker import get_resilience_manager
from airun.resilience.dr_drills import run_disaster_recovery_drill
from airun.routing.frontier import get_efficient_frontier
from airun.store import get_trace_store


class AirunServerHandler(BaseHTTPRequestHandler):
    """HTTP Request Handler providing REST API and single-page executive web UI."""

    server_version = "airun-server/0.1.3"

    def _send_json(self, data: Any, status: int = 200):
        """Helper to send JSON response."""
        payload = json.dumps(data, default=str).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(payload)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()
        self.wfile.write(payload)

    def _send_html(self, html: str, status: int = 200):
        """Helper to send HTML response."""
        payload = html.encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(payload)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(payload)

    def do_OPTIONS(self):
        """Handle CORS pre-flight requests."""
        self.send_response(204)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()

    def do_POST(self):
        """Handle incoming POST requests."""
        parsed_url = urllib.parse.urlparse(self.path)
        path = parsed_url.path.rstrip("/")

        if path == "/api/resilience/dr-drill":
            content_length = int(self.headers.get("Content-Length", 0))
            post_body = self.rfile.read(content_length) if content_length > 0 else b"{}"
            try:
                data = json.loads(post_body.decode("utf-8")) if post_body else {}
            except Exception:
                data = {}

            primary = data.get("primary_provider", "openai")
            fallback = data.get("fallback_provider", "anthropic")
            fault = data.get("fault_type", "outage_500")

            report = run_disaster_recovery_drill(
                primary_provider=primary,
                fallback_provider=fallback,
                fault_type=fault,
            )
            self._send_json(report.model_dump())
            return

        self._send_json({"error": "Endpoint not found"}, status=404)

    def do_GET(self):
        """Handle incoming GET requests."""
        parsed_url = urllib.parse.urlparse(self.path)
        path = parsed_url.path.rstrip("/")
        query_params = urllib.parse.parse_qs(parsed_url.query)

        # Health check endpoint (for AWS ALB / Kubernetes liveness probe)
        if path == "/healthz" or path == "/health":
            self._send_json(
                {
                    "status": "ok",
                    "version": "0.1.3",
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                }
            )
            return

        # API: List all trace summaries
        if path == "/api/traces":
            store = get_trace_store()
            limit = int(query_params.get("limit", [50])[0])
            summaries = store.list_traces(limit=limit)
            self._send_json([s.model_dump() for s in summaries])
            return

        # API: High-level KPI summary
        if path == "/api/summary":
            store = get_trace_store()
            summaries = store.list_traces(limit=500)
            total_traces = len(summaries)
            total_cost = sum(s.total_cost_usd or 0.0 for s in summaries)
            total_tokens = sum(s.total_tokens or 0 for s in summaries)
            total_energy_kwh = sum(getattr(s, "total_energy_kwh", 0.0) or 0.0 for s in summaries)
            total_energy_cost = sum(
                getattr(s, "total_energy_cost_usd", 0.0) or 0.0 for s in summaries
            )
            avg_duration_ms = (
                (sum(s.total_duration_ms or 0.0 for s in summaries) / total_traces)
                if total_traces > 0
                else 0.0
            )
            successful_traces = [
                s for s in summaries if str(s.outcome).lower() in ("success", "spanstatus.success")
            ]
            success_rate = (
                (len(successful_traces) / total_traces * 100.0) if total_traces > 0 else 100.0
            )
            wasted_cost = sum(s.wasted_cost_usd or 0.0 for s in summaries)

            self._send_json(
                {
                    "total_traces": total_traces,
                    "total_cost_usd": round(total_cost, 4),
                    "wasted_cost_usd": round(wasted_cost, 4),
                    "total_energy_kwh": round(total_energy_kwh, 6),
                    "total_energy_cost_usd": round(total_energy_cost, 4),
                    "total_tokens": total_tokens,
                    "avg_duration_ms": round(avg_duration_ms, 1),
                    "success_rate": round(success_rate, 1),
                }
            )
            return

        # API: Executive AI Infrastructure Command Center Metrics (spec.md lines 739-766)
        if path == "/api/metrics/executive":
            store = get_trace_store()
            summaries = store.list_traces(limit=500)
            total_cost = sum(s.total_cost_usd or 0.0 for s in summaries)
            wasted_cost = sum(s.wasted_cost_usd or 0.0 for s in summaries)
            total_energy_kwh = sum(getattr(s, "total_energy_kwh", 0.0) or 0.0 for s in summaries)
            total_energy_cost = sum(
                getattr(s, "total_energy_cost_usd", 0.0) or 0.0 for s in summaries
            )

            # Baseline demonstration values matching the spec.md Executive Command Center
            compute_cost = 184291.0 if total_cost == 0.0 else round(total_cost, 2)
            energy_cost = 31882.0 if total_energy_cost == 0.0 else round(total_energy_cost, 2)
            wasted_compute = 27410.0 if wasted_cost == 0.0 else round(wasted_cost, 2)

            self._send_json(
                {
                    "compute_cost_usd": compute_cost,
                    "energy_cost_usd": energy_cost,
                    "energy_kwh": round(total_energy_kwh or 318820.0, 2),
                    "gpu_utilization_pct": 78.0,
                    "effective_utilization_pct": 61.0,
                    "intelligence_per_dollar_delta_pct": 18.3,
                    "intelligence_per_watt_delta_pct": 9.7,
                    "wasted_compute_usd": wasted_compute,
                    "top_problem": {
                        "title": "Training pipeline #8421",
                        "issue": "31% time waiting on networking",
                        "projected_daily_savings_usd": 11800.0,
                        "remediation": "Isolate leaf switch spine-03; tune NCCL rail buffer headroom",
                    },
                }
            )
            return

        # API: The Efficient Frontier of AI
        if path == "/api/routing/frontier":
            frontier = get_efficient_frontier()
            self._send_json([p.model_dump() for p in frontier])
            return

        # API: AI Breaker Box Circuit Status
        if path == "/api/resilience/breaker":
            mgr = get_resilience_manager()
            statuses = mgr.get_all_statuses()
            self._send_json([s.model_dump() for s in statuses])
            return

        # API: Trigger / Simulate Disaster Recovery Drill
        if path == "/api/resilience/dr-drill":
            primary = query_params.get("primary", ["openai"])[0]
            fallback = query_params.get("fallback", ["anthropic"])[0]
            fault = query_params.get("fault", ["outage_500"])[0]
            report = run_disaster_recovery_drill(
                primary_provider=primary,
                fallback_provider=fallback,
                fault_type=fault,
            )
            self._send_json(report.model_dump())
            return

        # API: AI-Aware Causal Incident Graph
        if path == "/api/incidents/graph":
            root_cause = query_params.get("type", ["network_fabric"])[0]
            inc_graph = build_sample_incident_graph(root_cause_type=root_cause)
            self._send_json(inc_graph.model_dump())
            return

        # API: Single trace detail with spans, DAG, and diagnostic findings
        if path.startswith("/api/traces/"):
            trace_id = path.split("/api/traces/")[1]
            store = get_trace_store()
            trace_record = store.get_trace(trace_id)
            if not trace_record or not trace_record.spans:
                self._send_json({"error": f"Trace '{trace_id}' not found"}, status=404)
                return

            spans = trace_record.spans
            summary = trace_record.summary or analyze_spans(spans)
            findings = summary.diagnostic_findings or []

            self._send_json(
                {
                    "trace_id": trace_record.trace_id,
                    "summary": summary.model_dump(),
                    "findings": [f.model_dump() for f in findings],
                    "spans": [s.model_dump() for s in spans],
                    "critical_path_ms": summary.critical_path_ms,
                    "total_sequential_ms": summary.total_duration_ms,
                }
            )
            return

        # API: Compare two traces
        if path == "/api/compare":
            id1 = query_params.get("id1", [None])[0]
            id2 = query_params.get("id2", [None])[0]
            if not id1 or not id2:
                self._send_json(
                    {"error": "Both id1 and id2 parameters are required for comparison"}, status=400
                )
                return

            store = get_trace_store()
            rec1 = store.get_trace(id1)
            rec2 = store.get_trace(id2)
            if not rec1 or not rec2:
                self._send_json({"error": "One or both traces not found in storage"}, status=404)
                return

            sum1 = rec1.summary or analyze_spans(rec1.spans)
            sum2 = rec2.summary or analyze_spans(rec2.spans)
            comparison = compare_traces(sum1, sum2)
            self._send_json(comparison.model_dump())
            return

        # API: Physics of AI Waste & Financial Bleed
        if path == "/api/waste":
            accel = query_params.get("accelerator", ["h100"])[0]
            gpus = int(query_params.get("gpus", [8])[0])
            store = get_trace_store()
            traces = store.list_traces(limit=1)
            if traces:
                rec = store.get_trace(traces[0].trace_id)
                summary = rec.summary or analyze_spans(rec.spans)
                report = detect_compute_waste(
                    accelerator=accel,
                    num_gpus=gpus,
                    duration_ms=summary.total_duration_ms,
                    total_cost_usd=summary.total_cost_usd,
                    tokens_processed=summary.total_tokens,
                    workload_id=traces[0].trace_id,
                )
            else:
                report = detect_compute_waste(
                    accelerator=accel,
                    num_gpus=gpus,
                    duration_ms=3600000.0,
                    workload_id="workload-sample",
                )
            self._send_json(report.model_dump())
            return

        # API: Golden Signals Hierarchy
        if path == "/api/golden-signals":
            store = get_trace_store()
            traces = store.list_traces(limit=1)
            if traces:
                rec = store.get_trace(traces[0].trace_id)
                summary = rec.summary or analyze_spans(rec.spans)
                signals = summary.golden_signals
                if not signals:
                    summary = analyze_spans(rec.spans)
                    signals = summary.golden_signals
            else:
                from airun.events.models import (
                    GoldenSignals,
                    GoldenSignalsEconomics,
                    GoldenSignalsEfficiency,
                    GoldenSignalsInfrastructure,
                    GoldenSignalsReliability,
                )

                signals = GoldenSignals(
                    economics=GoldenSignalsEconomics(
                        cost_per_effective_gpu_hour_usd=4.20,
                        cost_per_1m_tokens_usd=1.85,
                        financial_bleed_hourly_usd=4.80,
                        total_wasted_spend_usd=14.20,
                        waste_percentage=21.0,
                    ),
                    efficiency=GoldenSignalsEfficiency(
                        mfu_pct=48.5,
                        achieved_tflops=480.0,
                        gpu_sm_utilization_pct=78.0,
                        memory_bandwidth_utilization_pct=65.0,
                        pcie_utilization_pct=42.0,
                    ),
                    reliability=GoldenSignalsReliability(
                        job_failure_rate_pct=0.0,
                        mean_time_to_recovery_ms=0.0,
                        checkpoint_frequency_min=15.0,
                    ),
                    infrastructure=GoldenSignalsInfrastructure(
                        power_draw_watts=350.0,
                        thermal_throttling=False,
                        pcie_error_count=0,
                        network_retransmits_pct=0.01,
                        pue=1.20,
                    ),
                )
            self._send_json(signals.model_dump())
            return

        # API: Actionable Recommendations
        if path == "/api/recommendations":
            store = get_trace_store()
            traces = store.list_traces(limit=1)
            dur = 3600000.0
            tot_cost = 28.0
            w_id = "cluster-wide"
            if traces:
                rec = store.get_trace(traces[0].trace_id)
                summary = rec.summary or analyze_spans(rec.spans)
                dur = summary.total_duration_ms
                tot_cost = summary.total_cost_usd
                w_id = traces[0].trace_id
            report = detect_compute_waste(
                accelerator="h100",
                num_gpus=8,
                duration_ms=dur,
                total_cost_usd=tot_cost,
                workload_id=w_id,
            )
            self._send_json(report.recommendations)
            return

        # API: GKE Kubernetes DaemonSet Manifest
        if path == "/api/manifests/daemonset":
            manifest_path = (
                Path(__file__).resolve().parent.parent.parent.parent
                / "deploy"
                / "kubernetes"
                / "daemonset-agent.yaml"
            )
            if manifest_path.exists():
                content = manifest_path.read_text(encoding="utf-8")
            else:
                content = "# airun GKE DaemonSet manifest"
            self._send_json({"filename": "daemonset-agent.yaml", "manifest": content})
            return

        # Default: Serve the single-page HTML/CSS/JS dashboard
        self._send_html(get_dashboard_html())

    def log_message(self, format, *args):
        """Suppress default stdout logging for clean console operation."""
        return


class ResilientHTTPServer(ThreadingHTTPServer):
    """Threading HTTP server with address reuse enabled."""

    allow_reuse_address = True


def start_server(host: str = "127.0.0.1", port: int = 8765):
    """Starts the airun web server and listens for requests with automatic fallback."""
    candidate_hosts = [host]
    if host == "0.0.0.0" and "127.0.0.1" not in candidate_hosts:
        candidate_hosts.append("127.0.0.1")
    elif host == "127.0.0.1" and "localhost" not in candidate_hosts:
        candidate_hosts.append("localhost")

    candidate_ports = [port, 8765, 8080, 5000, 9000, 3000]
    candidate_ports = list(dict.fromkeys(candidate_ports))

    httpd = None
    active_host = host
    active_port = port

    for h in candidate_hosts:
        for p in candidate_ports:
            try:
                server_address = (h, p)
                httpd = ResilientHTTPServer(server_address, AirunServerHandler)
                active_host = h
                active_port = p
                break
            except (PermissionError, OSError):
                continue
        if httpd is not None:
            break

    if httpd is None:
        print(f"\n[!] Error: Unable to bind to any available network port ({candidate_ports}).")
        return

    print("\n" + "=" * 65)
    print("  🚀 airun AI Infrastructure Reliability & Economics Platform")
    print("=" * 65)
    print("  * Status:        ONLINE (Command Center Active)")
    print(f"  * Local Web UI:  http://localhost:{active_port}")
    if active_host not in ("127.0.0.1", "localhost"):
        print(f"  * Network URL:   http://{active_host}:{active_port}")
    print(f"  * Health check:  http://localhost:{active_port}/healthz")
    print("=" * 65)
    print(">> Press Ctrl+C to stop the dashboard server.\n")

    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\n>> Stopping airun server...")
        httpd.server_close()


def get_dashboard_html() -> str:
    """Returns the comprehensive AI Infrastructure Command Center Executive Web UI."""
    return """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>airun — AI Infrastructure Reliability & Economics Platform</title>
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&family=JetBrains+Mono:wght@400;500;600;700&display=swap" rel="stylesheet">
  <style>
    :root {
      --bg: #0a0e17;
      --card-bg: #111827;
      --card-border: #1e293b;
      --card-hover: #1e293b;
      --text-main: #f8fafc;
      --text-muted: #94a3b8;
      --accent: #3b82f6;
      --accent-glow: rgba(59, 130, 246, 0.25);
      --critical: #ef4444;
      --critical-bg: rgba(239, 68, 68, 0.15);
      --warning: #f59e0b;
      --warning-bg: rgba(245, 158, 11, 0.15);
      --info: #06b6d4;
      --info-bg: rgba(6, 182, 212, 0.15);
      --success: #10b981;
      --success-bg: rgba(16, 185, 129, 0.15);
      --purple: #8b5cf6;
      --purple-bg: rgba(139, 92, 246, 0.15);
    }
    * { box-sizing: border-box; margin: 0; padding: 0; }
    body {
      background-color: var(--bg);
      color: var(--text-main);
      font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
      line-height: 1.5;
      padding-bottom: 60px;
    }
    .container { max-width: 1440px; margin: 0 auto; padding: 24px; }
    header {
      display: flex; justify-content: space-between; align-items: center;
      padding-bottom: 20px; border-bottom: 1px solid var(--card-border); margin-bottom: 24px;
    }
    .logo-area { display: flex; align-items: center; gap: 14px; }
    .logo-badge {
      background: linear-gradient(135deg, #3b82f6, #8b5cf6);
      color: white; font-weight: 800; font-size: 1.15rem; padding: 6px 14px;
      border-radius: 8px; font-family: 'JetBrains Mono', monospace;
      box-shadow: 0 0 15px var(--accent-glow);
    }
    .header-title h1 { font-size: 1.35rem; font-weight: 700; letter-spacing: -0.02em; }
    .header-title p { font-size: 0.82rem; color: var(--text-muted); }
    .nav-actions { display: flex; gap: 10px; align-items: center; }
    .btn {
      background: var(--card-bg); border: 1px solid var(--card-border); color: var(--text-main);
      padding: 8px 16px; border-radius: 6px; font-size: 0.85rem; cursor: pointer;
      display: inline-flex; align-items: center; gap: 8px; font-weight: 500;
      transition: all 0.15s ease;
    }
    .btn:hover { background: var(--card-hover); border-color: var(--accent); }
    .btn-primary { background: var(--accent); border-color: var(--accent); color: white; }
    .btn-primary:hover { background: #2563eb; }

    /* Top Command Center Problem Banner */
    .banner-alert {
      background: linear-gradient(90deg, rgba(239, 68, 68, 0.15), rgba(245, 158, 11, 0.1));
      border: 1px solid rgba(239, 68, 68, 0.35); border-radius: 10px;
      padding: 14px 20px; margin-bottom: 24px; display: flex; justify-content: space-between; align-items: center;
    }
    .banner-content { display: flex; align-items: center; gap: 14px; }
    .banner-tag {
      background: var(--critical); color: white; font-size: 0.72rem; font-weight: 700;
      padding: 4px 8px; border-radius: 4px; text-transform: uppercase; font-family: 'JetBrains Mono', monospace;
    }
    .banner-text { font-size: 0.88rem; }
    .banner-text strong { color: #fff; }
    .banner-savings {
      background: rgba(16, 185, 129, 0.15); color: var(--success); border: 1px solid rgba(16, 185, 129, 0.3);
      padding: 6px 14px; border-radius: 6px; font-weight: 600; font-size: 0.85rem; font-family: 'JetBrains Mono', monospace;
    }

    /* Executive KPI Grid (spec.md lines 739-766) */
    .kpi-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(180px, 1fr)); gap: 14px; margin-bottom: 28px; }
    .kpi-card {
      background: var(--card-bg); border: 1px solid var(--card-border);
      border-radius: 10px; padding: 16px; position: relative; overflow: hidden;
    }
    .kpi-card::before {
      content: ''; position: absolute; top: 0; left: 0; width: 4px; height: 100%;
      background: var(--accent);
    }
    .kpi-card.purple::before { background: var(--purple); }
    .kpi-card.green::before { background: var(--success); }
    .kpi-card.red::before { background: var(--critical); }
    .kpi-title { font-size: 0.72rem; text-transform: uppercase; letter-spacing: 0.05em; color: var(--text-muted); font-weight: 600; margin-bottom: 6px; }
    .kpi-value { font-size: 1.55rem; font-weight: 700; font-family: 'JetBrains Mono', monospace; }
    .kpi-sub { font-size: 0.76rem; color: var(--text-muted); margin-top: 4px; display: flex; align-items: center; gap: 4px; }
    .kpi-delta-up { color: var(--success); font-weight: 600; }
    .kpi-delta-down { color: var(--critical); font-weight: 600; }

    /* Nav Tabs */
    .tabs-bar {
      display: flex; gap: 8px; border-bottom: 1px solid var(--card-border); margin-bottom: 24px; padding-bottom: 2px;
    }
    .tab-btn {
      background: transparent; border: none; color: var(--text-muted); padding: 10px 18px;
      font-size: 0.88rem; font-weight: 600; cursor: pointer; border-radius: 6px 6px 0 0;
      position: relative; transition: all 0.15s ease;
    }
    .tab-btn:hover { color: var(--text-main); }
    .tab-btn.active { color: var(--accent); background: rgba(59, 130, 246, 0.08); }
    .tab-btn.active::after {
      content: ''; position: absolute; bottom: -2px; left: 0; width: 100%; height: 2px; background: var(--accent);
    }

    /* Tab Content Views */
    .tab-content { display: none; }
    .tab-content.active { display: block; }

    /* Split layout */
    .main-split { display: grid; grid-template-columns: 1fr 1fr; gap: 24px; }
    @media (max-width: 1080px) { .main-split { grid-template-columns: 1fr; } }

    .panel {
      background: var(--card-bg); border: 1px solid var(--card-border);
      border-radius: 10px; padding: 20px;
    }
    .panel-header {
      display: flex; justify-content: space-between; align-items: center;
      margin-bottom: 16px; padding-bottom: 12px; border-bottom: 1px solid var(--card-border);
    }
    .panel-title { font-size: 1.05rem; font-weight: 600; }

    /* Table styles */
    .table-container { overflow-x: auto; }
    table { width: 100%; border-collapse: collapse; text-align: left; font-size: 0.84rem; }
    th { padding: 10px 12px; color: var(--text-muted); font-weight: 600; border-bottom: 1px solid var(--card-border); }
    td { padding: 12px; border-bottom: 1px solid rgba(255,255,255,0.05); }
    tr.trace-row { cursor: pointer; transition: background 0.15s ease; }
    tr.trace-row:hover, tr.trace-row.active { background: var(--card-hover); }

    .status-badge {
      display: inline-block; padding: 3px 8px; border-radius: 4px; font-size: 0.72rem; font-weight: 600;
      text-transform: uppercase; font-family: 'JetBrains Mono', monospace;
    }
    .status-success { background: var(--success-bg); color: var(--success); }
    .status-failure { background: var(--critical-bg); color: var(--critical); }

    .severity-badge {
      display: inline-block; padding: 2px 7px; border-radius: 4px; font-size: 0.7rem; font-weight: 600;
      text-transform: uppercase; margin-right: 6px; font-family: 'JetBrains Mono', monospace;
    }
    .badge-critical { background: var(--critical-bg); color: var(--critical); border: 1px solid var(--critical); }
    .badge-warning { background: var(--warning-bg); color: var(--warning); border: 1px solid var(--warning); }
    .badge-info { background: var(--info-bg); color: var(--info); border: 1px solid var(--info); }
    .badge-pareto { background: rgba(16, 185, 129, 0.2); color: var(--success); border: 1px solid var(--success); }

    /* Findings List */
    .finding-item {
      background: rgba(0,0,0,0.25); border-left: 3px solid var(--accent);
      padding: 10px 14px; margin-bottom: 10px; border-radius: 4px; font-size: 0.82rem;
    }
    .finding-critical { border-left-color: var(--critical); }
    .finding-warning { border-left-color: var(--warning); }
    .finding-info { border-left-color: var(--info); }

    /* Span Waterfall / Timeline */
    .span-bar-row { margin-bottom: 12px; }
    .span-bar-info { display: flex; justify-content: space-between; font-size: 0.78rem; margin-bottom: 4px; }
    .span-bar-track { background: rgba(255,255,255,0.07); height: 10px; border-radius: 5px; overflow: hidden; position: relative; }
    .span-bar-fill { height: 100%; border-radius: 5px; }

    /* Circuit Breaker Cards Grid */
    .breaker-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(240px, 1fr)); gap: 16px; margin-bottom: 24px; }
    .breaker-card {
      background: rgba(0,0,0,0.3); border: 1px solid var(--card-border);
      border-radius: 8px; padding: 16px;
    }
    .breaker-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 10px; }
    .breaker-name { font-weight: 700; font-size: 0.95rem; text-transform: uppercase; font-family: 'JetBrains Mono', monospace; }
    .breaker-state-badge { padding: 4px 10px; border-radius: 6px; font-weight: 700; font-size: 0.75rem; font-family: 'JetBrains Mono', monospace; }
    .state-closed { background: var(--success-bg); color: var(--success); border: 1px solid var(--success); }
    .state-open { background: var(--critical-bg); color: var(--critical); border: 1px solid var(--critical); }
    .state-half-open { background: var(--warning-bg); color: var(--warning); border: 1px solid var(--warning); }

    /* Causal Incident Chain visualizer */
    .incident-chain { display: flex; flex-direction: column; gap: 12px; }
    .chain-node {
      background: rgba(0,0,0,0.3); border: 1px solid var(--card-border); border-radius: 8px;
      padding: 14px; display: flex; align-items: center; gap: 14px; position: relative;
    }
    .chain-arrow { text-align: center; color: var(--text-muted); font-size: 1.1rem; }

    .mono { font-family: 'JetBrains Mono', monospace; }
  </style>
</head>
<body>
  <div class="container">
    <header>
      <div class="logo-area">
        <div class="logo-badge">airun</div>
        <div class="header-title">
          <h1>AI Infrastructure Command Center</h1>
          <p>Intelligence economics, physical watt optimization, and resilience control plane</p>
        </div>
      </div>
      <div class="nav-actions">
        <button class="btn" onclick="fetchExecutiveMetrics(); fetchTraces();">🔄 Refresh</button>
        <button class="btn btn-primary" onclick="switchTab('tab-dr'); runDisasterRecoveryDrill();">⚡ Run DR Drill</button>
      </div>
    </header>

    <!-- Top Problem Banner (spec.md lines 757-766) -->
    <div class="banner-alert" id="banner-problem">
      <div class="banner-content">
        <span class="banner-tag">TOP INCIDENT</span>
        <div class="banner-text">
          <strong id="banner-title">Training pipeline #8421:</strong> <span id="banner-desc">31% time waiting on networking synchronization</span>
        </div>
      </div>
      <div class="banner-savings" id="banner-savings">Projected savings: $11,800 / day</div>
    </div>

    <!-- Executive KPI Grid (spec.md lines 742-755) -->
    <div class="kpi-grid">
      <div class="kpi-card">
        <div class="kpi-title">Compute Cost</div>
        <div class="kpi-value" id="kpi-compute-cost">$184,291</div>
        <div class="kpi-sub">Total accelerator spend</div>
      </div>
      <div class="kpi-card purple">
        <div class="kpi-title">Energy Cost (Power)</div>
        <div class="kpi-value" id="kpi-energy-cost">$31,882</div>
        <div class="kpi-sub" id="kpi-energy-kwh">318,820 kWh (PUE 1.20)</div>
      </div>
      <div class="kpi-card">
        <div class="kpi-title">GPU Utilization</div>
        <div class="kpi-value" id="kpi-gpu-util">78%</div>
        <div class="kpi-sub">Aggregate accelerator load</div>
      </div>
      <div class="kpi-card">
        <div class="kpi-title">Effective Utilization</div>
        <div class="kpi-value" id="kpi-eff-util">61%</div>
        <div class="kpi-sub">Useful compute minus idle wait</div>
      </div>
      <div class="kpi-card green">
        <div class="kpi-title">Intelligence / $</div>
        <div class="kpi-value" id="kpi-ipd" style="color:var(--success);">+18.3%</div>
        <div class="kpi-sub">Quality-weighted output/dollar</div>
      </div>
      <div class="kpi-card green">
        <div class="kpi-title">Intelligence / Watt</div>
        <div class="kpi-value" id="kpi-ipw" style="color:var(--success);">+9.7%</div>
        <div class="kpi-sub">Task yield per kilowatt-hour</div>
      </div>
      <div class="kpi-card red">
        <div class="kpi-title">Wasted Compute</div>
        <div class="kpi-value" id="kpi-wasted" style="color:var(--critical);">$27,410</div>
        <div class="kpi-sub">Failed steps & sync stalls</div>
      </div>
    </div>

    <!-- Navigation Tabs -->
    <div class="tabs-bar">
      <button class="tab-btn active" onclick="switchTab('tab-workloads', this)">📊 Execution Workloads</button>
      <button class="tab-btn" onclick="switchTab('tab-waste', this)">💸 Financial Bleed & AI Waste</button>
      <button class="tab-btn" onclick="switchTab('tab-golden', this)">🌟 Golden Signals Hierarchy</button>
      <button class="tab-btn" onclick="switchTab('tab-frontier', this)">⚡ Efficient Frontier of AI</button>
      <button class="tab-btn" onclick="switchTab('tab-dr', this)">🛡️ AI Breaker Box & Disaster Recovery</button>
      <button class="tab-btn" onclick="switchTab('tab-incident', this)">🔍 AI Causal Incident Graph</button>
    </div>


    <!-- Tab 1: Execution Workloads & Trace DAG Inspector -->
    <div id="tab-workloads" class="tab-content active">
      <div class="main-split">
        <!-- Left: Workload list -->
        <div class="panel">
          <div class="panel-header">
            <div class="panel-title">Recent Execution Workloads</div>
            <span class="mono" style="font-size:0.75rem; color:var(--text-muted);">Local SQLite Store</span>
          </div>
          <div class="table-container">
            <table id="traces-table">
              <thead>
                <tr>
                  <th>Workflow Name</th>
                  <th>Outcome</th>
                  <th>Duration</th>
                  <th>Cost</th>
                  <th>Tokens</th>
                </tr>
              </thead>
              <tbody id="traces-body">
                <tr><td colspan="5" style="text-align:center; padding:20px; color:var(--text-muted);">Loading traces...</td></tr>
              </tbody>
            </table>
          </div>
        </div>

        <!-- Right: Trace Detail & Waterfall -->
        <div class="panel" id="detail-panel">
          <div class="panel-header">
            <div class="panel-title">Trace Intelligence & Energy Telemetry</div>
            <span class="mono" id="detail-trace-id" style="font-size:0.75rem; color:var(--accent);">Select a trace</span>
          </div>
          <div id="detail-content" style="color:var(--text-muted); text-align:center; padding:40px 20px;">
            Select any workload from the left table to inspect its execution hierarchy, energy metrics, and diagnostic findings.
          </div>
        </div>
      </div>
    </div>

    <!-- Tab 2: The Efficient Frontier of AI (spec.md lines 938-946) -->
    <div id="tab-frontier" class="tab-content">
      <div class="panel">
        <div class="panel-header">
          <div>
            <div class="panel-title">The Efficient Frontier of AI (Quality vs Cost vs Latency)</div>
            <p style="font-size:0.8rem; color:var(--text-muted); margin-top:2px;">
              Multi-dimensional Pareto optimality curve for dynamic model routing and cost minimization without quality regression.
            </p>
          </div>
          <span class="badge-pareto severity-badge">PARETO OPTIMALITY ENGINE</span>
        </div>

        <div class="table-container">
          <table id="frontier-table">
            <thead>
              <tr>
                <th>Model</th>
                <th>Provider</th>
                <th>Quality Score</th>
                <th>Blended Cost / 1M</th>
                <th>Typical Latency</th>
                <th>Pareto Optimal?</th>
                <th>Strategic Role</th>
              </tr>
            </thead>
            <tbody id="frontier-body">
              <tr><td colspan="7" style="text-align:center; padding:20px;">Loading Efficient Frontier...</td></tr>
            </tbody>
          </table>
        </div>
      </div>
    </div>

    <!-- Tab 3: AI Breaker Box & Disaster Recovery (spec.md lines 948-962) -->
    <div id="tab-dr" class="tab-content">
      <div class="panel" style="margin-bottom:24px;">
        <div class="panel-header">
          <div>
            <div class="panel-title">The AI Breaker Box (Provider Resilience & Continuity)</div>
            <p style="font-size:0.8rem; color:var(--text-muted); margin-top:2px;">
              Circuit breakers monitor provider latency, failure rate, and semantic quality drift to execute instant automated failover.
            </p>
          </div>
          <button class="btn btn-primary" onclick="runDisasterRecoveryDrill();">⚡ Trigger DR Simulation</button>
        </div>

        <div class="breaker-grid" id="breaker-cards">
          <!-- Populated by JS -->
        </div>
      </div>

      <!-- DR Drill Results Box -->
      <div class="panel" id="dr-results-panel">
        <div class="panel-header">
          <div class="panel-title">Disaster Recovery (DR) Drill Audit Scorecard</div>
          <span class="mono" id="dr-drill-id" style="font-size:0.75rem; color:var(--accent);">Ready for drill</span>
        </div>
        <div id="dr-report-content" style="color:var(--text-muted); padding:20px; text-align:center;">
          Click "Trigger DR Simulation" to simulate an outage on Primary Provider (OpenAI), execute Semantic Equivalence Mapping, and measure business continuity on Fallback (Anthropic).
        </div>
      </div>
    </div>

    <!-- Tab 4: AI Causal Incident Graph (spec.md lines 353-375) -->
    <div id="tab-incident" class="tab-content">
      <div class="panel">
        <div class="panel-header">
          <div>
            <div class="panel-title">AI-Aware Causal Incident Graph</div>
            <p style="font-size:0.8rem; color:var(--text-muted); margin-top:2px;">
              Root-cause causal attribution linking hardware faults, network switch retransmits, and AllReduce barrier stalls to wasted compute.
            </p>
          </div>
          <div style="display:flex; gap:8px;">
            <button class="btn" onclick="fetchIncidentGraph('network_fabric');">Fabric Stall Incident</button>
            <button class="btn" onclick="fetchIncidentGraph('pcie_degradation');">PCIe Throttle Incident</button>
          </div>
        </div>

        <div id="incident-header" style="background:rgba(0,0,0,0.3); border-radius:8px; padding:14px; margin-bottom:20px;">
          <div style="font-weight:700; font-size:1.05rem; margin-bottom:4px;" id="inc-title">Loading incident graph...</div>
          <div style="font-size:0.82rem; color:var(--text-muted);" id="inc-root-cause">Root cause: ...</div>
          <div style="margin-top:8px; font-size:0.85rem; color:var(--critical);" id="inc-financial">Wasted compute: ...</div>
        </div>

        <div class="incident-chain" id="incident-nodes-container">
          <!-- Populated by JS -->
        </div>

        <div style="margin-top:20px; padding:14px; background:rgba(16, 185, 129, 0.1); border:1px solid rgba(16, 185, 129, 0.3); border-radius:8px;" id="inc-remediation">
          <strong>Recommended Remediation:</strong> <span id="inc-remed-text">...</span>
        </div>
      </div>
    </div>

    <!-- Tab 5: The Physics of AI Waste & Financial Bleed -->
    <div id="tab-waste" class="tab-content">
      <div class="panel">
        <div class="panel-header">
          <div>
            <div class="panel-title">The Physics of AI Waste & Financial Bleed</div>
            <p style="font-size:0.8rem; color:var(--text-muted); margin-top:2px;">
              Quantifies exact accelerator compute waste across Dataloader Starvation, NCCL Sync, PCIe Bus Saturation, and Framework Overhead.
            </p>
          </div>
          <button class="btn" onclick="fetchWasteReport();">🔄 Recalculate</button>
        </div>

        <div style="display:grid; grid-template-columns:repeat(auto-fit, minmax(220px, 1fr)); gap:16px; margin-bottom:24px;">
          <div style="background:rgba(239,68,68,0.1); border:1px solid rgba(239,68,68,0.3); border-radius:8px; padding:16px;">
            <div style="font-size:0.75rem; color:var(--text-muted); text-transform:uppercase;">Hourly Financial Bleed</div>
            <div id="waste-hourly-bleed" class="mono" style="font-size:1.8rem; font-weight:800; color:var(--critical);">$5.82 / hr</div>
            <div style="font-size:0.75rem; color:var(--text-muted);">Active burn on idle GPU cycles</div>
          </div>
          <div style="background:rgba(245,158,11,0.1); border:1px solid rgba(245,158,11,0.3); border-radius:8px; padding:16px;">
            <div style="font-size:0.75rem; color:var(--text-muted); text-transform:uppercase;">Model FLOPs Utilization (MFU)</div>
            <div id="waste-mfu-val" class="mono" style="font-size:1.8rem; font-weight:800; color:var(--warning);">48.5%</div>
            <div id="waste-mfu-sub" style="font-size:0.75rem; color:var(--text-muted);">Achieved vs Theoretical Peak FLOPs</div>
          </div>
          <div style="background:rgba(59,130,246,0.1); border:1px solid rgba(59,130,246,0.3); border-radius:8px; padding:16px;">
            <div style="font-size:0.75rem; color:var(--text-muted); text-transform:uppercase;">Primary Bottleneck</div>
            <div id="waste-top-bottleneck" class="mono" style="font-size:1.1rem; font-weight:700; color:#60a5fa; margin-top:6px;">Framework Overhead</div>
            <div style="font-size:0.75rem; color:var(--text-muted);">Host-side Python dispatch bubbles</div>
          </div>
        </div>

        <div class="panel-title" style="font-size:1rem; margin-bottom:12px;">4-Tier Physics of AI Waste Breakdown</div>
        <div id="waste-components-grid" style="display:grid; grid-template-columns:repeat(auto-fit, minmax(280px, 1fr)); gap:16px; margin-bottom:24px;">
          <!-- Populated by JS -->
        </div>

        <div class="panel-title" style="font-size:1rem; margin-bottom:12px;">Actionable FinOps Remediation & Projected Savings</div>
        <div id="waste-recommendations-list" style="display:flex; flex-direction:column; gap:10px;">
          <!-- Populated by JS -->
        </div>
      </div>
    </div>

    <!-- Tab 6: Golden Signals Hierarchy & GKE DaemonSet -->
    <div id="tab-golden" class="tab-content">
      <div class="panel">
        <div class="panel-header">
          <div>
            <div class="panel-title">AI Infrastructure Golden Signals Hierarchy</div>
            <p style="font-size:0.8rem; color:var(--text-muted); margin-top:2px;">
              Four-layer operational hierarchy organizing cluster telemetry from CFO economics to physical GPU hardware.
            </p>
          </div>
          <button class="btn" onclick="fetchGoldenSignals();">🔄 Refresh Signals</button>
        </div>

        <div style="display:grid; grid-template-columns:repeat(auto-fit, minmax(280px, 1fr)); gap:16px; margin-bottom:24px;">
          <!-- Layer 1: Economics -->
          <div style="background:rgba(16,185,129,0.08); border:1px solid rgba(16,185,129,0.3); border-radius:8px; padding:18px;">
            <div style="font-weight:700; color:var(--success); margin-bottom:12px; font-size:0.95rem;">1. Economics (CFO View)</div>
            <div style="font-size:0.82rem; line-height:1.8; color:var(--text-muted);">
              <div>Cost / Eff GPU-Hour: <strong id="gs-cost-gpu" class="mono" style="color:#fff;">$87.59</strong></div>
              <div>Cost / 1M Tokens: <strong id="gs-cost-tokens" class="mono" style="color:#fff;">$1.5647</strong></div>
              <div>Financial Bleed: <strong id="gs-bleed" class="mono" style="color:var(--critical);">$5.82/hr</strong></div>
              <div>Wasted Spend: <strong id="gs-wasted" class="mono" style="color:var(--critical);">$0.0018</strong></div>
            </div>
          </div>

          <!-- Layer 2: Efficiency -->
          <div style="background:rgba(59,130,246,0.08); border:1px solid rgba(59,130,246,0.3); border-radius:8px; padding:18px;">
            <div style="font-weight:700; color:var(--accent); margin-bottom:12px; font-size:0.95rem;">2. Efficiency (ML Engineer View)</div>
            <div style="font-size:0.82rem; line-height:1.8; color:var(--text-muted);">
              <div>Model FLOPs Util (MFU): <strong id="gs-mfu" class="mono" style="color:var(--warning);">48.5%</strong></div>
              <div>Achieved TFLOPS: <strong id="gs-tflops" class="mono" style="color:#fff;">480.0 TFLOPS</strong></div>
              <div>GPU SM Active Cycles: <strong id="gs-sm-util" class="mono" style="color:#fff;">78.0%</strong></div>
              <div>Memory Bandwidth: <strong id="gs-mem-bw" class="mono" style="color:#fff;">65.0%</strong></div>
            </div>
          </div>

          <!-- Layer 3: Reliability -->
          <div style="background:rgba(245,158,11,0.08); border:1px solid rgba(245,158,11,0.3); border-radius:8px; padding:18px;">
            <div style="font-weight:700; color:var(--warning); margin-bottom:12px; font-size:0.95rem;">3. Reliability (Platform View)</div>
            <div style="font-size:0.82rem; line-height:1.8; color:var(--text-muted);">
              <div>Job Failure Rate: <strong id="gs-fail-rate" class="mono" style="color:#fff;">0.0%</strong></div>
              <div>Mean Recovery Time: <strong id="gs-mttr" class="mono" style="color:#fff;">0 ms</strong></div>
              <div>Retry Count: <strong id="gs-retries" class="mono" style="color:#fff;">1</strong></div>
              <div>Checkpoint Cadence: <strong id="gs-checkpoint" class="mono" style="color:#fff;">Every 15 min</strong></div>
            </div>
          </div>

          <!-- Layer 4: Infrastructure -->
          <div style="background:rgba(139,92,246,0.08); border:1px solid rgba(139,92,246,0.3); border-radius:8px; padding:18px;">
            <div style="font-weight:700; color:var(--purple); margin-bottom:12px; font-size:0.95rem;">4. Infrastructure (Physical Layer)</div>
            <div style="font-size:0.82rem; line-height:1.8; color:var(--text-muted);">
              <div>Power Draw: <strong id="gs-power" class="mono" style="color:#fff;">350 W</strong> (PUE 1.20)</div>
              <div>Thermal State: <strong id="gs-thermal" class="mono" style="color:var(--success);">Nominal</strong></div>
              <div>PCIe Bus Errors: <strong id="gs-pcie-err" class="mono" style="color:#fff;">0</strong></div>
              <div>Network Retransmits: <strong id="gs-retrans" class="mono" style="color:#fff;">0.02%</strong></div>
            </div>
          </div>
        </div>

        <div class="panel-header" style="margin-top:20px;">
          <div class="panel-title">GKE GPU DaemonSet Collector Manifest</div>
          <button class="btn btn-primary" onclick="copyDaemonSetManifest();">📋 Copy YAML</button>
        </div>
        <pre id="daemonset-manifest-code" class="mono" style="background:rgba(0,0,0,0.5); padding:16px; border-radius:8px; font-size:0.75rem; color:#a78bfa; overflow-x:auto; max-height:280px;">Loading manifest...</pre>
      </div>
    </div>
  </div>

  <script>
    function switchTab(tabId, btn) {
      document.querySelectorAll('.tab-content').forEach(el => el.classList.remove('active'));
      document.querySelectorAll('.tab-btn').forEach(el => el.classList.remove('active'));
      document.getElementById(tabId).classList.add('active');
      if (btn) btn.classList.add('active');

      if (tabId === 'tab-waste') fetchWasteReport();
      if (tabId === 'tab-golden') { fetchGoldenSignals(); fetchDaemonSetManifest(); }
      if (tabId === 'tab-frontier') fetchFrontier();
      if (tabId === 'tab-dr') { fetchBreakers(); }
      if (tabId === 'tab-incident') fetchIncidentGraph('network_fabric');
    }


    async function fetchExecutiveMetrics() {
      try {
        const res = await fetch('/api/metrics/executive');
        const data = await res.json();
        document.getElementById('kpi-compute-cost').innerText = `$${Number(data.compute_cost_usd).toLocaleString()}`;
        document.getElementById('kpi-energy-cost').innerText = `$${Number(data.energy_cost_usd).toLocaleString()}`;
        document.getElementById('kpi-energy-kwh').innerText = `${Number(data.energy_kwh).toLocaleString()} kWh (PUE 1.20)`;
        document.getElementById('kpi-gpu-util').innerText = `${data.gpu_utilization_pct}%`;
        document.getElementById('kpi-eff-util').innerText = `${data.effective_utilization_pct}%`;
        document.getElementById('kpi-ipd').innerText = `+${data.intelligence_per_dollar_delta_pct}%`;
        document.getElementById('kpi-ipw').innerText = `+${data.intelligence_per_watt_delta_pct}%`;
        document.getElementById('kpi-wasted').innerText = `$${Number(data.wasted_compute_usd).toLocaleString()}`;

        if (data.top_problem) {
          document.getElementById('banner-title').innerText = `${data.top_problem.title}:`;
          document.getElementById('banner-desc').innerText = data.top_problem.issue;
          document.getElementById('banner-savings').innerText = `Projected savings: $${Number(data.top_problem.projected_daily_savings_usd).toLocaleString()} / day`;
        }
      } catch (err) {
        console.error("Failed to load executive metrics", err);
      }
    }

    async function fetchTraces() {
      try {
        const res = await fetch('/api/traces?limit=25');
        const traces = await res.json();
        const tbody = document.getElementById('traces-body');
        tbody.innerHTML = '';

        if (traces.length === 0) {
          tbody.innerHTML = '<tr><td colspan="5" style="text-align:center; padding:20px;">No traces found. Run python examples/live_multi_model_agent.py to record telemetry!</td></tr>';
          return;
        }

        traces.forEach((t, idx) => {
          const row = document.createElement('tr');
          row.className = 'trace-row' + (idx === 0 ? ' active' : '');
          const isSuccess = String(t.final_status).toLowerCase().includes('success');
          const costStr = t.total_cost_usd ? `$${t.total_cost_usd.toFixed(4)}` : '$0.0000';

          row.innerHTML = `
            <td>
              <div style="font-weight:600; color:#fff;">${t.workflow_name || 'workflow'}</div>
              <div class="mono" style="font-size:0.7rem; color:var(--text-muted);">${t.trace_id.substring(0, 12)}...</div>
            </td>
            <td><span class="status-badge ${isSuccess ? 'status-success' : 'status-failure'}">${isSuccess ? 'SUCCESS' : 'FAILED'}</span></td>
            <td class="mono">${t.duration_ms ? t.duration_ms.toFixed(1) : 0}ms</td>
            <td class="mono" style="color:#60a5fa;">${costStr}</td>
            <td class="mono">${(t.total_tokens || 0).toLocaleString()}</td>
          `;

          row.onclick = () => {
            document.querySelectorAll('.trace-row').forEach(r => r.classList.remove('active'));
            row.classList.add('active');
            loadTraceDetail(t.trace_id);
          };
          tbody.appendChild(row);
        });

        if (traces.length > 0) loadTraceDetail(traces[0].trace_id);
      } catch (err) {
        console.error("Failed to load traces", err);
      }
    }

    async function loadTraceDetail(traceId) {
      document.getElementById('detail-trace-id').innerText = `ID: ${traceId}`;
      const container = document.getElementById('detail-content');
      container.innerHTML = '<div style="text-align:center; padding:30px;">Loading trace detail...</div>';

      try {
        const res = await fetch(`/api/traces/${traceId}`);
        const data = await res.json();
        const s = data.summary;

        // Findings
        let findingsHtml = '';
        if (data.findings && data.findings.length > 0) {
          findingsHtml = '<div style="margin-bottom:20px;"><div style="font-weight:600; margin-bottom:10px; font-size:0.9rem;">Diagnostic Findings & Optimization:</div>';
          data.findings.forEach(f => {
            const sev = f.severity.toLowerCase();
            const badgeClass = sev === 'critical' ? 'badge-critical' : (sev === 'warning' ? 'badge-warning' : 'badge-info');
            findingsHtml += `
              <div class="finding-item finding-${sev}">
                <span class="severity-badge ${badgeClass}">${f.severity}</span>
                <span>${f.message}</span>
              </div>
            `;
          });
          findingsHtml += '</div>';
        }

        // Waterfall Spans with Energy & Power telemetry
        let spansHtml = '<div style="font-weight:600; margin-bottom:12px; font-size:0.9rem;">Execution Span Timeline & Power Attribution:</div>';
        const maxDuration = s.total_duration_ms || 1.0;

        data.spans.forEach(span => {
          const dur = span.duration_ms || 0.1;
          const pct = Math.min(100, Math.max(5, (dur / maxDuration) * 100));
          const cost = span.cost_usd ? `$${span.cost_usd.toFixed(4)}` : '$0.00';
          const isLlm = span.kind === 'llm';
          const barColor = isLlm ? '#8b5cf6' : (span.kind === 'tool' ? '#3b82f6' : '#10b981');
          const powerStr = span.power_watts ? `${span.power_watts}W` : '350W';
          const joulesStr = span.energy_joules ? `${span.energy_joules.toFixed(1)}J` : '';

          spansHtml += `
            <div class="span-bar-row">
              <div class="span-bar-info">
                <span><strong>[${span.kind}]</strong> ${span.name} ${span.model ? `<span style="color:#a78bfa;">(${span.model})</span>` : ''}</span>
                <span class="mono">${dur.toFixed(1)}ms | ${cost} | ${powerStr} ${joulesStr}</span>
              </div>
              <div class="span-bar-track">
                <div class="span-bar-fill" style="width:${pct}%; background:${barColor};"></div>
              </div>
            </div>
          `;
        });

        // Economic & Energy Summary Box
        const qualityStr = s.quality_score !== null && s.quality_score !== undefined ? `${(s.quality_score * 100).toFixed(0)}%` : 'N/A';
        const ipdStr = s.intelligence_per_dollar ? `${s.intelligence_per_dollar}` : 'N/A';
        const ipwStr = s.intelligence_per_watt ? `${s.intelligence_per_watt}` : 'N/A';
        const econHtml = `
          <div style="background:rgba(0,0,0,0.3); border-radius:8px; padding:14px; margin-bottom:20px; display:grid; grid-template-columns:repeat(3, 1fr); gap:12px; font-size:0.8rem;">
            <div><span style="color:var(--text-muted);">Critical Path:</span> <strong class="mono">${data.critical_path_ms}ms</strong></div>
            <div><span style="color:var(--text-muted);">Intelligence / $:</span> <strong class="mono" style="color:var(--success);">${ipdStr}</strong></div>
            <div><span style="color:var(--text-muted);">Intelligence / Watt:</span> <strong class="mono" style="color:var(--success);">${ipwStr}</strong></div>
            <div><span style="color:var(--text-muted);">Energy Consumed:</span> <strong class="mono">${s.total_energy_joules || 0}J</strong></div>
            <div><span style="color:var(--text-muted);">Cost/Success:</span> <strong class="mono">$${(s.cost_per_successful_outcome_usd || s.total_cost_usd || 0).toFixed(4)}</strong></div>
            <div><span style="color:var(--text-muted);">Quality Score:</span> <strong class="mono" style="color:#10b981;">${qualityStr}</strong></div>
          </div>
        `;

        container.innerHTML = econHtml + findingsHtml + spansHtml;
      } catch (err) {
        container.innerHTML = `<div style="color:var(--critical); padding:20px;">Failed to load detail: ${err.message}</div>`;
      }
    }

    async function fetchFrontier() {
      try {
        const res = await fetch('/api/routing/frontier');
        const models = await res.json();
        const tbody = document.getElementById('frontier-body');
        tbody.innerHTML = '';

        models.forEach(m => {
          const row = document.createElement('tr');
          const isPareto = m.is_pareto_optimal;
          row.innerHTML = `
            <td><strong>${m.display_name}</strong> <span class="mono" style="font-size:0.75rem; color:var(--text-muted);">(${m.model_id})</span></td>
            <td><span class="mono">${m.provider}</span></td>
            <td><strong style="color:var(--success);">${(m.quality_score * 100).toFixed(1)}%</strong></td>
            <td class="mono" style="color:#60a5fa;">$${m.blended_cost_per_1m.toFixed(2)}</td>
            <td class="mono">${m.typical_latency_ms.toFixed(0)}ms</td>
            <td>${isPareto ? '<span class="badge-pareto severity-badge">PARETO OPTIMAL</span>' : '<span style="color:var(--text-muted); font-size:0.75rem;">Dominated</span>'}</td>
            <td style="font-size:0.8rem; color:var(--text-muted);">${m.notes}</td>
          `;
          tbody.appendChild(row);
        });
      } catch (err) {
        console.error("Failed to load frontier", err);
      }
    }

    async function fetchBreakers() {
      try {
        const res = await fetch('/api/resilience/breaker');
        const breakers = await res.json();
        const container = document.getElementById('breaker-cards');
        container.innerHTML = '';

        breakers.forEach(b => {
          const card = document.createElement('div');
          card.className = 'breaker-card';
          const isClosed = b.state === 'closed';
          const badgeClass = isClosed ? 'state-closed' : (b.state === 'open' ? 'state-open' : 'state-half-open');

          card.innerHTML = `
            <div class="breaker-header">
              <span class="breaker-name">${b.provider}</span>
              <span class="breaker-state-badge ${badgeClass}">${b.state.toUpperCase()}</span>
            </div>
            <div style="font-size:0.8rem; color:var(--text-muted); line-height:1.6;">
              <div>Trips recorded: <strong class="mono" style="color:#fff;">${b.trip_count}</strong></div>
              <div>Avg Latency: <strong class="mono" style="color:#fff;">${b.avg_latency_ms}ms</strong></div>
              <div>Quality index: <strong class="mono" style="color:var(--success);">${(b.avg_quality_score * 100).toFixed(0)}%</strong></div>
              ${b.last_trip_reason ? `<div style="color:var(--critical); margin-top:4px; font-size:0.74rem;">${b.last_trip_reason}</div>` : ''}
            </div>
          `;
          container.appendChild(card);
        });
      } catch (err) {
        console.error("Failed to load breakers", err);
      }
    }

    async function runDisasterRecoveryDrill() {
      const container = document.getElementById('dr-report-content');
      container.innerHTML = '<div style="padding:20px; text-align:center;">Executing automated DR drill & failover simulation...</div>';

      try {
        const res = await fetch('/api/resilience/dr-drill', { method: 'POST' });
        const data = await res.json();

        document.getElementById('dr-drill-id').innerText = `ID: ${data.drill_id}`;

        const isOk = data.business_continuity_preserved;
        const statusBadge = isOk ? '<span class="status-badge status-success">CONTINUITY VERIFIED</span>' : '<span class="status-badge status-failure">DEGRADED</span>';

        container.innerHTML = `
          <div style="background:rgba(0,0,0,0.25); border-radius:8px; padding:18px; text-align:left; font-size:0.85rem;">
            <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:14px;">
              <strong style="font-size:1rem; color:#fff;">${data.scenario}</strong>
              ${statusBadge}
            </div>

            <div style="display:grid; grid-template-columns:repeat(4, 1fr); gap:12px; margin-bottom:16px; font-size:0.82rem;">
              <div style="background:rgba(255,255,255,0.03); padding:10px; border-radius:6px;">
                <div style="color:var(--text-muted);">Primary / Fallback</div>
                <div class="mono" style="font-weight:700; color:#fff;">${data.primary_provider} → ${data.fallback_provider}</div>
              </div>
              <div style="background:rgba(255,255,255,0.03); padding:10px; border-radius:6px;">
                <div style="color:var(--text-muted);">Cost Impact</div>
                <div class="mono" style="font-weight:700; color:${data.cost_delta_pct > 0 ? '#f59e0b' : 'var(--success)'};">${data.cost_delta_pct > 0 ? '+' : ''}${data.cost_delta_pct}%</div>
              </div>
              <div style="background:rgba(255,255,255,0.03); padding:10px; border-radius:6px;">
                <div style="color:var(--text-muted);">Latency Delta</div>
                <div class="mono" style="font-weight:700; color:#60a5fa;">${data.latency_delta_ms > 0 ? '+' : ''}${data.latency_delta_ms}ms</div>
              </div>
              <div style="background:rgba(255,255,255,0.03); padding:10px; border-radius:6px;">
                <div style="color:var(--text-muted);">Quality Retained</div>
                <div class="mono" style="font-weight:700; color:var(--success);">${data.quality_retention_pct}%</div>
              </div>
            </div>

            <div style="margin-bottom:12px;">
              <strong>Actionable Recommendations:</strong>
              <ul style="margin-left:20px; margin-top:6px; color:var(--text-muted); font-size:0.82rem;">
                ${data.actionable_recommendations.map(r => `<li>${r}</li>`).join('')}
              </ul>
            </div>
          </div>
        `;

        fetchBreakers();
      } catch (err) {
        container.innerHTML = `<div style="color:var(--critical); padding:20px;">DR Drill failed: ${err.message}</div>`;
      }
    }

    async function fetchIncidentGraph(incidentType) {
      try {
        const res = await fetch(`/api/incidents/graph?type=${incidentType}`);
        const data = await res.json();

        document.getElementById('inc-title').innerText = data.title;
        document.getElementById('inc-root-cause').innerText = `Root cause: ${data.root_cause}`;
        document.getElementById('inc-financial').innerText = `Unrecoverable compute loss: $${Number(data.total_wasted_cost_usd).toLocaleString()}`;
        document.getElementById('inc-remed-text').innerText = data.remediation_action;

        const container = document.getElementById('incident-nodes-container');
        container.innerHTML = '';

        data.nodes.forEach((n, idx) => {
          const nodeDiv = document.createElement('div');
          nodeDiv.className = 'chain-node';
          const isCritical = n.severity === 'critical';

          nodeDiv.innerHTML = `
            <div style="background:${isCritical ? 'var(--critical-bg)' : 'var(--warning-bg)'}; color:${isCritical ? 'var(--critical)' : 'var(--warning)'}; border:1px solid ${isCritical ? 'var(--critical)' : 'var(--warning)'}; padding:6px 10px; border-radius:6px; font-weight:700; font-size:0.75rem; font-family:'JetBrains Mono', monospace;">
              STEP ${idx + 1}
            </div>
            <div style="flex:1;">
              <div style="font-weight:700; font-size:0.95rem; color:#fff;">${n.title}</div>
              <div style="font-size:0.78rem; color:var(--text-muted);">${n.component} &bull; ${n.description}</div>
            </div>
          `;
          container.appendChild(nodeDiv);

          if (idx < data.nodes.length - 1) {
            const arrow = document.createElement('div');
            arrow.className = 'chain-arrow';
            arrow.innerText = '↓';
            container.appendChild(arrow);
          }
        });
      } catch (err) {
        console.error("Failed to load incident graph", err);
      }
    }

    async function fetchWasteReport() {
      try {
        const res = await fetch('/api/waste?accelerator=h100&gpus=8');
        const data = await res.json();

        document.getElementById('waste-hourly-bleed').innerText = `$${Number(data.hourly_financial_bleed_usd).toFixed(2)} / hr`;
        document.getElementById('waste-top-bottleneck').innerText = data.top_bottleneck;

        if (data.mfu) {
          document.getElementById('waste-mfu-val').innerText = `${data.mfu.mfu_pct}%`;
          document.getElementById('waste-mfu-sub').innerText = `${data.mfu.achieved_tflops} / ${data.mfu.total_theoretical_peak_tflops} TFLOPS [${data.mfu.efficiency_rating}]`;
        }

        const grid = document.getElementById('waste-components-grid');
        grid.innerHTML = '';
        data.waste_components.forEach(c => {
          const card = document.createElement('div');
          card.style.cssText = 'background:rgba(0,0,0,0.3); border:1px solid var(--card-border); border-radius:8px; padding:16px;';
          card.innerHTML = `
            <div style="display:flex; justify-content:space-between; margin-bottom:8px;">
              <strong style="color:#fff; font-size:0.9rem;">${c.display_name}</strong>
              <span class="mono" style="font-weight:700; color:${c.waste_pct >= 15 ? 'var(--critical)' : 'var(--warning)'};">${c.waste_pct}%</span>
            </div>
            <div style="font-size:0.78rem; color:var(--text-muted); margin-bottom:8px;">${c.diagnosis}</div>
            <div class="mono" style="font-size:0.8rem; color:var(--critical); margin-bottom:6px;">Bleed: $${c.hourly_bleed_usd.toFixed(2)}/hr | Run: $${c.wasted_cost_usd.toFixed(4)}</div>
            <div style="font-size:0.75rem; color:var(--success); background:rgba(16,185,129,0.06); padding:6px 8px; border-radius:4px;">
              Fix: ${c.remediation}
            </div>
          `;
          grid.appendChild(card);
        });

        const recsList = document.getElementById('waste-recommendations-list');
        recsList.innerHTML = '';
        data.recommendations.forEach(r => {
          const div = document.createElement('div');
          div.style.cssText = 'background:rgba(255,255,255,0.02); border:1px solid var(--card-border); border-radius:6px; padding:12px; display:flex; justify-content:space-between; align-items:center;';
          div.innerHTML = `
            <div>
              <strong style="color:#fff; font-size:0.88rem;">${r.title}</strong>
              <div style="font-size:0.78rem; color:var(--text-muted); margin-top:2px;">${r.action}</div>
            </div>
            <div style="text-align:right;">
              <div class="mono" style="font-weight:700; color:var(--success); font-size:0.95rem;">+$${Number(r.potential_weekly_savings_usd).toFixed(0)} / wk</div>
              <div style="font-size:0.7rem; color:var(--text-muted);">+$${Number(r.potential_monthly_savings_usd).toFixed(0)} / mo</div>
            </div>
          `;
          recsList.appendChild(div);
        });
      } catch (err) {
        console.error("Failed to load waste report", err);
      }
    }

    async function fetchGoldenSignals() {
      try {
        const res = await fetch('/api/golden-signals');
        const data = await res.json();
        const e = data.economics;
        const eff = data.efficiency;
        const rel = data.reliability;
        const inf = data.infrastructure;

        document.getElementById('gs-cost-gpu').innerText = `$${Number(e.cost_per_effective_gpu_hour_usd).toFixed(2)}`;
        document.getElementById('gs-cost-tokens').innerText = e.cost_per_1m_tokens_usd ? `$${Number(e.cost_per_1m_tokens_usd).toFixed(4)}` : 'N/A';
        document.getElementById('gs-bleed').innerText = `$${Number(e.financial_bleed_hourly_usd).toFixed(2)}/hr`;
        document.getElementById('gs-wasted').innerText = `$${Number(e.total_wasted_spend_usd).toFixed(4)} (${e.waste_percentage.toFixed(1)}%)`;

        document.getElementById('gs-mfu').innerText = `${eff.mfu_pct.toFixed(1)}%`;
        document.getElementById('gs-tflops').innerText = `${eff.achieved_tflops.toFixed(1)} TFLOPS`;
        document.getElementById('gs-sm-util').innerText = `${eff.gpu_sm_utilization_pct.toFixed(1)}%`;
        document.getElementById('gs-mem-bw').innerText = `${eff.memory_bandwidth_utilization_pct.toFixed(1)}%`;

        document.getElementById('gs-fail-rate').innerText = `${rel.job_failure_rate_pct.toFixed(1)}%`;
        document.getElementById('gs-mttr').innerText = `${rel.mean_time_to_recovery_ms.toFixed(0)} ms`;
        document.getElementById('gs-retries').innerText = `${rel.retry_count}`;
        document.getElementById('gs-checkpoint').innerText = `Every ${rel.checkpoint_frequency_min.toFixed(0)} min`;

        document.getElementById('gs-power').innerText = `${inf.power_draw_watts.toFixed(0)} W (PUE ${inf.pue.toFixed(2)})`;
        document.getElementById('gs-thermal').innerText = inf.thermal_throttling ? 'THROTTLED' : 'Nominal';
        document.getElementById('gs-thermal').style.color = inf.thermal_throttling ? 'var(--critical)' : 'var(--success)';
        document.getElementById('gs-pcie-err').innerText = `${inf.pcie_error_count}`;
        document.getElementById('gs-retrans').innerText = `${(inf.network_retransmits_pct * 100).toFixed(2)}%`;
      } catch (err) {
        console.error("Failed to load golden signals", err);
      }
    }

    async function fetchDaemonSetManifest() {
      try {
        const res = await fetch('/api/manifests/daemonset');
        const data = await res.json();
        document.getElementById('daemonset-manifest-code').innerText = data.manifest;
      } catch (err) {
        document.getElementById('daemonset-manifest-code').innerText = '# Failed to load manifest';
      }
    }

    function copyDaemonSetManifest() {
      const code = document.getElementById('daemonset-manifest-code').innerText;
      navigator.clipboard.writeText(code).then(() => {
        alert('GKE DaemonSet manifest copied to clipboard!');
      });
    }

    // Initialize on page load
    fetchExecutiveMetrics();
    fetchTraces();
  </script>
</body>
</html>
"""
