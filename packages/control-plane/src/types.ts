/**
 * TypeScript Control Plane Data Contracts & PostgreSQL Schema Interfaces
 */

export interface Organization {
  orgId: string;
  name: string;
  slug: string;
  planTier: 'developer' | 'team' | 'enterprise';
  createdAt: string;
}

export interface Project {
  projectId: string;
  orgId: string;
  name: string;
  slug: string;
  monthlyBudgetUsd: number;
  createdAt: string;
}

export interface Cluster {
  clusterId: string;
  orgId: string;
  name: string;
  cloudProvider: 'gcp' | 'aws' | 'azure' | 'lambda' | 'on-prem';
  region: string;
  acceleratorType: 'h100' | 'a100' | 'b200' | 'tpu_v5e' | 'mi300x';
  totalGpus: number;
  hourlyRateUsd: number;
  status: 'active' | 'draining' | 'offline';
}

export interface Workload {
  workloadId: string;
  projectId: string;
  clusterId?: string;
  name: string;
  workloadType: 'training' | 'inference' | 'eval' | 'agent';
  modelName?: string;
  parametersBillions?: number;
  createdAt: string;
}

export interface Run {
  runId: string;
  workloadId: string;
  traceId: string;
  status: 'completed' | 'failed' | 'timeout' | 'running';
  startedAt: string;
  completedAt?: string;
  durationMs: number;
  criticalPathMs: number;
  totalTokens: number;
  totalCostUsd: number;
  wastedCostUsd: number;
  mfuPct: number;
  achievedTflops: number;
  qualityScore?: number;
}

export interface CostRecord {
  recordId: string;
  runId: string;
  accelerator: string;
  numDevices: number;
  computeCostUsd: number;
  energyCostUsd: number;
  financialBleedHourlyUsd: number;
  wastedCostUsd: number;
  primaryWasteCategory: 'dataloader_starvation' | 'nccl_overhead' | 'pcie_bottleneck' | 'framework_overhead';
  recordedAt: string;
}

export interface Recommendation {
  recommendationId: string;
  workloadId: string;
  category: string;
  title: string;
  action: string;
  potentialWeeklySavingsUsd: number;
  potentialMonthlySavingsUsd: number;
  estimatedEfficiencyGainPct: number;
  status: 'open' | 'applied' | 'dismissed';
  createdAt: string;
}

export interface HardwareBleedReport {
  workloadName: string;
  traceId: string;
  accelerator: string;
  numGpus: number;
  primaryBottleneck: string;
  bottleneckCategory: 'dataloader_starvation' | 'nccl_overhead' | 'pcie_bottleneck' | 'framework_overhead';
  symptom: string;
  rootCause: string;
  remediationAction: string;
  hourlyBleedUsd: number;
  weeklyBleedUsd: number;
  monthlyBleedUsd: number;
  expectedImpact: Record<string, string>;
}

export interface WorkloadEconomicsReport {
  workloadId: string;
  workloadName: string;
  monthlySpendUsd: number;
  potentialWasteUsd: number;
  wastePercentage: number;
  topIssue: string;
  rootCause: string;
  recommendation: string;
  expectedImpact: {
    cost: string;
    latency: string;
    quality: string;
  };
}

export interface GoldenSignals {
  economics: {
    costPerEffectiveGpuHourUsd: number;
    costPer1mTokensUsd?: number;
    financialBleedHourlyUsd: number;
    totalWastedSpendUsd: number;
    wastePercentage: number;
  };
  efficiency: {
    mfuPct: number;
    achievedTflops: number;
    gpuSmUtilizationPct: number;
    memoryBandwidthUtilizationPct: number;
    pcieUtilizationPct: number;
  };
  reliability: {
    jobFailureRatePct: number;
    meanTimeToRecoveryMs: number;
    retryCount: number;
    checkpointFrequencyMin: number;
  };
  infrastructure: {
    powerDrawWatts: number;
    thermalThrottling: boolean;
    pcieErrorCount: number;
    networkRetransmitsPct: number;
    pue: number;
  };
}
