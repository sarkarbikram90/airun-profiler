# Deploying `airun` on Azure Kubernetes Service (AKS) & Real-World API Profiling Guide

This guide walks you through:
1. **Real-World API Instrumentation**: Profiling real Azure OpenAI Service, Google Gemini, and Anthropic Claude workloads.
2. **Azure AKS Deployment**: Deploying the interactive `airun` executive dashboard and Rust collector on Azure Kubernetes Service.
3. **Sharing the Live URL**: Generating an Azure Application Gateway Ingress Controller (AGIC) or Azure Load Balancer public URL for your ML Director and engineering team.
4. **NVIDIA DCGM Telemetry on AKS GPU Node Pools**: Capturing 10Hz GPU telemetry (H100, A100, T4) to detect silicon stalls and financial compute bleed.

---

## Part 1: Real-World Multi-Model API Profiling

`airun` allows you to profile real live API calls with zero guesswork. We provide a complete runnable multi-model pipeline in [`examples/live_multi_model_agent.py`](../examples/live_multi_model_agent.py).

### 1. Set Your API Keys
```bash
# Azure OpenAI Credentials
export AZURE_OPENAI_API_KEY="your-azure-api-key"
export AZURE_OPENAI_ENDPOINT="https://your-resource-name.openai.azure.com/"
export AZURE_OPENAI_DEPLOYMENT_NAME="gpt-4o"

# Other Providers
export GEMINI_API_KEY="AIzaSy..."
export ANTHROPIC_API_KEY="sk-ant-..."
```

### 2. Run the Real-World Agent Pipeline
```bash
python examples/live_multi_model_agent.py "Analyze inference economics for agentic AI"
```

### 3. How Different Providers are Instrumented in Code

#### A. Azure OpenAI Service (`gpt-4o`, `gpt-4o-mini`, `o1`)
```python
import os
from openai import AzureOpenAI
from airun import trace, SpanKind, set_span_tokens

client = AzureOpenAI(
    azure_endpoint=os.environ["AZURE_OPENAI_ENDPOINT"],
    api_key=os.environ["AZURE_OPENAI_API_KEY"],
    api_version="2024-08-01-preview",
)

@trace(kind=SpanKind.LLM, model="gpt-4o", provider="azure_openai")
def call_azure_openai(prompt: str) -> str:
    response = client.chat.completions.create(
        model=os.environ["AZURE_OPENAI_DEPLOYMENT_NAME"],
        messages=[{"role": "user", "content": prompt}]
    )
    # Record actual token usage returned by Azure OpenAI
    set_span_tokens(
        input_tokens=response.usage.prompt_tokens,
        output_tokens=response.usage.completion_tokens,
    )
    return response.choices[0].message.content
```

#### B. Anthropic Claude (`claude-3-5-sonnet`, `claude-3-5-haiku`)
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

#### C. Google Gemini (`gemini-1.5-flash`, `gemini-1.5-pro`)
```python
import google.generativeai as genai
from airun import trace, SpanKind, set_span_tokens

@trace(kind=SpanKind.LLM, model="gemini-1.5-flash", provider="google")
def call_gemini(prompt: str) -> str:
    model = genai.GenerativeModel("gemini-1.5-flash")
    response = model.generate_content(prompt)
    
    set_span_tokens(
        input_tokens=response.usage_metadata.prompt_token_count,
        output_tokens=response.usage_metadata.candidates_token_count,
    )
    return response.text
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

## Part 3: Deploying on Azure Kubernetes Service (AKS)

All AKS Kubernetes manifests are ready in [`deploy/kubernetes/aks/`](../deploy/kubernetes/aks/).

### Step 1: Create or Connect to Your AKS Cluster

If you already have an existing AKS cluster, ensure your `kubectl` context is configured:
```bash
az aks get-credentials \
  --resource-group <YOUR_RESOURCE_GROUP> \
  --name <YOUR_CLUSTER_NAME>
```

#### (Optional) Creating a Fresh AKS Cluster with GPU Acceleration

To create an AKS cluster with an NVIDIA GPU node pool (e.g. A100 or H100):

```bash
# 1. Create AKS Cluster with Application Gateway Ingress Controller (AGIC)
az aks create \
  --resource-group airun-rg \
  --name airun-aks-cluster \
  --node-count 2 \
  --node-vm-size Standard_D4s_v5 \
  --enable-managed-identity \
  --enable-addons ingress-appgw \
  --appgw-name airun-appgw \
  --appgw-subnet-cidr "10.2.0.0/24" \
  --generate-ssh-keys

# 2. Add an NVIDIA GPU Node Pool (e.g. Standard_NC24ads_A100_v4 or Standard_NC8as_T4_v3)
az aks nodepool add \
  --resource-group airun-rg \
  --cluster-name airun-aks-cluster \
  --name gpunodepool \
  --node-count 1 \
  --node-vm-size Standard_NC24ads_A100_v4 \
  --enable-cluster-autoscaler \
  --min-count 1 \
  --max-count 4
```

> **Note**: AKS automated GPU driver installation ensures NVIDIA drivers and the DCGM kernel socket (`/var/run/nvidia-dcgm`) are available for the `airun-gpu-agent` DaemonSet.

---

### Step 2: Apply the `airun` AKS Manifests

Deploy the entire stack with Kustomize:
```bash
kubectl apply -k deploy/kubernetes/aks/
```

This single command automatically deploys:
1. **`PersistentVolumeClaim`** (`airun-trace-pvc`): 20GB Azure Premium SSD Disk (`managed-csi-premium`).
2. **`Deployment`** (`airun-dashboard`): Runs `ghcr.io/sarkarbikram90/airun-tracing:latest` with the executive web dashboard.
3. **`Service`** (`airun-service`): Exposes port 80 to the internal cluster network.
4. **`Ingress`** (`airun-aks-ingress`): Configures the Azure Application Gateway Ingress Controller (AGIC) with `/healthz` probing.
5. **`DaemonSet`** (`airun-gpu-agent`): Deploys the Rust collector on GPU nodes to scrape DCGM metrics at 10Hz and ingest OTLP spans on port `4318`.

---

### Step 3: Retrieve the Public URL for Your ML Director

Wait ~2 minutes for Azure Application Gateway provisioning and backend health probes to become healthy, then run:

```bash
kubectl get ingress airun-aks-ingress
```

Output:
```text
NAME                CLASS   HOSTS   ADDRESS          PORTS   AGE
airun-aks-ingress   <none>  *       20.84.142.60     80      2m
```

Copy the address under `ADDRESS`:
👉 **`http://20.84.142.60`**

Send this URL directly to your ML Director! They can immediately open it in any browser to inspect live trace DAGs, cost breakdowns, Pareto frontiers, and hardware utilization gauges.

---

## Part 4: Sending Traces to the Centralized Server

Once `airun` is deployed on AKS, your AI applications running inside or outside the cluster can stream telemetry directly:

### Inside the AKS Cluster (Kubernetes DNS)
```bash
export OTEL_EXPORTER_OTLP_ENDPOINT="http://airun-service.default.svc.cluster.local:8080"
```

### Outside the Cluster (Public Application Gateway IP)
```bash
export OTEL_EXPORTER_OTLP_ENDPOINT="http://20.84.142.60:80"
```

### Profile Your Python Workload
```python
import os
from airun import trace

# Runs will now automatically stream telemetry to your AKS dashboard
with trace("financial_agent_aks"):
    # Your agent code
    pass
```

---

## Part 5: Diagnosing GPU Silicon Waste on AKS

With the `airun-gpu-agent` DaemonSet running on your AKS GPU nodes, you can run hardware-level diagnostics directly:

```bash
# Analyze hardware stalls (Dataloader starvation, NCCL stalls, PCIe saturation)
airun waste --hardware

# Output will display:
# - Model FLOPs Utilization (MFU %)
# - GPU SM Active Cycles % vs VRAM Memory Bandwidth
# - Real-time financial bleed ($/hour and $/week on Azure VM hourly rates)
# - Exact remediation actions (e.g. pin_memory=True, num_workers tuning)
```
