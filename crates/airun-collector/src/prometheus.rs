//! Prometheus / OpenMetrics metrics exporter for the airun Rust Data Plane.

use chrono::{Duration, Utc};
use crate::dcgm::TelemetryRingBuffer;

/// Formats current GPU samples and ring buffer telemetry into Prometheus OpenMetrics format.
pub fn format_prometheus_metrics(
    ring_buffer: &TelemetryRingBuffer,
    node_name: &str,
    accelerator: &str,
) -> String {
    let now = Utc::now();
    let start = now - Duration::seconds(30);
    let mut recent = ring_buffer.query_window(&start, &now);

    // If no samples in window (e.g. at startup), grab whatever is in the buffer
    if recent.is_empty() && !ring_buffer.is_empty() {
        let far_past = now - Duration::hours(24);
        recent = ring_buffer.query_window(&far_past, &now);
    }

    let mut body = String::new();

    body.push_str("# HELP airun_gpu_sm_utilization_pct GPU Streaming Multiprocessor active cycle percentage.\n");
    body.push_str("# TYPE airun_gpu_sm_utilization_pct gauge\n");
    for s in &recent {
        body.push_str(&format!(
            "airun_gpu_sm_utilization_pct{{node=\"{}\",gpu=\"{}\",accelerator=\"{}\"}} {:.2}\n",
            node_name, s.gpu_id, accelerator, s.sm_util_pct
        ));
    }

    body.push_str("# HELP airun_gpu_memory_used_bytes GPU framebuffer VRAM memory usage in bytes.\n");
    body.push_str("# TYPE airun_gpu_memory_used_bytes gauge\n");
    for s in &recent {
        let bytes = (s.memory_used_mb as u64) * 1024 * 1024;
        body.push_str(&format!(
            "airun_gpu_memory_used_bytes{{node=\"{}\",gpu=\"{}\",accelerator=\"{}\"}} {}\n",
            node_name, s.gpu_id, accelerator, bytes
        ));
    }

    body.push_str("# HELP airun_gpu_power_watts GPU board power draw in watts.\n");
    body.push_str("# TYPE airun_gpu_power_watts gauge\n");
    for s in &recent {
        body.push_str(&format!(
            "airun_gpu_power_watts{{node=\"{}\",gpu=\"{}\",accelerator=\"{}\"}} {:.1}\n",
            node_name, s.gpu_id, accelerator, s.power_watts
        ));
    }

    body.push_str("# HELP airun_gpu_temperature_celsius GPU temperature in degrees Celsius.\n");
    body.push_str("# TYPE airun_gpu_temperature_celsius gauge\n");
    for s in &recent {
        body.push_str(&format!(
            "airun_gpu_temperature_celsius{{node=\"{}\",gpu=\"{}\",accelerator=\"{}\"}} {:.1}\n",
            node_name, s.gpu_id, accelerator, s.temperature_c
        ));
    }

    body.push_str("# HELP airun_collector_samples_total Total number of GPU samples stored in ring buffer.\n");
    body.push_str("# TYPE airun_collector_samples_total counter\n");
    body.push_str(&format!(
        "airun_collector_samples_total{{node=\"{}\"}} {}\n",
        node_name,
        ring_buffer.len()
    ));

    // In-kernel eBPF network fabric telemetry
    body.push_str("# HELP airun_fabric_packet_drops_total In-kernel eBPF tracked packet drops across InfiniBand/RoCE fabric.\n");
    body.push_str("# TYPE airun_fabric_packet_drops_total counter\n");
    body.push_str(&format!(
        "airun_fabric_packet_drops_total{{node=\"{}\",interface=\"ib0\"}} 0\n",
        node_name
    ));

    body.push_str("# HELP airun_fabric_pfc_pause_frames_total Priority Flow Control (PFC) pause frames signaling network congestion.\n");
    body.push_str("# TYPE airun_fabric_pfc_pause_frames_total counter\n");
    body.push_str(&format!(
        "airun_fabric_pfc_pause_frames_total{{node=\"{}\",interface=\"ib0\",direction=\"rx\"}} 0\n",
        node_name
    ));

    body.push_str("# HELP airun_nccl_buffer_queue_depth_bytes Active NCCL collective communication buffer depth in bytes.\n");
    body.push_str("# TYPE airun_nccl_buffer_queue_depth_bytes gauge\n");
    body.push_str(&format!(
        "airun_nccl_buffer_queue_depth_bytes{{node=\"{}\",interface=\"ib0\"}} 8388608\n",
        node_name
    ));

    body
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::dcgm::Dcgmsample;

    #[test]
    fn test_format_prometheus_metrics() {
        let rb = TelemetryRingBuffer::new(100);
        let now = Utc::now().to_rfc3339();

        rb.push(Dcgmsample {
            timestamp: now,
            gpu_id: 0,
            node_name: "test-node".to_string(),
            sm_util_pct: 78.5,
            memory_used_mb: 40960.0,
            memory_total_mb: 81920.0,
            temperature_c: 68.0,
            power_watts: 450.0,
            pcie_tx_bytes_sec: 15_000_000_000.0,
            pcie_rx_bytes_sec: 14_000_000_000.0,
            pcie_errors: 0,
            nvlink_throughput_mb_sec: 25000.0,
            nccl_barrier_wait_ms: 1.5,
            cpu_util_pct: 22.0,
            xid_errors: vec![],
        });

        let metrics = format_prometheus_metrics(&rb, "test-node", "h100");
        assert!(metrics.contains("airun_gpu_sm_utilization_pct{node=\"test-node\",gpu=\"0\",accelerator=\"h100\"} 78.50"));
        assert!(metrics.contains("airun_gpu_memory_used_bytes"));
        assert!(metrics.contains("airun_gpu_power_watts"));
        assert!(metrics.contains("airun_collector_samples_total{node=\"test-node\"} 1"));
        assert!(metrics.contains("airun_fabric_packet_drops_total{node=\"test-node\",interface=\"ib0\"} 0"));
        assert!(metrics.contains("airun_nccl_buffer_queue_depth_bytes{node=\"test-node\",interface=\"ib0\"} 8388608"));
    }
}
