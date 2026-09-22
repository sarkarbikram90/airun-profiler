# Standardized GPU Efficiency Score (0–100) Specification

The **GPU Efficiency Score** is an opinionated, physically-grounded metric engineered by `airun` to quantify how effectively an AI workload leverages modern hardware accelerators (NVIDIA H100 SXM5/PCIe, A100, L4, B200 Blackwell, and TPU v5e).

Unlike superficial metrics (e.g. `nvidia-smi` percent utilization which merely reports whether any kernel touched the GPU during a sampling window), the GPU Efficiency Score evaluates **tensor core saturation, high-bandwidth memory (HBM) throughput, host bus utilization, and distributed synchronization barriers**.

---

## 1. Mathematical Formulation

The base efficiency score is computed as a weighted linear combination of four physical silicon dimensions, penalized by hardware anomalies:

$$\text{Score} = \text{clamp}_{[0, 100]}\left( w_{\text{SM}} \cdot U_{\text{SM}} + w_{\text{BW}} \cdot U_{\text{BW}} + w_{\text{MFU}} \cdot \text{MFU}_{\text{norm}} + w_{\text{Bus}} \cdot U_{\text{Bus}} - \sum \text{Penalties} \right)$$

### Dimension Weights

| Dimension | Symbol | Weight | Telemetry Source | Physical Rationale |
| :--- | :---: | :---: | :--- | :--- |
| **SM Active Cycles** | $U_{\text{SM}}$ | **35%** (`0.35`) | DCGM `DCGM_FI_PROF_SM_ACTIVE` | Percentage of time Streaming Multiprocessors have at least 1 active warp. Directly bounds compute efficiency. |
| **Memory Bandwidth** | $U_{\text{BW}}$ | **30%** (`0.30`) | DCGM `DCGM_FI_PROF_DRAM_ACTIVE` | Saturation of HBM3/HBM2e memory controller. Critical for LLM autoregressive token decode phases. |
| **Model FLOPs Util (MFU)** | $\text{MFU}_{\text{norm}}$ | **20%** (`0.20`) | Calculated: $\frac{\text{Achieved TFLOPS}}{\text{Peak Hardware TFLOPS}}$ | Measures algorithmic math efficiency relative to theoretical accelerator peak (FP16/BF16/FP8). |
| **Host Bus Efficiency** | $U_{\text{Bus}}$ | **15%** (`0.15`) | DCGM `DCGM_FI_PROF_PCIE_RX_BYTES` | Host-to-Device transfer rate relative to physical PCIe Gen4/5 or NVLink bus bandwidth. |

---

## 2. Deductions for Hardware & Fabric Anomalies

Physical anomalies reduce effective compute capacity and indicate degraded silicon health or cluster misconfiguration:

| Anomaly | Deduction | Trigger Condition | Impact |
| :--- | :---: | :--- | :--- |
| **Thermal Throttling** | **-15.0** | `DCGM_FI_DEV_THERMAL_VIOLATION > 0` | GPU drops clock frequency to prevent hardware damage, slashing effective FLOPS. |
| **PCIe Bus Errors** | **-10.0** | `pcie_errors > 0` or PCIe Gen1 fallback | Packet replays and downgraded link widths throttle tensor dispatch. |
| **NCCL Stalls** | **-10.0** | `nccl_stall_ms > 200.0` | Distributed workers idling at synchronization barriers (`AllReduce`, `AllGather`). |

---

## 3. Workload Calibration Matrix

The score classifies workloads across four operational tiers:

- **EXCELLENT (85–100)**: Optimal silicon utilization. Hardware operates within target efficiency envelope.
- **GOOD (70–84)**: Well-tuned inference or training workload with balanced compute and memory access.
- **SUBOPTIMAL (50–69)**: Detectable bottlenecks present. Batch size, KV-cache, or data loader tuning required.
- **CRITICAL WASTE (<50)**: Severe silicon starvation. Over 50% of hourly GPU spend is unproductively wasted.

### Workload Diagnostic Signatures

```text
1. DataLoader Starvation (CPU/IO Bound)
   SM Active: 28%  |  Mem BW: 25%  |  PCIe RX: 1.2 GB/s  |  Score: 24/100 (CRITICAL_WASTE)
   Root Cause: Host CPU workers cannot load and preprocess mini-batches fast enough.
   Remedy: Increase DataLoader num_workers=8, set pin_memory=True, prefetch tensors.

2. Memory Bandwidth Bound (LLM Decode)
   SM Active: 45%  |  Mem BW: 88%  |  PCIe RX: 12.4 GB/s |  Score: 68/100 (SUBOPTIMAL)
   Root Cause: Autoregressive decoding waiting on weight memory transfer from HBM.
   Remedy: Implement continuous batching, weight quantization (FP8), or FlashAttention-3.

3. Distributed NCCL Stall
   SM Active: 38%  |  Mem BW: 34%  |  NCCL Barrier: 420ms |  Score: 32/100 (CRITICAL_WASTE)
   Root Cause: Network fabric congestion (PFC pause frame storm or straggler node).
   Remedy: Check InfiniBand/RoCE MTU, disable PCIe power management, isolate straggler GPU.
```

---

## 4. Defensible Transparency in `airun`

Every time `airun` computes a GPU Efficiency Score, the complete mathematical derivation is exposed:

```bash
$ airun diagnose latest --json
```

```json
"gpu_efficiency": {
  "score": 24,
  "rating": "CRITICAL_WASTE",
  "accelerator": "H100",
  "formula_breakdown": "0.35*SM(29%) + 0.30*MemBW(32%) + 0.20*MFU(22%) + 0.15*Bus(2%) = 24/100",
  "primary_bottleneck": "Host DataLoader starvation (CPU/IO Bound)",
  "potential_throughput_gain_pct": 36.8,
  "cost_savings_per_1k_tokens_usd": 0.00179
}
```
