//! airun-collector: Production Rust DaemonSet agent for NVIDIA DCGM & Kubernetes GPU telemetry.

mod dcgm;
mod pubsub;

use dcgm::DcgmScraper;
use pubsub::PubSubPublisher;
use std::env;
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
    println!("  airun-collector DaemonSet (Rust High-Throughput Data Plane)");
    println!("============================================================");
    println!("  * Node Name:    {}", node_name);
    println!("  * Cluster ID:   {}", cluster_id);
    println!("  * Accelerator:  {}x {}", num_gpus, accelerator_type);
    println!("  * Pub/Sub:      projects/{}/topics/{}", project_id, pubsub_topic);
    println!("  * Sample Rate:  1 Hz");
    println!("============================================================");

    let scraper = DcgmScraper::new(node_name.clone(), accelerator_type, num_gpus);
    let publisher = PubSubPublisher::new(pubsub_topic, project_id);

    let mut count: u64 = 0;
    loop {
        count += 1;
        let batch_id = format!("batch_{}", count);
        let batch = scraper.collect_batch(&batch_id, &cluster_id);

        if let Err(e) = publisher.publish_telemetry_batch(&batch).await {
            eprintln!("[!] Telemetry push failed: {}", e);
        }

        // 1-second scraping interval
        tokio::time::sleep(Duration::from_secs(1)).await;

        // In test/demo environment, yield after 5 batches if running non-daemon
        if env::var("AIRUN_TEST_MODE").is_ok() && count >= 5 {
            println!("[*] Test mode complete: 5 batches collected.");
            break;
        }
    }

    Ok(())
}
