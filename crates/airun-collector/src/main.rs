//! airun-collector: Production Rust Real-Time Data Plane DaemonSet for NVIDIA DCGM & Kubernetes.

mod circuit_breaker;
mod dcgm;
mod otlp;
mod pubsub;

use circuit_breaker::{CircuitBreaker, BreakerConfig};
use dcgm::{DcgmScraper, TelemetryRingBuffer};
use otlp::{OtlpSpan, SpanCorrelator};
use pubsub::{AirunEventType, GpuAlertPayload, PubSubPublisher, WorkloadLifecyclePayload};
use std::collections::HashMap;
use std::env;
use std::sync::Arc;
use std::time::Duration;

#[tokio::main]
async fn main() -> Result<(), Box<dyn std::error::Error>> {
    let node_name = env::var("NODE_NAME").unwrap_or_else(|_| "gke-gpu-node-default".to_string());
    let pod_name = env::var("POD_NAME").unwrap_or_else(|_| "airun-collector-daemonset-4x8".to_string());
    let pod_namespace = env::var("POD_NAMESPACE").unwrap_or_else(|_| "airun-system".to_string());
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
    println!("  * Pod Context:     {}/{}", pod_namespace, pod_name);
    println!("  * Cluster ID:      {}", cluster_id);
    println!("  * Accelerator:     {}x {}", num_gpus, accelerator_type);
    println!("  * Pub/Sub Topic:   projects/{}/topics/{}", project_id, pubsub_topic);
    println!("  * In-Memory Buffer: 1,000 samples @ 10Hz ring buffer");
    println!("============================================================");

    let scraper = DcgmScraper::new(node_name.clone(), accelerator_type.clone(), num_gpus);
    println!("  * Hardware Mode:   {:?}", scraper.mode());

    let ring_buffer = Arc::new(TelemetryRingBuffer::new(1000));
    let publisher = PubSubPublisher::new(pubsub_topic.clone(), project_id.clone());
    let breaker = CircuitBreaker::new("openai-h100-pool".into(), Some(BreakerConfig::default()));

    println!("  * Circuit Breaker: Initial state = {:?}", breaker.state());

    // Spawn high-throughput OTLP HTTP ingestion server on port 4318
    let otlp_port: u16 = env::var("OTLP_PORT")
        .ok()
        .and_then(|p| p.parse().ok())
        .unwrap_or(4318);
    let otlp_ring_buffer = Arc::clone(&ring_buffer);
    tokio::spawn(async move {
        let addr = format!("127.0.0.1:{}", otlp_port);
        match tokio::net::TcpListener::bind(&addr).await {
            Ok(listener) => {
                println!("  * OTLP HTTP Receiver: listening on http://{}/v1/traces", addr);
                loop {
                    if let Ok((mut socket, _)) = listener.accept().await {
                        let rb = Arc::clone(&otlp_ring_buffer);
                        tokio::spawn(async move {
                            use tokio::io::{AsyncReadExt, AsyncWriteExt};
                            let mut buf = vec![0u8; 65536];
                            if let Ok(n) = socket.read(&mut buf).await {
                                if n > 0 {
                                    let request = String::from_utf8_lossy(&buf[..n]);
                                    if request.starts_with("POST /v1/traces") {
                                        if let Some(body_idx) = request.find("\r\n\r\n") {
                                            let body = &request[body_idx + 4..];
                                            if let Ok(spans) = SpanCorrelator::parse_otlp_json(body) {
                                                for span in &spans {
                                                    let finding = SpanCorrelator::correlate_span(span, &rb);
                                                    println!(
                                                        "[airun-collector/otlp] Correlated Span: '{}' (Trace: '{}') -> {:.2}ms (SM: {:.1}%, PCIe: {:.1} MB/s, Bleed: {:?})",
                                                        finding.span_name,
                                                        finding.trace_id,
                                                        finding.duration_ms,
                                                        finding.hardware_analysis.avg_sm_util_pct,
                                                        finding.hardware_analysis.max_pcie_tx_mbs,
                                                        finding.hardware_analysis.detected_bottleneck
                                                    );
                                                }
                                            }
                                        }
                                        let response = "HTTP/1.1 200 OK\r\nContent-Type: application/json\r\nContent-Length: 19\r\nConnection: close\r\n\r\n{\"status\":\"success\"}";
                                        let _ = socket.write_all(response.as_bytes()).await;
                                    } else {
                                        let response = "HTTP/1.1 200 OK\r\nContent-Type: application/json\r\nContent-Length: 15\r\nConnection: close\r\n\r\n{\"status\":\"ok\"}";
                                        let _ = socket.write_all(response.as_bytes()).await;
                                    }
                                }
                            }
                        });
                    }
                }
            }
            Err(e) => {
                eprintln!("[!] Could not bind OTLP HTTP receiver on port {}: {}", otlp_port, e);
            }
        }
    });

    // Emit initial workload.started lifecycle event
    let start_payload = WorkloadLifecyclePayload {
        workload_name: "customer-support-agent".to_string(),
        workload_type: "agent".to_string(),
        node_id: node_name.clone(),
        pid: Some(std::process::id()),
        duration_ms: None,
        status: "running".to_string(),
    };
    if let Err(e) = publisher.publish_event(
        AirunEventType::WorkloadStarted,
        &format!("airun-collector/{}", node_name),
        Some("wl_customer_support".to_string()),
        None,
        start_payload,
    ).await {
        eprintln!("[!] Failed to publish workload.started: {}", e);
    }

    let mut count: u64 = 0;
    loop {
        count += 1;
        let batch_id = format!("batch_{}", count);
        let batch = scraper.collect_batch(&batch_id, &cluster_id);

        // Feed local ring buffer for microsecond zero-overhead time-window correlation
        ring_buffer.push_batch(batch.samples.clone());

        // Check for GPU thermal/PCIe anomaly and trigger gpu.alert
        for sample in &batch.samples {
            if sample.temperature_c > 82.0 || sample.pcie_errors > 0 {
                let alert = GpuAlertPayload {
                    node_id: node_name.clone(),
                    gpu_index: sample.gpu_id,
                    accelerator: accelerator_type.clone(),
                    alert_type: if sample.temperature_c > 82.0 {
                        "thermal_throttling".to_string()
                    } else {
                        "pcie_degradation".to_string()
                    },
                    severity: "warning".to_string(),
                    description: format!(
                        "Hardware anomaly on GPU {}: Temp={:.1}C, PCIe Errors={}",
                        sample.gpu_id, sample.temperature_c, sample.pcie_errors
                    ),
                    metric_value: sample.temperature_c as f64,
                    threshold_value: 82.0,
                    hourly_financial_bleed_usd: 8.50,
                };
                let _ = publisher.publish_event(
                    AirunEventType::GpuAlert,
                    &format!("airun-collector/{}", node_name),
                    None,
                    None,
                    alert,
                ).await;
            }
        }

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
