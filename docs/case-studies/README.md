# Real-World AI Infrastructure Performance Case Studies

This directory contains production case studies demonstrating how `airun` bridges logical AI traces with physical infrastructure telemetry to detect bottlenecks, eliminate financial bleed, and guarantee SLA compliance.

---

## Case Study Directory

| Case Study | Infrastructure | Workload | Primary Bottleneck | Financial Recovery | Document |
| :--- | :--- | :--- | :--- | :---: | :--- |
| **Case #1** | 8x NVIDIA H100 SXM5 | Llama-3-70B DeepSpeed Fine-Tuning | **Host CPU DataLoader Starvation** | **$14,270 / mo** | [Read Case Study](case-1-dataloader-starvation.md) |
| **Case #2** | 4x NVIDIA L4 (GKE/EKS) | vLLM Qwen-2.5-32B Serving | **PCIe Host-Device KV-Cache Thrashing** | **$5,731 / mo** | [Read Case Study](case-2-pcie-nvlink-bottleneck.md) |
| **Case #3** | Multi-Agent MCP Graph | Claude 3.5 Sonnet + MCP Tools | **Retry Amplification & Context Bloat** | **$6,280 / mo** | [Read Case Study](case-3-agent-tool-amplification.md) |

---

## Methodology & Reproducibility Standard

Every case study in this catalog adheres to strict reproducibility standards:
1. **Physical Grounding**: Grounded in high-frequency hardware metrics (NVIDIA DCGM at 100ms, Linux kernel tracepoints, PCIe RX/TX DMA transfers).
2. **Deterministic Root Cause**: Identifies the exact application line, tensor configuration, or kernel stall causing the inefficiency.
3. **Verified Before/After**: Rigorous empirical measurement comparing baseline vs. optimized states across latency, throughput, token volume, and dollar spend.
