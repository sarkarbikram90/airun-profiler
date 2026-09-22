# Case Study 1: Host CPU & DataLoader Starvation on NVIDIA H100 Cluster

## Executive Summary
A distributed fine-tuning job on an 8x NVIDIA H100 SXM5 cluster was achieving only **32% GPU compute utilization**, costing **$14,820/month in wasted GPU compute**. By correlating the Python application trace with NVIDIA DCGM hardware telemetry, `airun` identified that host CPU workers were failing to saturate the tensor cores due to unpinned memory and synchronous dataset tokenization.

---

## 1. Environment
- **Hardware**: 8x NVIDIA H100 SXM5 (80GB HBM3 each), 2x Intel Xeon Platinum 8480+ (112 vCPUs), 512GB DDR5 RAM
- **Cluster**: Google Kubernetes Engine (GKE) A3-HighGPU-8g node
- **OS / Drivers**: Ubuntu 22.04 LTS, NVIDIA Driver 550.54.14, CUDA 12.4
- **Framework**: PyTorch 2.4, HuggingFace Accelerate, DeepSpeed ZeRO-3

---

## 2. Workload
- **Model**: Llama-3-70B instruction fine-tuning
- **Batch Size**: Micro-batch size 2, gradient accumulation steps 8
- **Sequence Length**: 4,096 tokens with dynamic padding
- **Dataset**: 500k multimodal instruction-tuning pairs loaded from network-attached Cloud Storage (GCS)

---

## 3. Raw Infrastructure Telemetry
```text
NVIDIA DCGM Samples (100ms interval):
- DCGM_FI_PROF_SM_ACTIVE:       29.4% (stalled waiting for memory input)
- DCGM_FI_PROF_DRAM_ACTIVE:     31.8%
- DCGM_FI_PROF_PCIE_RX_BYTES:   1.1 GB/s (Bus capacity: 64 GB/s PCIe Gen5)
- DCGM_FI_DEV_POWER_USAGE:      240 W / 700 W TDP

Host Linux Telemetry:
- CPU utilization:              98.2% across 8 DataLoader worker processes
- Context switches/sec:         148,000 (high lock contention in PyTorch IPC queues)
- Page faults/sec:              32,000 (unpinned host memory pages being paged in)
```

---

## 4. `airun` Trace & Diagnosis Card

```bash
$ airun diagnose trace-h100-train-01 --accelerator h100 --gpus 8
```

```text
+--------------------------- AIRUN DIAGNOSTIC ---------------------------+
| Workflow: llama3_70b_finetune_step                                     |
| Duration: 4.82s                                                        |
| Cost: $0.1820/step                                                     |
| GPU: H100 SXM (8x GPUs)                                                |
| GPU utilization: 32%                                                   |
| SM active: 29%                                                         |
| PCIe RX: 1.1 GB/s                                                      |
| CPU utilization: 98%                                                   |
| GPU Efficiency: [#####---------------] 26/100 (CRITICAL_WASTE)         |
|                                                                        |
| ROOT CAUSE ----------------------------------------                    |
| Host DataLoader starvation (CPU/IO Bound)                              |
|                                                                        |
| EVIDENCE ------------------------------------------                    |
| * GPU SM active cycles stalled at 29.4% (idle wait between batches)    |
| * PCIe Host-to-Device RX bus at 1.1 GB/s (<2% PCIe Gen5 bus capacity)  |
| * Host CPU data preparation took 3.24s out of 4.82s total step duration|
|                                                                        |
| FINANCIAL IMPACT ----------------------------------                    |
| Current cost:    $29.44/node-hour                                      |
| Estimated waste: $19.82/node-hour (67.3% unutilized silicon)           |
| Monthly waste:   $14,270.40                                            |
|                                                                        |
| RECOMMENDATION ------------------------------------                    |
| [OK] Set DataLoader pin_memory=True and prefetch_factor=4              |
| [OK] Increase DataLoader num_workers=16 and pin to NUMA sockets        |
| [OK] Pre-tokenize dataset to disk to eliminate per-step CPU overhead   |
|                                                                        |
| EXPECTED RESULT -----------------------------------                    |
| Gpu Utilization    32% -> ~81%                                         |
| Step Duration      4.82s -> 1.74s (-63.9%)                             |
| Monthly Savings    $14,270.40                                          |
+------------------------------------------------------------------------+
```

---

## 5. Before vs. After Optimization

| Metric | Before Optimization | After `airun` Fix | Delta |
| :--- | :---: | :---: | :---: |
| **Step Latency** | 4.82s | **1.68s** | **-65.1%** |
| **GPU SM Utilization** | 29.4% | **82.1%** | **+52.7%** |
| **Token Throughput** | 1,700 tokens/s | **4,876 tokens/s** | **+186.8%** |
| **Effective Cost / 1M Tokens** | $4.81 | **$1.68** | **-65.1%** |
| **Recovered Monthly Spend** | $0 | **$14,270 / month** | **100% Recovered** |

---

## 6. Reproduction Steps

1. Ingest sample workload trace:
   ```bash
   airun trace import examples/telemetry/case_studies/case1_dataloader.json
   ```
2. Run automated silicon diagnosis:
   ```bash
   airun diagnose latest --accelerator h100
   ```
3. Export executive HTML audit report:
   ```bash
   airun diagnose latest --export case1_report.html
   ```
