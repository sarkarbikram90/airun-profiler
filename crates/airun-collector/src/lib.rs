//! airun-collector: Production Rust Real-Time Data Plane DaemonSet for NVIDIA DCGM & Kubernetes.
//!
//! Provides high-throughput, low-latency node telemetry collection, in-kernel eBPF network fabric tracing,
//! OpenTelemetry span correlation, tri-state circuit breaking, and distributed event broadcasting for AI infrastructure.

pub mod circuit_breaker;
pub mod dcgm;
pub mod ebpf;
pub mod otlp;
pub mod prometheus;
pub mod pubsub;

pub use circuit_breaker::{BreakerConfig, BreakerState, CircuitBreaker};
pub use dcgm::{Dcgmsample, DcgmScraper, HardwareMode, TelemetryBatch, TelemetryRingBuffer};
pub use ebpf::{EbpfFabricProbe, EbpfMode, FabricDropSample, FabricHealthReport};
pub use otlp::{OtlpSpan, SpanCorrelator};
pub use prometheus::format_prometheus_metrics;
pub use pubsub::{
    AirunEventEnvelope, AirunEventType, GpuAlertPayload, PubSubPublisher, WorkloadLifecyclePayload,
};
