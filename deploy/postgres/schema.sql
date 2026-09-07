-- ==============================================================================
-- airun: System of Record PostgreSQL Relational Schema (State & Decisions)
-- ==============================================================================
-- Architectural Rule: High-frequency telemetry streams via Pub/Sub to Parquet/GCS.
-- PostgreSQL holds strictly operational state, metadata, policies, and decisions.

CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- 1. Organizations & Multi-tenancy
CREATE TABLE IF NOT EXISTS organizations (
    org_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name VARCHAR(255) NOT NULL,
    slug VARCHAR(100) UNIQUE NOT NULL,
    plan_tier VARCHAR(50) DEFAULT 'enterprise',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- 2. Projects
CREATE TABLE IF NOT EXISTS projects (
    project_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    org_id UUID NOT NULL REFERENCES organizations(org_id) ON DELETE CASCADE,
    name VARCHAR(255) NOT NULL,
    slug VARCHAR(100) NOT NULL,
    monthly_budget_usd NUMERIC(12, 2) DEFAULT 10000.00,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    UNIQUE (org_id, slug)
);

-- 3. Compute Clusters & Node Pools
CREATE TABLE IF NOT EXISTS clusters (
    cluster_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    org_id UUID NOT NULL REFERENCES organizations(org_id) ON DELETE CASCADE,
    name VARCHAR(255) NOT NULL,
    cloud_provider VARCHAR(50) NOT NULL DEFAULT 'gcp', -- 'gcp', 'aws', 'azure', 'lambda', 'on-prem'
    region VARCHAR(100) NOT NULL,
    accelerator_type VARCHAR(100) NOT NULL DEFAULT 'h100', -- 'h100', 'a100', 'b200', 'tpu_v5e', 'mi300x'
    total_gpus INTEGER NOT NULL DEFAULT 8,
    hourly_rate_usd NUMERIC(10, 2) NOT NULL DEFAULT 28.00,
    status VARCHAR(50) NOT NULL DEFAULT 'active',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- 4. Workloads (Training jobs, Inference endpoints, Multi-agent pipelines)
CREATE TABLE IF NOT EXISTS workloads (
    workload_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    project_id UUID NOT NULL REFERENCES projects(project_id) ON DELETE CASCADE,
    cluster_id UUID REFERENCES clusters(cluster_id) ON DELETE SET NULL,
    name VARCHAR(255) NOT NULL,
    workload_type VARCHAR(50) NOT NULL DEFAULT 'training', -- 'training', 'inference', 'eval', 'agent'
    model_name VARCHAR(255),
    parameters_billions NUMERIC(8, 2),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- 5. Runs (Individual executions or profiling sessions)
CREATE TABLE IF NOT EXISTS runs (
    run_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    workload_id UUID NOT NULL REFERENCES workloads(workload_id) ON DELETE CASCADE,
    trace_id VARCHAR(64) UNIQUE NOT NULL,
    status VARCHAR(50) NOT NULL DEFAULT 'completed', -- 'completed', 'failed', 'timeout', 'running'
    started_at TIMESTAMP WITH TIME ZONE NOT NULL,
    completed_at TIMESTAMP WITH TIME ZONE,
    duration_ms NUMERIC(14, 2) NOT NULL DEFAULT 0.0,
    critical_path_ms NUMERIC(14, 2) NOT NULL DEFAULT 0.0,
    total_tokens INTEGER DEFAULT 0,
    total_cost_usd NUMERIC(10, 6) DEFAULT 0.0,
    wasted_cost_usd NUMERIC(10, 6) DEFAULT 0.0,
    mfu_pct NUMERIC(6, 2) DEFAULT 0.0,
    achieved_tflops NUMERIC(10, 2) DEFAULT 0.0,
    quality_score NUMERIC(5, 4),
    summary_metadata JSONB DEFAULT '{}'::jsonb
);

-- 6. Cost Records & Financial Bleed
CREATE TABLE IF NOT EXISTS cost_records (
    record_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    run_id UUID NOT NULL REFERENCES runs(run_id) ON DELETE CASCADE,
    accelerator VARCHAR(100) NOT NULL,
    num_devices INTEGER NOT NULL DEFAULT 1,
    compute_cost_usd NUMERIC(10, 6) NOT NULL,
    energy_cost_usd NUMERIC(10, 6) NOT NULL DEFAULT 0.0,
    financial_bleed_hourly_usd NUMERIC(10, 2) NOT NULL DEFAULT 0.0,
    wasted_cost_usd NUMERIC(10, 6) NOT NULL DEFAULT 0.0,
    primary_waste_category VARCHAR(100), -- 'dataloader_starvation', 'nccl_overhead', 'pcie_bottleneck', 'framework_overhead'
    recorded_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- 7. Policies (SLA, Routing, Resilience & Breaker Rules)
CREATE TABLE IF NOT EXISTS policies (
    policy_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    project_id UUID NOT NULL REFERENCES projects(project_id) ON DELETE CASCADE,
    name VARCHAR(255) NOT NULL,
    policy_type VARCHAR(50) NOT NULL, -- 'breaker', 'routing', 'sla', 'budget'
    rule_config JSONB NOT NULL DEFAULT '{}'::jsonb,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- 8. Alerts & Threshold Violations
CREATE TABLE IF NOT EXISTS alerts (
    alert_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    project_id UUID NOT NULL REFERENCES projects(project_id) ON DELETE CASCADE,
    run_id UUID REFERENCES runs(run_id) ON DELETE SET NULL,
    severity VARCHAR(50) NOT NULL DEFAULT 'warning', -- 'info', 'warning', 'critical'
    title VARCHAR(255) NOT NULL,
    message TEXT NOT NULL,
    status VARCHAR(50) NOT NULL DEFAULT 'firing', -- 'firing', 'acknowledged', 'resolved'
    triggered_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    resolved_at TIMESTAMP WITH TIME ZONE
);

-- 9. Incidents & Causal Graph Attributions
CREATE TABLE IF NOT EXISTS incidents (
    incident_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    cluster_id UUID REFERENCES clusters(cluster_id) ON DELETE SET NULL,
    title VARCHAR(255) NOT NULL,
    root_cause_type VARCHAR(100) NOT NULL, -- 'network_fabric', 'pcie_degradation', 'thermal_throttle'
    total_wasted_cost_usd NUMERIC(12, 2) DEFAULT 0.0,
    causal_chain JSONB NOT NULL DEFAULT '[]'::jsonb,
    remediation_action TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- 10. Recommendations & Projected Optimization ROI
CREATE TABLE IF NOT EXISTS recommendations (
    recommendation_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    workload_id UUID NOT NULL REFERENCES workloads(workload_id) ON DELETE CASCADE,
    category VARCHAR(100) NOT NULL, -- 'dataloader_starvation', 'nccl_overhead', 'framework_overhead', 'model_switch'
    title VARCHAR(255) NOT NULL,
    action TEXT NOT NULL,
    potential_weekly_savings_usd NUMERIC(10, 2) DEFAULT 0.0,
    potential_monthly_savings_usd NUMERIC(10, 2) DEFAULT 0.0,
    estimated_efficiency_gain_pct NUMERIC(5, 2) DEFAULT 0.0,
    status VARCHAR(50) DEFAULT 'open', -- 'open', 'applied', 'dismissed'
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Indexes for high-performance control plane queries
CREATE INDEX IF NOT EXISTS idx_runs_workload_id ON runs(workload_id);
CREATE INDEX IF NOT EXISTS idx_runs_trace_id ON runs(trace_id);
CREATE INDEX IF NOT EXISTS idx_cost_records_run_id ON cost_records(run_id);
CREATE INDEX IF NOT EXISTS idx_recommendations_workload_id ON recommendations(workload_id);
CREATE INDEX IF NOT EXISTS idx_alerts_project_id ON alerts(project_id);
