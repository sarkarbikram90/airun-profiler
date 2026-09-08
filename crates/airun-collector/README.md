# airun-collector

High-throughput, real-time node telemetry collector DaemonSet for NVIDIA DCGM, NVML, and Kubernetes AI infrastructure profiling.

`airun-collector` serves as the high-performance **Real-Time Data Plane** for the [`airun`](https://github.com/sarkarbikram90/airun-profiler) AI Infrastructure Reliability & Economics Platform.

---

## Key Capabilities

- **High-Frequency GPU Telemetry (10Hz / 100ms)**: Samples GPU SM activity, Tensor Core utilization, memory bandwidth, temperature, power draw (Watts), and throttling states via NVML and NVIDIA DCGM.
- **In-Memory Circular Ring Buffer**: Retains high-resolution time-window samples in lock-free shared memory for instantaneous time-window correlation against application execution spans.
- **OTLP Native Span Ingestion**: Ingests and processes OpenTelemetry traces with sub-microsecond overhead.
- **Zero-GC Determinism**: Pure Rust implementation engineered for predictability under heavy multi-tenant Kubernetes workloads.
- **Multi-Cloud Kubernetes DaemonSet**: First-class support for GCP GKE, AWS EKS, and Azure AKS GPU node pools.

---

## Installation

### From crates.io
```bash
cargo install airun-collector
```

### Pre-built Docker Container
```bash
docker pull ghcr.io/sarkarbikram90/airun-profiler:latest
```

### Kubernetes Helm Chart
```bash
helm install airun-collector deploy/helm/airun-data-plane
```

---

## CLI Usage

```bash
# Run collector with default parameters (port 8080, 1000 sample ring buffer)
airun-collector

# Custom port and buffer capacity
airun-collector --port 9090 --buffer-size 2000 --interval-ms 50
```

### Configuration Options

| Flag / Argument | Environment Variable | Default | Description |
|---|---|---|---|
| `--port` | `AIRUN_PORT` | `8080` | HTTP/metrics port |
| `--buffer-size` | `AIRUN_BUFFER_SIZE` | `1000` | In-memory ring buffer capacity per GPU |
| `--interval-ms` | `AIRUN_INTERVAL_MS` | `100` | Telemetry sampling interval in milliseconds |
| `--dcgm-socket` | `DCGM_SOCKET` | `/var/run/nvidia-dcgm/dcgm.sock` | Path to UNIX domain socket for DCGM |

---

## Architecture Context

`airun-collector` runs as a `DaemonSet` on GPU worker nodes, bridging low-level hardware metrics with high-level AI application spans:

```text
[ LLM Agent / Pipeline ] ----(OTLP Trace Spans)----> [ airun-collector ]
                                                            │
[ NVIDIA GPU Silicon ] -----(DCGM / NVML 10Hz)------> [ Ring Buffer ]
                                                            │
                                                   (Time-Window Correlation)
                                                            │
                                                     [ airun Platform ]
```

---

## Related Projects

- **Main Platform Repository**: [https://github.com/sarkarbikram90/airun-profiler](https://github.com/sarkarbikram90/airun-profiler)
- **Python SDK (`airun-profiler`)**: [https://pypi.org/project/airun-profiler/](https://pypi.org/project/airun-profiler/)
- **Master Documentation**: [https://github.com/sarkarbikram90/airun-profiler#readme](https://github.com/sarkarbikram90/airun-profiler#readme)

---

## License

Apache-2.0. See [LICENSE](https://github.com/sarkarbikram90/airun-profiler/blob/main/LICENSE) for details.