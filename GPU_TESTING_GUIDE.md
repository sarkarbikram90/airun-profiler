# Physical GPU Testing & Verification Guide

This guide provides step-by-step instructions to verify and benchmark `airun-profiler` on machines equipped with physical NVIDIA GPUs (e.g., **H100**, **A100**, **L40S**, **V100**, or **RTX 4090/3090**).

---

## 1. Prerequisites on the GPU Host

Ensure your GPU machine has the necessary drivers and runtime dependencies installed:

1. **NVIDIA Driver & CUDA Toolkit**:
   ```bash
   nvidia-smi
   ```
   Verify that your GPU device(s) and driver version are reported properly.

2. **Python Environment & Dependencies**:
   Install `airun-profiler` with development and OTLP dependencies:
   ```bash
   pip install -e ".[dev,otel]"
   ```

3. **PyTorch with CUDA Support** *(Recommended for live tensor execution)*:
   Verify CUDA is accessible in Python:
   ```bash
   python -c "import torch; print('CUDA available:', torch.cuda.is_available(), '| Device:', torch.cuda.get_device_name(0) if torch.cuda.is_available() else 'None')"
   ```

4. **NVIDIA DCGM Daemon** *(Optional, for kernel & hardware telemetry scraping)*:
   If using DCGM, ensure the socket exists:
   ```bash
   ls -la /var/run/nvidia-dcgm/dcgm.sock
   ```

---

## 2. Method 1: Automated Turnkey Verification Script (Fastest)

Run the included verification script in `examples/verify_real_gpu.py`:

```bash
python examples/verify_real_gpu.py
```

### What this does:
1. **Queries Hardware**: Detects physical GPU attributes via `nvidia-smi` / `pynvml` (device name, driver version, total VRAM, live SM utilization, temperature, and power draw in Watts).
2. **Executes Real GPU Workload**: Allocates FP16 tensors on `cuda:0` and runs high-throughput GEMM matrix multiplications (`torch.matmul`) inside an `airun` execution span with CUDA synchronization.
3. **Correlates Telemetry**: Feeds live GPU telemetry into `TimeWindowCorrelator`.
4. **Renders Bleed Report**: Outputs the formatted **Hardware Waste & Financial Bleed Report** calculating:
   - GPU SM active cycles vs idle stalls
   - PCIe TX/RX throughput
   - MFU (Model FLOPs Utilization)
   - Real-time financial bleed ($/hr and $/week)

---

## 3. Method 2: Execute the Physical Hardware Test Suite

Run the dedicated hardware test suite:

```bash
pytest tests/hardware/test_silicon_hardware.py -v -s
```

### What this verifies:
- `test_silicon_environment_detection`: Verifies the hardware probing subsystem initializes cleanly without errors.
- `test_physical_gpu_discovery`: Confirms physical NVIDIA GPU detection, verifies device UUID, compute capability, and VRAM > 1GB.
- `test_gpu_telemetry_metrics`: Queries live GPU temperature (10°C–105°C) and active power consumption (W).
- `test_dcgm_socket_or_emulation`: Checks socket connectivity against `/var/run/nvidia-dcgm/dcgm.sock` or verifies graceful sysfs fallback.
- `test_synthetic_h100_silicon_waste_diagnosis`: Tests sub-millisecond physical silicon telemetry correlation (throttling, memory bounds, and eBPF fabric drops).

---

## 4. Method 3: Run the High-Throughput Rust Data Plane Collector

To test live metric collection at 10Hz directly from hardware:

### Step 1: Start the Rust Collector Daemon
```bash
cargo run --manifest-path crates/airun-collector/Cargo.toml --release
```

*Or via Docker with GPU passthrough:*
```bash
docker run --rm --gpus all \
  -v /var/run/nvidia-dcgm:/var/run/nvidia-dcgm \
  -p 9445:9445 -p 4318:4318 \
  ghcr.io/sarkarbikram90/airun-collector:latest
```

### Step 2: Inspect OpenMetrics Exporter (`:9445/metrics`)
In a separate terminal, query the Prometheus metrics endpoint:
```bash
curl http://localhost:9445/metrics
```

Expected live metrics from physical silicon:
```text
# HELP airun_gpu_sm_utilization_pct GPU Streaming Multiprocessor utilization percentage (0-100)
# TYPE airun_gpu_sm_utilization_pct gauge
airun_gpu_sm_utilization_pct{gpu="0"} 84.5
# HELP airun_gpu_power_watts GPU real-time power draw in watts
# TYPE airun_gpu_power_watts gauge
airun_gpu_power_watts{gpu="0"} 542.0
# HELP airun_fabric_packet_drops_total In-kernel network fabric packet drops
# TYPE airun_fabric_packet_drops_total counter
airun_fabric_packet_drops_total{interface="ib0"} 0
# HELP airun_fabric_pfc_pause_frames_total PFC pause frames received/transmitted
# TYPE airun_fabric_pfc_pause_frames_total counter
airun_fabric_pfc_pause_frames_total{interface="ib0"} 0
```

---

## 5. Method 4: Non-Intrusively Profile an Existing PyTorch / vLLM Process

If you already have a training job, inference server, or agent workflow running on the GPU:

1. **Find the Process ID (PID)** of the Python/PyTorch job:
   ```bash
   nvidia-smi
   ```
2. **Attach the airun Profiler Hook**:
   ```bash
   airun profiler trace --pid <PID>
   ```
3. **Diagnose Silicon Waste & Bleed**:
   ```bash
   airun waste latest --hardware --accelerator h100 --gpus 8
   ```

---

## 6. Method 5: CLI Hardware Waste & Multi-Cluster Federation

Use the CLI to inspect hardware signals and multi-cluster capacity:

- **Golden Signals Hierarchy (4 Layers)**:
  ```bash
  airun golden-signals latest
  ```
  Inspects Economics (CFO View), Efficiency / MFU, Reliability (AI Breaker Box), and Infrastructure (Physical Layer).

- **Multi-Cluster Cross-Cloud Federation**:
  ```bash
  airun cluster list
  airun cluster overview
  airun cluster recommend llama3-70b-train --gpus 8 --accelerator h100
  ```

---

## 7. Method 6: Launch the Visual Command Center

To inspect the real GPU telemetry in a live web dashboard:

```bash
airun ui
```
Open **`http://localhost:8585`** in your browser to inspect:
- **Executive KPI Dashboard**: Live cost, power, Intelligence per Watt (IPW), and MFU.
- **Physical Silicon Layer**: GPU SM cycles, PCIe saturation, and thermal throttling.
- **AI-Aware Causal Incident Graph**: Direct graphical correlation between hardware events and financial waste.

---

## 8. Troubleshooting & FAQ

- **Q: `nvidia-smi: command not found`**
  Ensure NVIDIA drivers are installed and added to your `PATH` (e.g. `/usr/local/cuda/bin` on Linux or `C:\Program Files\NVIDIA Corporation\NVSMI` on Windows).
- **Q: Running in Docker container without GPU access?**
  Add the `--gpus all` flag:
  ```bash
  docker run --gpus all ...
  ```
- **Q: Running in Kubernetes?**
  Use the provided DaemonSet and self-hosted runner manifests:
  - `deploy/kubernetes/daemonset-agent.yaml`
  - `deploy/ci/gpu-runner.yaml`
  - `.github/workflows/gpu-hardware-ci.yml`