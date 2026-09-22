"""Standalone HTML Executive Report Generator for airun.

Produces responsive, self-contained, dark-theme HTML executive reports with
zero external CDN or JavaScript dependencies.
"""

from __future__ import annotations

from airun.analysis.diagnose import TraceDiagnostic
from airun.analysis.money_leak import MoneyLeakReport


def generate_money_leak_html(report: MoneyLeakReport) -> str:
    """Generate standalone HTML report for airun money-leak."""
    leak_rows = ""
    for item in report.top_leaks:
        leak_rows += f"""
        <tr>
            <td style="font-weight: 600; color: #f0f6fc;">{item.category}</td>
            <td style="color: #f85149; font-weight: bold; text-align: right;">${item.amount_usd:,.2f}</td>
            <td style="text-align: right; color: #8b949e;">{item.percentage_of_waste:.1f}%</td>
            <td style="color: #c9d1d9; font-size: 0.9em;">{item.explanation}</td>
            <td style="color: #3fb950; font-size: 0.9em;">{item.remediation}</td>
        </tr>
        """

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>AIRUN MONEY LEAK AUDIT REPORT</title>
    <style>
        body {{
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
            background-color: #0d1117;
            color: #c9d1d9;
            margin: 0;
            padding: 32px 16px;
        }}
        .container {{
            max-width: 1080px;
            margin: 0 auto;
        }}
        .header {{
            border-bottom: 1px solid #30363d;
            padding-bottom: 24px;
            margin-bottom: 32px;
        }}
        .title {{
            font-size: 28px;
            font-weight: 700;
            color: #f0f6fc;
            margin: 0 0 8px 0;
            display: flex;
            align-items: center;
            gap: 12px;
        }}
        .badge {{
            font-size: 13px;
            padding: 4px 10px;
            border-radius: 12px;
            font-weight: 600;
            background-color: #f8514922;
            color: #f85149;
            border: 1px solid #f8514955;
        }}
        .grid-cards {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(240px, 1fr));
            gap: 20px;
            margin-bottom: 32px;
        }}
        .card {{
            background: #161b22;
            border: 1px solid #30363d;
            border-radius: 8px;
            padding: 20px;
        }}
        .card-label {{
            font-size: 13px;
            color: #8b949e;
            text-transform: uppercase;
            letter-spacing: 0.05em;
            margin-bottom: 8px;
        }}
        .card-value {{
            font-size: 32px;
            font-weight: 700;
            color: #f0f6fc;
        }}
        .card-value.red {{ color: #f85149; }}
        .card-value.green {{ color: #3fb950; }}
        .card-subtext {{
            font-size: 13px;
            color: #8b949e;
            margin-top: 6px;
        }}
        .recommendation-box {{
            background: #1f6feb15;
            border: 1px solid #1f6feb66;
            border-radius: 8px;
            padding: 20px;
            margin-bottom: 32px;
        }}
        .rec-title {{
            font-size: 16px;
            font-weight: 700;
            color: #58a6ff;
            margin-bottom: 8px;
        }}
        .rec-desc {{
            font-size: 15px;
            color: #f0f6fc;
        }}
        table {{
            width: 100%;
            border-collapse: collapse;
            background: #161b22;
            border: 1px solid #30363d;
            border-radius: 8px;
            overflow: hidden;
            margin-bottom: 32px;
        }}
        th, td {{
            padding: 14px 16px;
            text-align: left;
            border-bottom: 1px solid #21262d;
        }}
        th {{
            background: #21262d;
            color: #8b949e;
            font-weight: 600;
            font-size: 13px;
            text-transform: uppercase;
            letter-spacing: 0.05em;
        }}
        tr:last-child td {{ border-bottom: none; }}
        tr:hover td {{ background: #1c2128; }}
        .footer {{
            text-align: center;
            font-size: 12px;
            color: #8b949e;
            margin-top: 48px;
            border-top: 1px solid #21262d;
            padding-top: 20px;
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <div class="title">
                <span>airun Financial Bleed & Money Leak Audit</span>
                <span class="badge">RECOVERABLE WASTE DETECTED</span>
            </div>
            <div style="color: #8b949e; font-size: 14px;">Enterprise AI Infrastructure Resource Optimization Report</div>
        </div>

        <div class="grid-cards">
            <div class="card">
                <div class="card-label">Monthly AI Infra Spend</div>
                <div class="card-value">${report.monthly_spend_usd:,.2f}</div>
                <div class="card-subtext">Estimated compute & cluster footprint</div>
            </div>
            <div class="card">
                <div class="card-label">Recoverable Waste</div>
                <div class="card-value red">${report.recoverable_waste_usd:,.2f}</div>
                <div class="card-subtext">{report.recoverable_waste_pct:.1f}% total spend wasted</div>
            </div>
            <div class="card">
                <div class="card-label">Projected Monthly Savings</div>
                <div class="card-value green">${report.projected_monthly_savings_usd:,.2f}</div>
                <div class="card-subtext">Via top actionable recommendation</div>
            </div>
            <div class="card">
                <div class="card-label">Monitored Traces</div>
                <div class="card-value">{report.traces_analyzed}</div>
                <div class="card-subtext">Multi-agent execution samples</div>
            </div>
        </div>

        <div class="recommendation-box">
            <div class="rec-title">★ TOP ACTIONABLE RECOMMENDATION</div>
            <div class="rec-desc"><strong>{report.top_recommendation}</strong> — Projected immediate recovery: <strong style="color: #3fb950;">${report.projected_monthly_savings_usd:,.2f}/month</strong>.</div>
        </div>

        <div style="font-size: 18px; font-weight: 700; color: #f0f6fc; margin-bottom: 16px;">
            Physics of AI Waste Breakdown
        </div>
        <table>
            <thead>
                <tr>
                    <th>Leak Category</th>
                    <th style="text-align: right;">Monthly Bleed</th>
                    <th style="text-align: right;">% Waste</th>
                    <th>Root Cause</th>
                    <th>Actionable Remediation</th>
                </tr>
            </thead>
            <tbody>
                {leak_rows}
            </tbody>
        </table>

        <div class="footer">
            Generated by <strong>airun</strong> — AI Infrastructure Reliability & Economics Platform.
        </div>
    </div>
</body>
</html>
"""


def generate_diagnostic_html(diagnostic: TraceDiagnostic) -> str:
    """Generate standalone HTML report for airun diagnose."""
    evidence_items = "".join(f"<li>{item}</li>" for item in diagnostic.evidence)
    recommendations_items = "".join(
        f"<li><strong>{item}</strong></li>" for item in diagnostic.recommendations
    )

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>AIRUN DIAGNOSTIC — {diagnostic.workflow_name}</title>
    <style>
        body {{
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
            background-color: #0d1117;
            color: #c9d1d9;
            margin: 0;
            padding: 32px 16px;
        }}
        .container {{
            max-width: 960px;
            margin: 0 auto;
        }}
        .header {{
            border-bottom: 1px solid #30363d;
            padding-bottom: 20px;
            margin-bottom: 24px;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }}
        .title {{ font-size: 24px; font-weight: 700; color: #f0f6fc; }}
        .badge {{
            font-size: 13px;
            padding: 4px 12px;
            border-radius: 12px;
            font-weight: 600;
            background: #f8514922;
            color: #f85149;
            border: 1px solid #f8514955;
        }}
        .meta-grid {{
            display: grid;
            grid-template-columns: repeat(4, 1fr);
            gap: 12px;
            margin-bottom: 24px;
        }}
        .meta-box {{
            background: #161b22;
            border: 1px solid #30363d;
            border-radius: 6px;
            padding: 12px 16px;
        }}
        .meta-label {{ font-size: 11px; color: #8b949e; text-transform: uppercase; }}
        .meta-val {{ font-size: 18px; font-weight: 700; color: #f0f6fc; margin-top: 4px; }}
        .section {{
            background: #161b22;
            border: 1px solid #30363d;
            border-radius: 8px;
            padding: 20px;
            margin-bottom: 20px;
        }}
        .section-title {{
            font-size: 14px;
            font-weight: 700;
            color: #8b949e;
            text-transform: uppercase;
            letter-spacing: 0.05em;
            margin-bottom: 12px;
        }}
        .root-cause {{ font-size: 22px; font-weight: 700; color: #f85149; }}
        ul {{ margin: 0; padding-left: 20px; }}
        li {{ margin-bottom: 8px; font-size: 14px; color: #f0f6fc; }}
        .impact-grid {{
            display: grid;
            grid-template-columns: repeat(3, 1fr);
            gap: 16px;
        }}
        .impact-card {{
            background: #0d1117;
            border: 1px solid #30363d;
            border-radius: 6px;
            padding: 14px;
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <div>
                <div class="title">AIRUN DIAGNOSTIC: {diagnostic.workflow_name}</div>
                <div style="font-size: 13px; color: #8b949e; margin-top: 4px;">Trace ID: <code>{diagnostic.trace_id}</code></div>
            </div>
            <div class="badge">{diagnostic.gpu_efficiency.rating}</div>
        </div>

        <div class="meta-grid">
            <div class="meta-box"><div class="meta-label">Duration</div><div class="meta-val">{diagnostic.duration_sec:.2f}s</div></div>
            <div class="meta-box"><div class="meta-label">Cost / Request</div><div class="meta-val">${diagnostic.cost_per_request_usd:.4f}</div></div>
            <div class="meta-box"><div class="meta-label">Accelerator</div><div class="meta-val">{diagnostic.accelerator}</div></div>
            <div class="meta-box"><div class="meta-label">GPU Score</div><div class="meta-val">{diagnostic.gpu_efficiency.score}/100</div></div>
            <div class="meta-box"><div class="meta-label">GPU Util</div><div class="meta-val">{diagnostic.gpu_utilization_pct:.1f}%</div></div>
            <div class="meta-box"><div class="meta-label">SM Active</div><div class="meta-val">{diagnostic.sm_active_pct:.1f}%</div></div>
            <div class="meta-box"><div class="meta-label">PCIe RX</div><div class="meta-val">{diagnostic.pcie_rx_gbs:.1f} GB/s</div></div>
            <div class="meta-box"><div class="meta-label">CPU Util</div><div class="meta-val">{diagnostic.cpu_utilization_pct:.1f}%</div></div>
        </div>

        <div class="section" style="border-left: 4px solid #f85149;">
            <div class="section-title">Root Cause</div>
            <div class="root-cause">{diagnostic.root_cause}</div>
        </div>

        <div class="section">
            <div class="section-title">Telemetry Evidence</div>
            <ul>{evidence_items}</ul>
        </div>

        <div class="section">
            <div class="section-title">Financial Impact</div>
            <div class="impact-grid">
                <div class="impact-card">
                    <div class="meta-label">Current Cost / Request</div>
                    <div class="meta-val">${diagnostic.current_cost_per_request_usd:.4f}</div>
                </div>
                <div class="impact-card">
                    <div class="meta-label">Estimated Waste / Request</div>
                    <div class="meta-val" style="color: #f85149;">${diagnostic.estimated_waste_per_request_usd:.4f} ({diagnostic.waste_percentage:.1f}%)</div>
                </div>
                <div class="impact-card">
                    <div class="meta-label">Monthly Waste Bleed</div>
                    <div class="meta-val" style="color: #f85149;">${diagnostic.monthly_waste_usd:,.2f}</div>
                </div>
            </div>
        </div>

        <div class="section">
            <div class="section-title">Actionable Recommendation</div>
            <ul style="color: #3fb950;">{recommendations_items}</ul>
        </div>

        <div class="section">
            <div class="section-title">Expected Result</div>
            <div class="impact-grid">
                <div class="impact-card">
                    <div class="meta-label">GPU Utilization</div>
                    <div class="meta-val" style="color: #3fb950;">{diagnostic.expected_result.get("gpu_utilization", "N/A")}</div>
                </div>
                <div class="impact-card">
                    <div class="meta-label">Cost / Request</div>
                    <div class="meta-val" style="color: #3fb950;">{diagnostic.expected_result.get("cost_per_request", "N/A")}</div>
                </div>
                <div class="impact-card">
                    <div class="meta-label">Throughput Gain</div>
                    <div class="meta-val" style="color: #3fb950;">{diagnostic.expected_result.get("throughput", "N/A")}</div>
                </div>
            </div>
        </div>
    </div>
</body>
</html>
"""
