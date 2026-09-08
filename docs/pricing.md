# Pricing & Energy Economics Guide

`airun` includes a comprehensive cost and energy engine combining API token pricing, infrastructure amortization, and hardware accelerator electrical power modeling ($/kWh, Joules, IPD, IPW).

---

## 1. Default API Model Pricing Table

Built-in token rates per 1K tokens:
- **OpenAI**: `gpt-4o`, `gpt-4o-mini`, `gpt-4-turbo`, `gpt-4`, `gpt-3.5-turbo`, `o1`, `o1-mini`, `o3-mini`, `text-embedding-3-small`, `text-embedding-3-large`.
- **Anthropic**: `claude-3-5-sonnet`, `claude-3-opus`, `claude-3-5-haiku`, `claude-3-haiku`.
- **Google Gemini**: `gemini-1.5-pro`, `gemini-1.5-flash`, `gemini-2.0-flash`.
- **Local Models**: `local-llama-3-8b`, `mock-model`.

---

## 2. Hardware Accelerator Catalog & Thermal Profiles

`airun` models physical silicon power draw and hourly infrastructure amortization across major accelerators:

| Accelerator | Architecture | Peak TDP (Watts) | Typical Active Watts | Default Cloud Hourly Rate ($/hr) |
|---|---|---|---|---|
| **NVIDIA H100 SXM5** | Hopper (GH100) | 700 W | 650 W | $3.85 |
| **NVIDIA H100 PCIe** | Hopper (GH100) | 350 W | 310 W | $2.95 |
| **NVIDIA A100 SXM4** | Ampere (GA100) | 400 W | 350 W | $2.20 |
| **NVIDIA B200** | Blackwell | 1,000 W | 900 W | $6.50 |
| **NVIDIA L40S** | Ada Lovelace | 350 W | 300 W | $1.45 |
| **Google TPU v5e** | TPU Custom ASIC | 250 W | 200 W | $1.20 |
| **AMD Instinct MI300X** | CDNA 3 | 750 W | 680 W | $3.20 |
| **Apple Silicon (M3/M4 Max)** | Unified SoC | 60 W | 35 W | $0.00 (Local workstation) |

---

## 3. Electrical Energy & PUE Calculation

In addition to token and server rental costs, `airun` tracks true data center electricity consumption:

$$\text{Energy (Joules)} = \text{Power (Watts)} \times \left(\frac{\text{Duration (ms)}}{1000}\right)$$

$$\text{Energy (kWh)} = \frac{\text{Energy (Joules)}}{3,600,000}$$

$$\text{Energy Cost (USD)} = \text{Energy (kWh)} \times \text{Electricity Rate (\$/kWh)} \times \text{PUE}$$

- **Default Electricity Rate**: `$0.10 / kWh` (configurable)
- **Default Data Center PUE**: `1.20` (Power Usage Effectiveness factor)

---

## 4. Intelligence per Dollar (IPD) & Watt (IPW)

To quantify true economic and thermodynamic efficiency:

$$\text{IPD} = \frac{\text{Quality Score} \times \text{Output Tokens}}{\text{Token Cost (USD)} + \text{Infra Cost (USD)} + \text{Energy Cost (USD)}}$$

$$\text{IPW} = \frac{\text{Quality Score} \times \text{Output Tokens}}{\text{Energy (Joules)}}$$

---

## 5. Custom Configuration (`.airun/pricing.yaml`)

To override model rates, utility schedules, or custom hardware profiles:

```yaml
models:
  my-fine-tuned-model:
    input_cost_per_1k_tokens: 0.0015
    output_cost_per_1k_tokens: 0.0060

  vllm-llama3-70b-gpu-node:
    input_cost_per_1k_tokens: 0.0
    output_cost_per_1k_tokens: 0.0
    estimated_infra_cost_per_hour: 2.45
    accelerator: H100_SXM5

energy:
  electricity_rate_kwh: 0.12
  pue: 1.18
```

