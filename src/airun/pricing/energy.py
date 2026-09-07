"""Energy and power economics engine for AI accelerators and workloads.

Calculates accelerator power draw, energy consumption (Joules, kWh), data center PUE,
electricity cost, carbon emissions, and killer economic efficiency metrics:
- Intelligence per Dollar (IPD)
- Intelligence per Watt (IPW)
- Tokens per Dollar
- Tokens per kWh
"""

from __future__ import annotations

from typing import Dict, Optional

from pydantic import BaseModel, Field


class AcceleratorProfile(BaseModel):
    """Thermal, electrical, and memory specification for an AI accelerator."""

    name: str
    tdp_watts: float
    idle_watts: float
    typical_load_pct: float = 0.75
    memory_type: str = "HBM"
    description: str = ""


# Industry-standard hardware accelerator power specifications
ACCELERATOR_CATALOG: Dict[str, AcceleratorProfile] = {
    "h100": AcceleratorProfile(
        name="NVIDIA H100 SXM5",
        tdp_watts=700.0,
        idle_watts=120.0,
        typical_load_pct=0.75,
        memory_type="HBM3 (80GB)",
        description="Flagship frontier AI training and inference accelerator",
    ),
    "h100_pcie": AcceleratorProfile(
        name="NVIDIA H100 PCIe",
        tdp_watts=350.0,
        idle_watts=80.0,
        typical_load_pct=0.70,
        memory_type="HBM3 (80GB)",
        description="Enterprise PCIe form-factor H100",
    ),
    "a100": AcceleratorProfile(
        name="NVIDIA A100 SXM4",
        tdp_watts=400.0,
        idle_watts=80.0,
        typical_load_pct=0.70,
        memory_type="HBM2e (80GB)",
        description="Standard enterprise deep learning workhorse",
    ),
    "b200": AcceleratorProfile(
        name="NVIDIA B200 Blackwell",
        tdp_watts=1000.0,
        idle_watts=200.0,
        typical_load_pct=0.80,
        memory_type="HBM3e (192GB)",
        description="Next-generation exascale frontier AI accelerator",
    ),
    "l40s": AcceleratorProfile(
        name="NVIDIA L40S",
        tdp_watts=350.0,
        idle_watts=70.0,
        typical_load_pct=0.70,
        memory_type="GDDR6 (48GB)",
        description="Optimized for LLM inference and multimodal workloads",
    ),
    "tpu_v5e": AcceleratorProfile(
        name="Google TPU v5e",
        tdp_watts=250.0,
        idle_watts=50.0,
        typical_load_pct=0.70,
        memory_type="HBM2 (16GB)",
        description="Cost-efficient Google Cloud custom AI ASIC",
    ),
    "mi300x": AcceleratorProfile(
        name="AMD Instinct MI300X",
        tdp_watts=750.0,
        idle_watts=150.0,
        typical_load_pct=0.75,
        memory_type="HBM3 (192GB)",
        description="High-capacity open-ecosystem generative AI accelerator",
    ),
    "apple_silicon": AcceleratorProfile(
        name="Apple M-Series Neural Engine",
        tdp_watts=35.0,
        idle_watts=5.0,
        typical_load_pct=0.55,
        memory_type="Unified Memory",
        description="Local on-device inference for edge AI and local models",
    ),
    "generic_cloud": AcceleratorProfile(
        name="Generic Cloud AI Accelerator",
        tdp_watts=300.0,
        idle_watts=60.0,
        typical_load_pct=0.70,
        memory_type="Shared GPU VRAM",
        description="Default cloud inference endpoint allocation",
    ),
    "cpu": AcceleratorProfile(
        name="Host Server CPU",
        tdp_watts=65.0,
        idle_watts=15.0,
        typical_load_pct=0.50,
        memory_type="System RAM",
        description="CPU fallback inference or pre-processing",
    ),
}

# Average US Data Center PUE (Power Usage Effectiveness)
DEFAULT_PUE = 1.20

# Industrial electricity rate per kWh (USD)
DEFAULT_ELECTRICITY_RATE_PER_KWH = 0.10

# Average grid carbon intensity (grams CO2 per kWh)
DEFAULT_GRID_CARBON_INTENSITY = 385.0


class EnergyMetrics(BaseModel):
    """Calculated power, energy, carbon, and cost metrics for an execution."""

    accelerator: str
    power_watts: float
    energy_joules: float
    energy_kwh: float
    energy_cost_usd: float
    carbon_co2_grams: float
    pue: float = Field(default=DEFAULT_PUE)


def get_accelerator_profile(accelerator_name: Optional[str]) -> AcceleratorProfile:
    """Resolve an accelerator name or return generic cloud profile."""
    if not accelerator_name:
        return ACCELERATOR_CATALOG["generic_cloud"]

    normalized = accelerator_name.lower().strip().replace("-", "_").replace(" ", "_")
    if normalized in ACCELERATOR_CATALOG:
        return ACCELERATOR_CATALOG[normalized]

    # Partial match fallback
    for key, profile in ACCELERATOR_CATALOG.items():
        if key in normalized or normalized in key:
            return profile

    return ACCELERATOR_CATALOG["generic_cloud"]


def calculate_energy(
    duration_ms: float,
    accelerator: Optional[str] = None,
    utilization_pct: Optional[float] = None,
    pue: float = DEFAULT_PUE,
    electricity_rate_kwh: float = DEFAULT_ELECTRICITY_RATE_PER_KWH,
) -> EnergyMetrics:
    """
    Calculate electrical energy consumption and cost for a workload step.

    Parameters:
    - duration_ms: Wall-clock execution time in milliseconds.
    - accelerator: Name of accelerator (e.g., 'h100', 'a100', 'tpu_v5e', 'apple_silicon').
    - utilization_pct: Active compute load percentage (0.0 to 1.0). If None, uses typical load.
    - pue: Power Usage Effectiveness of data center facility (e.g. 1.15 to 1.35).
    - electricity_rate_kwh: Utility rate per kilowatt-hour in USD.
    """
    profile = get_accelerator_profile(accelerator)
    load = utilization_pct if utilization_pct is not None else profile.typical_load_pct
    load = max(0.0, min(1.0, load))

    # Dynamic power = idle + load * (tdp - idle)
    power_watts = profile.idle_watts + load * (profile.tdp_watts - profile.idle_watts)

    # Total facility power factoring in cooling, power supply overhead via PUE
    facility_power_watts = power_watts * pue

    # Energy in Joules: Power (Watts) * Time (Seconds)
    duration_seconds = max(0.0, duration_ms) / 1000.0
    energy_joules = facility_power_watts * duration_seconds

    # Energy in kWh: Joules / 3,600,000
    energy_kwh = energy_joules / 3_600_000.0

    # Electricity cost
    energy_cost_usd = energy_kwh * electricity_rate_kwh

    # Carbon emissions in grams CO2
    carbon_co2_grams = energy_kwh * DEFAULT_GRID_CARBON_INTENSITY

    return EnergyMetrics(
        accelerator=profile.name,
        power_watts=round(facility_power_watts, 2),
        energy_joules=round(energy_joules, 4),
        energy_kwh=round(energy_kwh, 8),
        energy_cost_usd=round(energy_cost_usd, 7),
        carbon_co2_grams=round(carbon_co2_grams, 4),
        pue=pue,
    )


def calculate_intelligence_per_dollar(
    quality_score: Optional[float],
    successful_outcomes: float,
    total_cost_usd: float,
    energy_cost_usd: float = 0.0,
) -> Optional[float]:
    """
    Calculate Intelligence per Dollar (IPD).

    IPD = (Quality-Weighted Useful Output) / (Total Compute + Energy Cost)

    Answers: How much validated intelligence is produced per dollar invested?
    """
    combined_cost = total_cost_usd + energy_cost_usd
    if combined_cost <= 0.0:
        return None

    quality = max(0.05, quality_score if quality_score is not None else 1.0)
    effective_intelligence = quality * max(1.0, successful_outcomes)
    return round(effective_intelligence / combined_cost, 2)


def calculate_intelligence_per_watt(
    quality_score: Optional[float],
    successful_outcomes: float,
    energy_kwh: float,
) -> Optional[float]:
    """
    Calculate Intelligence per Watt-hour / kWh (IPW).

    IPW = (Quality-Weighted Useful Output) / (Energy Consumption in kWh)

    Answers: Who converts raw electrical watts into useful intelligence most efficiently?
    """
    if energy_kwh <= 0.0:
        return None

    quality = max(0.05, quality_score if quality_score is not None else 1.0)
    effective_intelligence = quality * max(1.0, successful_outcomes)
    return round(effective_intelligence / energy_kwh, 2)


def calculate_tokens_per_dollar(total_tokens: int, total_cost_usd: float) -> Optional[float]:
    """Calculate economic throughput: tokens generated/processed per dollar."""
    if total_cost_usd <= 0.0 or total_tokens <= 0:
        return None
    return round(total_tokens / total_cost_usd, 1)


def calculate_tokens_per_kwh(total_tokens: int, energy_kwh: float) -> Optional[float]:
    """Calculate energy throughput: tokens generated/processed per kilowatt-hour."""
    if energy_kwh <= 0.0 or total_tokens <= 0:
        return None
    return round(total_tokens / energy_kwh, 1)
