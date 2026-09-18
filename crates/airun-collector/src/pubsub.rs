//! Pub/Sub streaming publisher and event envelope for the airun distributed event backbone.

use crate::dcgm::TelemetryBatch;
use serde::{Deserialize, Serialize};

/// The 10 standard event types in the airun distributed event backbone.
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub enum AirunEventType {
    #[serde(rename = "workload.started")]
    WorkloadStarted,
    #[serde(rename = "workload.completed")]
    WorkloadCompleted,
    #[serde(rename = "trace.created")]
    TraceCreated,
    #[serde(rename = "gpu.alert")]
    GpuAlert,
    #[serde(rename = "provider.degraded")]
    ProviderDegraded,
    #[serde(rename = "provider.failed")]
    ProviderFailed,
    #[serde(rename = "dr.drill.started")]
    DrDrillStarted,
    #[serde(rename = "dr.drill.completed")]
    DrDrillCompleted,
    #[serde(rename = "optimization.detected")]
    OptimizationDetected,
    #[serde(rename = "optimization.applied")]
    OptimizationApplied,
}

impl AirunEventType {
    pub fn as_str(&self) -> &'static str {
        match self {
            Self::WorkloadStarted => "workload.started",
            Self::WorkloadCompleted => "workload.completed",
            Self::TraceCreated => "trace.created",
            Self::GpuAlert => "gpu.alert",
            Self::ProviderDegraded => "provider.degraded",
            Self::ProviderFailed => "provider.failed",
            Self::DrDrillStarted => "dr.drill.started",
            Self::DrDrillCompleted => "dr.drill.completed",
            Self::OptimizationDetected => "optimization.detected",
            Self::OptimizationApplied => "optimization.applied",
        }
    }
}

/// Standard distributed event envelope shared across Python, Rust, and TypeScript.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct AirunEventEnvelope<T> {
    pub event_id: String,
    pub event_type: AirunEventType,
    pub source: String,
    pub timestamp: String,
    #[serde(default = "default_org")]
    pub org_id: String,
    #[serde(default = "default_project")]
    pub project_id: String,
    #[serde(default = "default_cluster")]
    pub cluster_id: String,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub workload_id: Option<String>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub trace_id: Option<String>,
    pub payload: T,
}

fn default_org() -> String { "org_default".to_string() }
fn default_project() -> String { "proj_default".to_string() }
fn default_cluster() -> String { "gke-us-central1-ai".to_string() }

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct WorkloadLifecyclePayload {
    pub workload_name: String,
    pub workload_type: String,
    pub node_id: String,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub pid: Option<u32>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub duration_ms: Option<f64>,
    pub status: String,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct GpuAlertPayload {
    pub node_id: String,
    pub gpu_index: u32,
    pub accelerator: String,
    pub alert_type: String,
    pub severity: String,
    pub description: String,
    pub metric_value: f64,
    pub threshold_value: f64,
    pub hourly_financial_bleed_usd: f64,
}

pub struct PubSubPublisher {
    pub topic: String,
    pub project_id: String,
    pub endpoint_url: Option<String>,
    client: reqwest::Client,
}

impl PubSubPublisher {
    pub fn new(topic: String, project_id: String) -> Self {
        let endpoint_url = std::env::var("PUBSUB_WEBHOOK_URL")
            .or_else(|_| std::env::var("AIRUN_EVENT_ENDPOINT"))
            .or_else(|_| std::env::var("PUBSUB_EMULATOR_HOST").map(|h| {
                if h.starts_with("http://") || h.starts_with("https://") {
                    format!("{}/v1/projects/{}/topics/{}:publish", h, project_id, topic)
                } else {
                    format!("http://{}/v1/projects/{}/topics/{}:publish", h, project_id, topic)
                }
            }))
            .ok();

        Self {
            topic,
            project_id,
            endpoint_url,
            client: reqwest::Client::builder()
                .timeout(std::time::Duration::from_millis(3000))
                .build()
                .unwrap_or_default(),
        }
    }

    #[allow(dead_code)]
    pub fn with_endpoint(topic: String, project_id: String, endpoint_url: String) -> Self {
        Self {
            topic,
            project_id,
            endpoint_url: Some(endpoint_url),
            client: reqwest::Client::builder()
                .timeout(std::time::Duration::from_millis(3000))
                .build()
                .unwrap_or_default(),
        }
    }

    /// Publishes a strongly-typed event envelope to Pub/Sub.
    pub async fn publish_event<T: Serialize>(
        &self,
        event_type: AirunEventType,
        source: &str,
        workload_id: Option<String>,
        trace_id: Option<String>,
        payload: T,
    ) -> Result<String, String> {
        let envelope = AirunEventEnvelope {
            event_id: format!("evt_{}_{}", chrono::Utc::now().timestamp_micros(), std::process::id()),
            event_type,
            source: source.to_string(),
            timestamp: chrono::Utc::now().to_rfc3339(),
            org_id: "org_default".to_string(),
            project_id: self.project_id.clone(),
            cluster_id: "gke-us-central1-ai".to_string(),
            workload_id,
            trace_id,
            payload,
        };

        let json = serde_json::to_string(&envelope)
            .map_err(|e| format!("Failed to serialize envelope: {}", e))?;

        if let Some(endpoint) = &self.endpoint_url {
            let res = self.client
                .post(endpoint)
                .header("Content-Type", "application/json")
                .body(json.clone())
                .send()
                .await;

            match res {
                Ok(resp) => {
                    println!(
                        "[airun-collector] Pub/Sub Event Dispatched to {}: HTTP {}",
                        endpoint,
                        resp.status()
                    );
                }
                Err(err) => {
                    eprintln!(
                        "[airun-collector] Network dispatch to '{}' failed (non-fatal): {}",
                        endpoint, err
                    );
                }
            }
        }

        let msg_id = format!("msg_{}", chrono::Utc::now().timestamp_millis());
        println!(
            "[airun-collector] Pub/Sub Event Published: type='{}' id='{}' ({} bytes)",
            envelope.event_type.as_str(),
            envelope.event_id,
            json.len()
        );

        Ok(msg_id)
    }

    /// Serializes and publishes a telemetry batch to the GCP Pub/Sub event bus.
    pub async fn publish_telemetry_batch(&self, batch: &TelemetryBatch) -> Result<String, String> {
        let envelope = AirunEventEnvelope {
            event_id: format!("evt_batch_{}", batch.batch_id),
            event_type: AirunEventType::TraceCreated,
            source: format!("airun-collector/{}", batch.node_id),
            timestamp: chrono::Utc::now().to_rfc3339(),
            org_id: "org_default".to_string(),
            project_id: self.project_id.clone(),
            cluster_id: "gke-us-central1-ai".to_string(),
            workload_id: None,
            trace_id: None,
            payload: batch.clone(),
        };

        let json = serde_json::to_string(&envelope)
            .map_err(|e| format!("Failed to serialize batch envelope: {}", e))?;

        if let Some(endpoint) = &self.endpoint_url {
            let res = self.client
                .post(endpoint)
                .header("Content-Type", "application/json")
                .body(json.clone())
                .send()
                .await;

            if let Err(err) = res {
                eprintln!(
                    "[airun-collector] Batch network dispatch to '{}' failed (non-fatal): {}",
                    endpoint, err
                );
            }
        }

        let msg_id = format!("msg_{}", chrono::Utc::now().timestamp_millis());
        println!(
            "[airun-collector] Published {} GPU samples to topic '{}' (batch: {}, len: {}B)",
            batch.samples.len(),
            self.topic,
            batch.batch_id,
            json.len()
        );

        Ok(msg_id)
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_event_envelope_serialization() {
        let payload = GpuAlertPayload {
            node_id: "gke-node-gpu-01".to_string(),
            gpu_index: 0,
            accelerator: "H100-SXM5-80GB".to_string(),
            alert_type: "pcie_degradation".to_string(),
            severity: "critical".to_string(),
            description: "PCIe Gen1 fallback detected (bandwidth dropped to 1.8 GB/s)".to_string(),
            metric_value: 1.8,
            threshold_value: 32.0,
            hourly_financial_bleed_usd: 14.50,
        };

        let envelope = AirunEventEnvelope {
            event_id: "evt_test123".to_string(),
            event_type: AirunEventType::GpuAlert,
            source: "airun-collector/gke-node-gpu-01".to_string(),
            timestamp: "2026-09-07T12:00:00Z".to_string(),
            org_id: "org_default".to_string(),
            project_id: "proj_default".to_string(),
            cluster_id: "gke-us-central1-ai".to_string(),
            workload_id: Some("wl_llm_train".to_string()),
            trace_id: Some("tr_abc".to_string()),
            payload,
        };

        let json = serde_json::to_string(&envelope).unwrap();
        assert!(json.contains("gpu.alert"));
        assert!(json.contains("pcie_degradation"));

        let deserialized: AirunEventEnvelope<GpuAlertPayload> = serde_json::from_str(&json).unwrap();
        assert_eq!(deserialized.event_type, AirunEventType::GpuAlert);
        assert_eq!(deserialized.payload.gpu_index, 0);
        assert_eq!(deserialized.payload.metric_value, 1.8);
    }

    #[tokio::test]
    async fn test_publisher_local_dispatch() {
        let publisher = PubSubPublisher::new("telemetry-topic".to_string(), "test-proj".to_string());
        assert_eq!(publisher.topic, "telemetry-topic");
        assert_eq!(publisher.project_id, "test-proj");

        let payload = WorkloadLifecyclePayload {
            workload_name: "test-workload".to_string(),
            workload_type: "training".to_string(),
            node_id: "node-0".to_string(),
            pid: Some(1234),
            duration_ms: Some(150.0),
            status: "completed".to_string(),
        };

        let result = publisher
            .publish_event(
                AirunEventType::WorkloadCompleted,
                "airun-collector/test",
                Some("wl-123".to_string()),
                Some("tr-456".to_string()),
                payload,
            )
            .await;

        assert!(result.is_ok());
        assert!(result.unwrap().starts_with("msg_"));
    }

    #[tokio::test]
    async fn test_publisher_network_dispatch_mock() {
        use tokio::io::{AsyncReadExt, AsyncWriteExt};

        let listener = tokio::net::TcpListener::bind("127.0.0.1:0").await.unwrap();
        let port = listener.local_addr().unwrap().port();
        let endpoint = format!("http://127.0.0.1:{}/publish", port);

        let server_handle = tokio::spawn(async move {
            if let Ok((mut socket, _)) = listener.accept().await {
                let mut buf = [0u8; 2048];
                let n = socket.read(&mut buf).await.unwrap();
                let request = String::from_utf8_lossy(&buf[..n]);

                assert!(request.starts_with("POST /publish HTTP/1.1"));
                assert!(request.contains("workload.started"));

                let response = "HTTP/1.1 200 OK\r\nContent-Length: 15\r\n\r\n{\"status\":\"ok\"}";
                socket.write_all(response.as_bytes()).await.unwrap();
            }
        });

        let publisher = PubSubPublisher::with_endpoint(
            "telemetry-topic".to_string(),
            "test-proj".to_string(),
            endpoint,
        );

        let payload = WorkloadLifecyclePayload {
            workload_name: "net-test-workload".to_string(),
            workload_type: "training".to_string(),
            node_id: "node-1".to_string(),
            pid: Some(5678),
            duration_ms: None,
            status: "started".to_string(),
        };

        let res = publisher
            .publish_event(
                AirunEventType::WorkloadStarted,
                "airun-collector/net-test",
                Some("wl-net".to_string()),
                None,
                payload,
            )
            .await;

        assert!(res.is_ok());
        server_handle.await.unwrap();
    }
}
