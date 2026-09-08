# Deploying `airun` on AWS EKS & Real-World API Profiling Guide

This guide walks you through:
1. **Real-World API Instrumentation**: Profiling real OpenAI, Google Gemini, and Anthropic Claude workloads.
2. **AWS EKS Deployment**: Deploying the interactive `airun` executive dashboard on Amazon EKS.
3. **Sharing the Live URL**: Generating an AWS Application Load Balancer (ALB) URL for your ML Director and engineering team.

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

#### A. OpenAI (`gpt-4o`, `gpt-4o-mini`, `o1`, `o3-mini`)
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

#### B. Google Gemini (`gemini-1.5-flash`, `gemini-1.5-pro`, `gemini-2.0-flash`)
```python
import google.generativeai as genai
from airun import trace, SpanKind, set_span_tokens

@trace(kind=SpanKind.LLM, model="gemini-1.5-flash", provider="google")
def call_gemini(prompt: str) -> str:
    model = genai.GenerativeModel("gemini-1.5-flash")
    response = model.generate_content(prompt)
    
    # Record Gemini usage metadata
    set_span_tokens(
        input_tokens=response.usage_metadata.prompt_token_count,
        output_tokens=response.usage_metadata.candidates_token_count,
    )
    return response.text
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
- **Severity-Graded Findings**: Highlighted `[CRITICAL]`, `[WARNING]`, and `[INFO]` optimization badges.

### Test the Dashboard Locally
```bash
airun ui --port 8080
# Or: python -m airun ui
```
Open **[http://localhost:8080](http://localhost:8080)** in your browser!

---

## Part 3: Deploying on AWS EKS (Amazon Elastic Kubernetes Service)

All Kubernetes manifests are ready in [`deploy/kubernetes/`](../deploy/kubernetes/).

### Step 1: Create or Connect to Your EKS Cluster
If you already have an EKS cluster, ensure your `kubectl` context is set:
```bash
aws eks update-kubeconfig --region us-east-1 --name <your-cluster-name>
```

*(If creating a fresh EKS cluster with `eksctl`)*:
```bash
eksctl create cluster \
  --name airun-cluster \
  --region us-east-1 \
  --nodegroup-name standard-workers \
  --node-type t3.medium \
  --nodes 2
```

### Step 2: Deploy the AWS Load Balancer Controller (if not already installed)
```bash
helm repo add eks https://aws.github.io/eks-charts
helm install aws-load-balancer-controller eks/aws-load-balancer-controller \
  -n kube-system \
  --set clusterName=airun-cluster
```

### Step 3: Apply the `airun` Kubernetes Manifests
Run the one-line deployment from the root of the repository:
```bash
kubectl apply -k deploy/kubernetes/
```

This creates:
- `PersistentVolumeClaim`: 10GB AWS EBS `gp3` storage for traces.
- `Deployment`: `airun-dashboard` running `ghcr.io/sarkarbikram90/airun-profiler:latest`.
- `Service`: `airun-service` on port 80.
- `Ingress`: AWS Application Load Balancer (ALB).

### Step 4: Retrieve the Public URL for Your ML Director
Wait ~1 minute for AWS ALB provisioning, then run:
```bash
kubectl get ingress airun-ingress
```

Output:
```text
NAME            CLASS   HOSTS   ADDRESS                                                                  PORTS   AGE
airun-ingress   alb     *       k8s-default-airuning-xxxxxxxxxx-1234567890.us-east-1.elb.amazonaws.com   80      90s
```

Copy the address under `ADDRESS`:
👉 **`http://k8s-default-airuning-xxxxxxxxxx-1234567890.us-east-1.elb.amazonaws.com`**

Send this URL directly to your ML Director! They can immediately open it in any browser to explore live trace DAGs, cost graphs, and optimization findings.

---

## Part 4: Sending Traces to the Centralized Server

Once `airun` is deployed on EKS, any team or automated pipeline can profile agent runs and inspect traces on the central server!
