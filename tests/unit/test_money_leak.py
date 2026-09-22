"""Tests for Money Leak analysis and executive report generation."""

from airun.analysis.money_leak import compute_money_leak_report
from airun.exporters.html_report import generate_money_leak_html


def test_compute_money_leak_report_default():
    report = compute_money_leak_report(monthly_spend_usd=184_720.0)

    assert report.monthly_spend_usd == 184_720.0
    assert report.recoverable_waste_usd > 30_000.0
    assert 15.0 <= report.recoverable_waste_pct <= 35.0
    assert len(report.top_leaks) >= 5

    categories = [item.category for item in report.top_leaks]
    assert "GPU starvation" in categories
    assert "oversized model selection" in categories
    assert "redundant agent/tool calls" in categories
    assert "KV-cache misses" in categories

    assert report.projected_monthly_savings_usd > 5_000.0
    assert "Route low-complexity" in report.top_recommendation


def test_generate_money_leak_html():
    report = compute_money_leak_report()
    html = generate_money_leak_html(report)

    assert "<!DOCTYPE html>" in html
    assert "AIRUN MONEY LEAK AUDIT REPORT" in html
    assert f"${report.monthly_spend_usd:,.2f}" in html
    assert f"${report.recoverable_waste_usd:,.2f}" in html
    assert "GPU starvation" in html
