# Case Study 2: PCIe Host-Device Bus Saturation in vLLM Serving

## Executive Summary
A production LLM serving deployment on 4x NVIDIA L4 GPUs was suffering from catastrophic **Time-to-First-Token (TTFT) p99 latency spikes exceeding 2.4 seconds** during peak user concurrency. Traditional APMs flagged slow database calls, but `airun` isolated the true physical bottleneck: **PCIe bus saturation** caused by excessive KV-cache swapping between GPU VRAM and host RAM over a constrained PCIe Gen4 x8 bus link.

---

## 1. Environment
- **Hardware**: 4x NVIDIA L4 (24GB GDDR6 each, PCIe Gen4 x8 link)
- **Cluster**: AWS EKS `g6.12xlarge` instance
- **Serving Engine**: vLLM 0.6.2
- **Model**: Qwen-2.5-32B-Instruct AWQ (4-bit quantized)
- **Concurrency**: 64 concurrent requests with average prompt length 3,500 tokens

---

## 2. Workload
- **Workload Type**: Enterprise RAG Assistant with long document context injection
- **Input Tokens**: 2,800 to 6,000 tokens per prompt
- **Output Tokens**: 250 tokens per generation
- **Serving Target**: Sub-500ms TTFT p95 SLA

---

## 3. Raw Infrastructure Telemetry
```text
NVIDIA DCGM & Linux Kernel Profiling:
- DCGM_FI_PROF_PCIE_TX_BYTES:   14.8 GB/s (saturated at physical PCIe x8 maximum)
- DCGM_FI_PROF_PCIE_RX_BYTES:   15.1 GB/s
- DCGM_FI_PROF_SM_ACTIVE:       38.2% (GPU cores idling while waiting for swapped cache blocks)
- DCGM_FI_PROF_DRAM_ACTIVE:     44.1%

vLLM Internal Metrics:
- vllm:gpu_cache_usage_factor:  99.8% (GPU memory fully exhausted)
- vllm:num_requests_swapped:    28 requests actively swapping KV blocks to host CPU memory
- vllm:time_in_queue_seconds:   1.42s
```

---

## 4. `airun` Trace & Diagnosis Card

```bash
$ airun diagnose trace-vllm-pcie-02 --accelerator l4 --gpus 4
```

```text
+--------------------------- AIRUN DIAGNOSTIC ---------------------------+
| Workflow: enterprise_rag_vllm_service                                  |
| Duration: 2.84s                                                        |
| Cost: $0.0092/request                                                  |
| GPU: L4 PCIe (4x GPUs)                                                 |
| GPU utilization: 41%                                                   |
| SM active: 38%                                                         |
| PCIe TX/RX: 15.0 GB/s (100% Saturation)                                |
| CPU utilization: 42%                                                   |
| GPU Efficiency: [#######-------------] 34/100 (CRITICAL_WASTE)         |
|                                                                        |
| ROOT CAUSE ----------------------------------------                    |
| Host-to-Device PCIe Bus Saturation (KV-Cache Thrashing)                |
|                                                                        |
| EVIDENCE ------------------------------------------                    |
| * PCIe bus saturated at 15.0 GB/s (>96% theoretical PCIe Gen4 x8 cap)  |
| * 28 active request KV caches swapped to host RAM causing bus stalls   |
| * GPU SM execution paused for 1,180ms waiting for tensor DMA transfers |
|                                                                        |
| FINANCIAL IMPACT ----------------------------------                    |
| Current cost:    $0.0092/request                                       |
| Estimated waste: $0.0039/request (42.4% PCIe wait penalty)             |
| Monthly waste:   $5,731.00                                             |
|                                                                        |
| RECOMMENDATION ------------------------------------                    |
| [OK] Enable vLLM automatic prefix caching (--enable-prefix-caching)    |
| [OK] Set gpu_memory_utilization=0.95 and reduce max_model_len to 4096  |
| [OK] Upgrade instance to PCIe Gen4 x16 bus layout or activate chunked  |
|      prefill (--enable-chunked-prefill)                                |
|                                                                        |
| EXPECTED RESULT -----------------------------------                    |
| TTFT p99           2.4s -> 380ms (-84.1%)                              |
| PCIe Saturation    100% -> 18%                                         |
| Monthly Savings    $5,731.00                                           |
+------------------------------------------------------------------------+
```

---

## 5. Before vs. After Optimization

| Metric | Before Optimization | After `airun` Fix | Delta |
| :--- | :---: | :---: | :---: |
| **TTFT p50** | 480ms | **140ms** | **-70.8%** |
| **TTFT p99** | 2,420ms | **365ms** | **-84.9%** |
| **Swapped Requests** | 28 | **0** | **-100%** |
| **Throughput** | 412 tok/s | **1,048 tok/s** | **+154.3%** |
| **Monthly Recoverable Waste** | $5,731 / month | **$0** | **100% Eliminated** |

---

## 6. Reproduction Steps

1. Ingest sample workload trace:
   ```bash
   airun trace import examples/telemetry/case_studies/case2_pcie_vllm.json
   ```
2. Diagnose silicon and bus bottlenecks:
   ```bash
   airun diagnose latest --accelerator l4 --gpus 4
   ```
3. Verify benchmark impact:
   ```bash
   airun bench --model qwen-2.5-32b --gpu l4
   ```
