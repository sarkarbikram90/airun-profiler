//! airun-collector: Production Rust Real-Time Data Plane DaemonSet for NVIDIA DCGM & Kubernetes.

mod circuit_breaker;
mod dcgm;
mod otlp;
mod pubsub;

use circuit_breaker::{CircuitBreaker, BreakerConfig};
use dcgm::{DcgmScraper, TelemetryRingBuffer};
use otlp::{OtlpSpan, SpanCorrelator};
use pubsub::PubSubPublisher;
use std::collections::HashMap;
use std::env;
use std::sync::Arc;
use std::time::Duration;

#[tokio::main]
async fn main() -> Result<(), Box<dyn std::error::Error>> {
    let node_name = env::var("NODE_NAME").unwrap_or_else(|_| "gke-gpu-node-default".to_string());
    let cluster_id = env::var("CLUSTER_ID").unwrap_or_else(|_| "us-central1-gke-prod".to_string());
    let pubsub_topic = env::var("PUBSUB_TOPIC").unwrap_or_else(|_| "ai-infrastructure-events".to_string());
    let project_id = env::var("GCP_PROJECT_ID").unwrap_or_else(|_| "airun-production".to_string());
    let accelerator_type = env::var("ACCELERATOR_TYPE").unwrap_or_else(|_| "h100".to_string());
    let num_gpus: u32 = env::var("NUM_GPUS")
        .ok()
        .and_then(|v| v.parse().ok())
        .unwrap_or(8);

    println!("============================================================");
    println!("  airun-collector (Rust Real-Time Data Plane Engine)");
    println!("============================================================");
    println!("  * Node Name:       {}", node_name);
    println!("  * Cluster ID:      {}", cluster_id);
    println!("  * Accelerator:     {}x {}", num_gpus, accelerator_type);
    println!("  * Pub/Sub Topic:   projects/{}/topics/{}", project_id, pubsub_topic);
    println!("  * In-Memory Buffer: 1,000 samples @ 10Hz ring buffer");
    println!("============================================================");

    let scraper = DcgmScraper::new(node_name.clone(), accelerator_type, num_gpus);
    println!("  * Hardware Mode:   {:?}", scraper.mode());

    let ring_buffer = Arc::new(TelemetryRingBuffer::new(1000));
    let publisher = PubSubPublisher::new(pubsub_topic, project_id);
    let breaker = CircuitBreaker::new("openai-h100-pool".into(), Some(BreakerConfig::default()));

    println!("  * Circuit Breaker: Initial state = {:?}", breaker.state());

    let mut count: u64 = 0;
    loop {
        count += 1;
        let batch_id = format!("batch_{}", count);
        let batch = scraper.collect_batch(&batch_id, &cluster_id);

        // Feed local ring buffer for microsecond zero-overhead time-window correlation
        ring_buffer.push_batch(batch.samples.clone());

        // Stream batch to Pub/Sub backbone
        if let Err(e) = publisher.publish_telemetry_batch(&batch).await {
            eprintln!("[!] Telemetry push failed: {}", e);
        }

        // Example local trace span correlation check
        if count == 1 {
            let now = chrono::Utc::now();
            let now_nano = (now.timestamp() as u64) * 1_000_000_000 + (now.timestamp_subsec_nanos() as u64);
            let sample_span = OtlpSpan {
                trace_id: "demo_trace_001".to_string(),
                span_id: "span_101".to_string(),
                name: "agent_researcher".to_string(),
                start_time_unix_nano: now_nano.saturating_sub(200_000_000),
                end_time_unix_nano: now_nano,
                attributes: HashMap::new(),
            };
            let finding = SpanCorrelator::correlate_span(&sample_span, &ring_buffer);
            println!(
                "  * Local Correlation: Trace '{}' Span '{}' Duration: {:.2}ms (SM: {:.1}%, PCIe: {:.1} MB/s)",
                finding.trace_id,
                finding.span_name,
                finding.duration_ms,
                finding.hardware_analysis.avg_sm_util_pct,
                finding.hardware_analysis.max_pcie_tx_mbs
            );
        }

        // 1-second scraping interval for batch publishing
        tokio::time::sleep(Duration::from_secs(1)).await;

        // In test/demo environment, yield after 5 batches if running non-daemon
        if env::var("AIRUN_TEST_MODE").is_ok() && count >= 5 {
            println!("[*] Test mode complete: 5 batches collected.");
            break;
        }
    }

    Ok(())
}
