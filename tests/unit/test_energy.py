"""Unit tests for AI hardware accelerator energy and power modeling engine."""

from airun.pricing.energy import (
    ACCELERATOR_CATALOG,
    calculate_energy,
    calculate_intelligence_per_dollar,
    calculate_intelligence_per_watt,
    calculate_tokens_per_dollar,
    calculate_tokens_per_kwh,
    get_accelerator_profile,
)


def test_accelerator_catalog_profiles():
    """Verify hardware accelerator specifications."""
    assert "h100" in ACCELERATOR_CATALOG
    assert "a100" in ACCELERATOR_CATALOG
    assert "b200" in ACCELERATOR_CATALOG
    assert "tpu_v5e" in ACCELERATOR_CATALOG

    h100 = ACCELERATOR_CATALOG["h100"]
    assert h100.tdp_watts == 700.0
    assert h100.idle_watts == 120.0
    assert "HBM3" in h100.memory_type


def test_get_accelerator_profile_fallback():
    """Verify fallback matching for accelerator names."""
    prof = get_accelerator_profile("nvidia-h100-sxm5")
    assert prof.name == "NVIDIA H100 SXM5"

    unknown = get_accelerator_profile("some_unknown_chip")
    assert unknown.name == "Generic Cloud AI Accelerator"


def test_calculate_energy_metrics():
    """Verify dynamic power, Joules, kWh, and cost calculations."""
    metrics = calculate_energy(
        duration_ms=1000.0, accelerator="h100", utilization_pct=1.0, pue=1.20
    )
    # Power at 100% load: 700W * 1.20 PUE = 840W
    assert metrics.power_watts == 840.0
    # 1 second = 840 Joules
    assert metrics.energy_joules == 840.0
    # kWh = 840 / 3,600,000 = 0.00023333 kWh
    assert abs(metrics.energy_kwh - (840.0 / 3_600_000.0)) < 1e-6
    assert metrics.energy_cost_usd > 0.0
    assert metrics.carbon_co2_grams > 0.0


def test_intelligence_per_dollar():
    """Verify IPD calculation formula."""
    ipd = calculate_intelligence_per_dollar(
        quality_score=0.95,
        successful_outcomes=1.0,
        total_cost_usd=0.01,
        energy_cost_usd=0.001,
    )
    assert ipd is not None
    # 0.95 / 0.011 = 86.36
    assert ipd == 86.36

    # Zero cost returns None
    assert calculate_intelligence_per_dollar(0.9, 1.0, 0.0, 0.0) is None


def test_intelligence_per_watt():
    """Verify IPW calculation formula."""
    ipw = calculate_intelligence_per_watt(
        quality_score=0.90,
        successful_outcomes=1.0,
        energy_kwh=0.0001,
    )
    assert ipw is not None
    assert ipw == 9000.0

    assert calculate_intelligence_per_watt(0.9, 1.0, 0.0) is None


def test_tokens_per_dollar_and_kwh():
    """Verify token efficiency ratios."""
    tok_usd = calculate_tokens_per_dollar(total_tokens=10000, total_cost_usd=0.02)
    assert tok_usd == 500000.0

    tok_kwh = calculate_tokens_per_kwh(total_tokens=10000, energy_kwh=0.001)
    assert tok_kwh == 10000000.0
