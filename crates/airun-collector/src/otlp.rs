//! OTLP Trace Ingestion and Time-Window Span Correlation in Rust Data Plane.

use chrono::{DateTime, Utc};
use serde::{Deserialize, Serialize};
use std::collections::HashMap;

use crate::dcgm::{TelemetryRingBuffer, WindowAnalysis};

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct OtlpSpan {
    pub trace_id: String,
    pub span_id: String,
    pub name: String,
    pub start_time_unix_nano: u64,
    pub end_time_unix_nano: u64,
    pub attributes: HashMap<String, String>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct CorrelatedSpanFinding {
    pub trace_id: String,
    pub span_name: String,
    pub duration_ms: f64,
    pub hardware_analysis: WindowAnalysis,
    pub root_cause: Option<String>,
    pub recommended_action: Option<String>,
}

pub struct SpanCorrelator;

impl SpanCorrelator {
    /// Correlates a logical OTLP span with the high-frequency physical telemetry in the ring buffer.
    pub fn correlate_span(span: &OtlpSpan, ring_buffer: &TelemetryRingBuffer) -> CorrelatedSpanFinding {
        let start_secs = (span.start_time_unix_nano / 1_000_000_000) as i64;
        let start_nanos = (span.start_time_unix_nano % 1_000_000_000) as u32;
        let start_dt = DateTime::<Utc>::from_timestamp(start_secs, start_nanos).unwrap_or_else(Utc::now);

        let end_secs = (span.end_time_unix_nano / 1_000_000_000) as i64;
        let end_nanos = (span.end_time_unix_nano % 1_000_000_000) as u32;
        let end_dt = DateTime::<Utc>::from_timestamp(end_secs, end_nanos).unwrap_or_else(Utc::now);

        let duration_ms = ((span.end_time_unix_nano - span.start_time_unix_nano) as f64) / 1_000_000.0;

        let hardware_analysis = ring_buffer.analyze_window(&start_dt, &end_dt);

        let (root_cause, recommended_action) = match hardware_analysis.detected_bottleneck.as_deref() {
            Some("dataloader_starvation") => (
                Some("GPU SM active cycles dropped significantly during span execution while PCIe remained idle.".into()),
                Some("Increase DataLoader num_workers, enable pin_memory=True, and pre-stage datasets to local NVMe storage.".into()),
            ),
            Some("nccl_communication_overhead") => (
                Some("GPU threads stalled in All-Reduce barrier synchronization.".into()),
                Some("Tune NCCL_BUFFSIZE=16MB and check InfiniBand/RoCE network switch retransmits.".into()),
            ),
            Some("pcie_bus_saturation") => (
                Some("Excessive Host-to-Device tensor copying saturated PCIe bandwidth.".into()),
                Some("Pin embeddings in VRAM and use asynchronous non_blocking=True memory copies.".into()),
            ),
            _ => (None, None),
        };

        CorrelatedSpanFinding {
            trace_id: span.trace_id.clone(),
            span_name: span.name.clone(),
            duration_ms,
            hardware_analysis,
            root_cause,
            recommended_action,
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_otlp_span_correlation() {
        let rb = TelemetryRingBuffer::new(50);
        let now = Utc::now();
        let now_nano = (now.timestamp() as u64) * 1_000_000_000 + (now.timestamp_subsec_nanos() as u64);

        let span = OtlpSpan {
            trace_id: "trace-999".into(),
            span_id: "span-1".into(),
            name: "agent_researcher".into(),
            start_time_unix_nano: now_nano - 100_000_000,
            end_time_unix_nano: now_nano,
            attributes: HashMap::new(),
        };

        let finding = SpanCorrelator::correlate_span(&span, &rb);
        assert_eq!(finding.trace_id, "trace-999");
        assert_eq!(finding.span_name, "agent_researcher");
    }
}
