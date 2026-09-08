# Deploying `airun` on Google Kubernetes Engine (GCP GKE) & Real-World API Profiling Guide

This guide walks you through:
1. **Real-World API Instrumentation**: Profiling real OpenAI, Google Gemini, and Anthropic Claude workloads.
2. **GCP GKE Deployment**: Deploying the interactive `airun` executive dashboard and Rust collector on Google Kubernetes Engine.
3. **Sharing the Live URL**: Generating a Google Cloud HTTP(S) Load Balancer external IP/URL for your ML Director and engineering team.
4. **NVIDIA DCGM Telemetry on GKE GPU Node Pools**: Capturing 10Hz GPU telemetry (H100, A100, L4) to detect silicon stalls and financial bleed.

---

## Part 1: Real-World Multi-Model API Profiling

`airun` allows you to profile real live API calls with zero guesswork. We provide a complete runnable multi-model pipeline in [`examples/live_multi_model_agent.py`](../examples/live_multi_model_agent.py).

### 1. Set Your API Keys
```bash
export OPENAI_API_KEY="sk-proj-..."
export GEMINI_API_KEY="AIzaSy..."
export ANTHROPIC_API_KEY="sk-ant-..."
```

### 2. Run the Real-World Agent Pipeline
```bash
python examples/live_multi_model_agent.py "Analyze inference economics for agentic AI"
```

### 3. How Different Providers are Instrumented in Code

#### A. Google Gemini (`gemini-1.5-flash`, `gemini-1.5-pro`, `gemini-2.0-flash`)
```python
import google.generativeai as genai
from airun import trace, SpanKind, set_span_tokens

genai.configure(api_key=os.environ["GEMINI_API_KEY"])

@trace(kind=SpanKind.LLM, model="gemini-1.5-flash", provider="google")
def call_gemini(prompt: str) -> str:
    model = genai.GenerativeModel("gemini-1.5-flash")
    response = model.generate_content(prompt)
    
    # Record Gemini token usage metadata
    set_span_tokens(
        input_tokens=response.usage_metadata.prompt_token_count,
        output_tokens=response.usage_metadata.candidates_token_count,
    )
    return response.text
```

#### B. OpenAI (`gpt-4o`, `gpt-4o-mini`, `o1`, `o3-mini`)
```python
from openai import OpenAI
from airun import trace, SpanKind, set_span_tokens

client = OpenAI()

@trace(kind=SpanKind.LLM, model="gpt-4o", provider="openai")
def call_openai(prompt: str) -> str:
    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[{"role": "user", "content": prompt}]
    )
    # Record actual token usage returned by OpenAI
    set_span_tokens(
        input_tokens=response.usage.prompt_tokens,
        output_tokens=response.usage.completion_tokens,
    )
    return response.choices[0].message.content
```

#### C. Anthropic Claude (`claude-3-5-sonnet`, `claude-3-5-haiku`)
```python
import anthropic
from airun import trace, SpanKind, set_span_tokens

client = anthropic.Anthropic()

@trace(kind=SpanKind.LLM, model="claude-3-5-haiku-20241022", provider="anthropic")
def call_claude(prompt: str) -> str:
    response = client.messages.create(
        model="claude-3-5-haiku-20241022",
        max_tokens=500,
        messages=[{"role": "user", "content": prompt}]
    )
    # Record Anthropic token usage
    set_span_tokens(
        input_tokens=response.usage.input_tokens,
        output_tokens=response.usage.output_tokens,
    )
    return response.content[0].text
```

---

## Part 2: Interactive Web Dashboard

`airun` includes a built-in executive dashboard that visualizes:
- **High-level KPIs**: Total spend, cost per successful outcome, total tokens, avg latency.
- **Trace DAG & Waterfall**: Critical-path scheduling and concurrency speedup.
- **Golden Signals Hierarchy**: Economics (CFO), Efficiency (ML Eng), Reliability (Platform), Infrastructure (Hardware).
- **The Efficient Frontier**: Pareto-optimal model comparisons across Quality vs Cost vs Latency.
- **The AI Breaker Box**: Circuit breaker states (`CLOSED`, `OPEN`, `HALF_OPEN`) with one-click DR failover simulations.

### Test the Dashboard Locally
```bash
airun ui --port 8080
# Or: python -m airun ui
```
Open **[http://localhost:8080](http://localhost:8080)** in your browser!

---

## Part 3: Deploying on Google Kubernetes Engine (GCP GKE)

All GKE Kubernetes manifests are ready in [`deploy/kubernetes/gke/`](../deploy/kubernetes/gke/).

### Step 1: Create or Connect to Your GKE Cluster

If you already have an existing GKE cluster, ensure your `kubectl` context is configured:
```bash
gcloud container clusters get-credentials <YOUR_CLUSTER_NAME> \
  --zone us-central1-a \
  --project <YOUR_GCP_PROJECT_ID>
```

#### (Optional) Creating a Fresh GKE Cluster with GPU Acceleration

To create a production GKE Standard cluster with an NVIDIA GPU node pool:

```bash
# 1. Create GKE Cluster Control Plane
gcloud container clusters create airun-cluster \
  --region us-central1 \
  --release-channel regular \
  --enable-ip-alias \
  --num-nodes 2 \
  --machine-type e2-standard-4

# 2. Add an NVIDIA GPU Node Pool (e.g. NVIDIA L4 or H100/A100)
gcloud container node-pools create gpu-pool \
  --cluster airun-cluster \
  --region us-central1 \
  --machine-type g2-standard-8 \
  --accelerator type=nvidia-l4,count=1,gpu-driver-version=default \
  --num-nodes 1 \
  --enable-autoscaling --min-nodes 1 --max-nodes 4
```

> **Note**: GKE automatically manages the NVIDIA GPU drivers and DCGM kernel socket when `gpu-driver-version=default` is specified.

---

### Step 2: Reserve a Static Global External IP Address

Reserve a static IP for the Google Cloud HTTP(S) Load Balancer:
```bash
gcloud compute addresses create airun-static-ip --global
```

Verify the reserved IP address:
```bash
gcloud compute addresses describe airun-static-ip --global --format="value(address)"
# Example output: 34.149.120.45
```

---

### Step 3: Apply the `airun` GKE Manifests

Deploy the entire stack with Kustomize:
```bash
kubectl apply -k deploy/kubernetes/gke/
```

This single command automatically deploys:
1. **`PersistentVolumeClaim`** (`airun-trace-pvc`): 20GB Compute Engine Persistent Disk (`standard-rwo`).
2. **`BackendConfig`** (`airun-backendconfig`): Configures Google Cloud Load Balancer HTTP health checking (`/healthz` on port 8080).
3. **`Deployment`** (`airun-dashboard`): Runs `ghcr.io/sarkarbikram90/airun-profiler:latest` with the executive web dashboard.
4. **`Service`** (`airun-service`): Uses Network Endpoint Groups (NEG) for direct container routing.
5. **`Ingress`** (`airun-gke-ingress`): Provisions a Google Cloud HTTP(S) Load Balancer bound to `airun-static-ip`.
6. **`DaemonSet`** (`airun-gpu-agent`): Deploys the Rust collector on GPU nodes to scrape DCGM at 10Hz and receive OTLP spans on port `4318`.

---

### Step 4: Retrieve the Public URL for Your ML Director

Wait 2–3 minutes for Google Cloud Load Balancer health checks and forwarding rules to initialize, then run:

```bash
kubectl get ingress airun-gke-ingress
```

Output:
```text
NAME                CLASS    HOSTS   ADDRESS          PORTS   AGE
airun-gke-ingress   <none>   *       34.149.120.45    80      3m
```

Copy the address under `ADDRESS`:
👉 **`http://34.149.120.45`**

Send this URL directly to your ML Director! They can immediately open it in any browser to inspect live trace DAGs, cost breakdowns, Pareto frontiers, and hardware utilization gauges.

---

## Part 5: Sending Traces to the Centralized Server

Once `airun` is deployed on GKE, your AI applications running inside or outside the cluster can stream telemetry directly:

### Inside the GKE Cluster (Kubernetes DNS)
```bash
export OTEL_EXPORTER_OTLP_ENDPOINT="http://airun-service.default.svc.cluster.local:8080"
```

### Outside the Cluster (Public Load Balancer)
```bash
export OTEL_EXPORTER_OTLP_ENDPOINT="http://34.149.120.45:80"
```

### Profile Your Python Workload
```python
import os
from airun import trace

# Runs will now automatically stream telemetry to your GKE dashboard
with trace("financial_agent_gke"):
    # Your agent code
    pass
```

---

## Part 6: Diagnosing GPU Silicon Waste on GKE

With the `airun-gpu-agent` DaemonSet running on your GKE GPU nodes, you can run hardware-level diagnostics directly:

```bash
# Analyze hardware stalls (Dataloader starvation, NCCL stalls, PCIe saturation)
airun waste --hardware

# Output will display:
# - Model FLOPs Utilization (MFU %)
# - GPU SM Active Cycles % vs VRAM Memory Bandwidth
# - Real-time financial bleed ($/hour and $/week)
# - Exact remediation actions (e.g. pin_memory=True, num_workers tuning)
```
