"""Example: Hardware Accelerator Power, Energy, and Intelligence per Watt Profiling.

Demonstrates the implementation of SPECIFICATION.md:
"The killer metric: Intelligence per Dollar (IPD) and Intelligence per Watt (IPW):
IPD = useful task output / (compute + energy + infrastructure cost)
IPW = useful task output / energy (kWh)
Who can extract the most economic output from each watt?
That is arguably the key economic metric emerging from the AI era."
"""

import time

from airun import SpanKind, set_span_metadata, set_span_quality, set_span_tokens, trace
from airun.pricing.energy import (
    ACCELERATOR_CATALOG,
    calculate_energy,
    calculate_intelligence_per_dollar,
    calculate_intelligence_per_watt,
)


def main():
    print("=" * 65)
    print("  [airun] Hardware Accelerator Power & Energy Economics Demo")
    print("=" * 65)

    print("\n>> AI Hardware Accelerator Catalog & Electrical Specifications:")
    for _key, prof in list(ACCELERATOR_CATALOG.items())[:6]:
        print(
            f"  * {prof.name:<26} TDP: {prof.tdp_watts:>4.0f}W | Idle: {prof.idle_watts:>3.0f}W | Memory: {prof.memory_type}"
        )

    # Profile simulated workload on an NVIDIA H100 SXM5
    with trace("h100_frontier_pretrain_step", kind=SpanKind.WORKFLOW):
        with trace(
            "transformer_forward_pass", kind=SpanKind.LLM, model="claude-3-5-sonnet"
        ) as span1:
            time.sleep(0.06)
            set_span_tokens(input_tokens=4000, output_tokens=1200)
            set_span_quality(0.98, {"eval_suite": "arc_challenge", "accuracy": 0.99})

            # Explicitly profile on H100 hardware
            span1.accelerator_type = "h100"
            nrg = calculate_energy(duration_ms=60.0, accelerator="h100", utilization_pct=0.85)
            span1.power_watts = nrg.power_watts
            span1.energy_joules = nrg.energy_joules
            span1.energy_kwh = nrg.energy_kwh
            span1.energy_cost_usd = nrg.energy_cost_usd
            set_span_metadata(
                {
                    "accelerator": "NVIDIA H100 SXM5",
                    "power_watts": nrg.power_watts,
                    "energy_joules": nrg.energy_joules,
                    "carbon_grams_co2": nrg.carbon_co2_grams,
                }
            )

    print("\n>> Profiled Step Telemetry on H100 SXM5:")
    print(f"  * Power Draw (with PUE 1.20): {nrg.power_watts:.1f} Watts")
    print(
        f"  * Energy Consumed:            {nrg.energy_joules:.2f} Joules ({nrg.energy_kwh:.8f} kWh)"
    )
    print(f"  * Estimated Electricity Cost: ${nrg.energy_cost_usd:.6f}")
    print(f"  * Carbon Footprint:           {nrg.carbon_co2_grams:.4f} g CO2")

    # Compute IPD and IPW
    ipd = calculate_intelligence_per_dollar(
        quality_score=0.98,
        successful_outcomes=1.0,
        total_cost_usd=0.024,
        energy_cost_usd=nrg.energy_cost_usd,
    )
    ipw = calculate_intelligence_per_watt(
        quality_score=0.98,
        successful_outcomes=1.0,
        energy_kwh=nrg.energy_kwh,
    )
    print("\n>> Economic Intelligence Ratios:")
    print(f"  * Intelligence per Dollar (IPD): {ipd}")
    print(f"  * Intelligence per Watt (IPW):   {ipw:,.1f}")

    print(
        "\n[OK] Energy and power profiling completed. Run 'airun metrics latest' to inspect full breakdown."
    )


if __name__ == "__main__":
    main()
