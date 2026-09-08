/**
 * airun TypeScript Control Plane & API Gateway
 * Serves enterprise REST/WebSocket APIs backed by PostgreSQL and Pub/Sub event streaming.
 */

import express, { Request, Response } from 'express';
import {
  GoldenSignals,
  HardwareBleedReport,
  Recommendation,
  WorkloadEconomicsReport,
} from './types.js';

const app = express();
const port = process.env.PORT || 4000;

app.use(express.json());

// Health check probe
app.get('/healthz', (_req: Request, res: Response) => {
  res.json({
    status: 'ok',
    service: '@airun/control-plane',
    version: '0.1.3',
    timestamp: new Date().toISOString(),
  });
});

// GET /api/v1/golden-signals
app.get('/api/v1/golden-signals', (_req: Request, res: Response) => {
  const signals: GoldenSignals = {
    economics: {
      costPerEffectiveGpuHourUsd: 87.59,
      costPer1mTokensUsd: 1.5647,
      financialBleedHourlyUsd: 5.82,
      totalWastedSpendUsd: 14.20,
      wastePercentage: 20.8,
    },
    efficiency: {
      mfuPct: 48.5,
      achievedTflops: 480.0,
      gpuSmUtilizationPct: 78.0,
      memoryBandwidthUtilizationPct: 65.0,
      pcieUtilizationPct: 42.0,
    },
    reliability: {
      jobFailureRatePct: 0.0,
      meanTimeToRecoveryMs: 0,
      retryCount: 1,
      checkpointFrequencyMin: 15.0,
    },
    infrastructure: {
      powerDrawWatts: 350.0,
      thermalThrottling: false,
      pcieErrorCount: 0,
      networkRetransmitsPct: 0.02,
      pue: 1.20,
    },
  };
  res.json(signals);
});

// GET /api/v1/recommendations
app.get('/api/v1/recommendations', (_req: Request, res: Response) => {
  const recs: Recommendation[] = [
    {
      recommendationId: 'rec_01',
      workloadId: 'wl_llama3_70b_finetune',
      category: 'framework_overhead',
      title: 'Mitigate Framework Eager-Mode Overhead',
      action: "Compile graph via 'torch.compile(model, mode=\"reduce-overhead\")' or capture CUDA Graphs.",
      potentialWeeklySavingsUsd: 564.0,
      potentialMonthlySavingsUsd: 2442.0,
      estimatedEfficiencyGainPct: 12.0,
      status: 'open',
      createdAt: new Date().toISOString(),
    },
    {
      recommendationId: 'rec_02',
      workloadId: 'wl_customer_support',
      category: 'model_routing',
      title: 'Route Simple Inquiries to Efficient Frontier Model',
      action: 'Route 73% of requests to cheaper model based on Pareto frontier eval.',
      potentialWeeklySavingsUsd: 4067.0,
      potentialMonthlySavingsUsd: 17430.0,
      estimatedEfficiencyGainPct: 31.0,
      status: 'open',
      createdAt: new Date().toISOString(),
    },
  ];
  res.json(recs);
});

// GET /api/v1/workloads/:id/waste
app.get('/api/v1/workloads/:id/waste', (req: Request, res: Response) => {
  const workloadId = req.params.id;
  const report: WorkloadEconomicsReport = {
    workloadId,
    workloadName: workloadId === 'customer-support-agent' ? 'customer-support-agent' : `workload-${workloadId}`,
    monthlySpendUsd: 84210.0,
    potentialWasteUsd: 17430.0,
    wastePercentage: 20.7,
    topIssue: '42% of cost from researcher agent',
    rootCause: 'Large prompt context + expensive model',
    recommendation: 'Route 73% of requests to cheaper model',
    expectedImpact: {
      cost: '-31%',
      latency: '-18%',
      quality: '-0.4%',
    },
  };
  res.json(report);
});

// GET /api/v1/hardware/waste
app.get('/api/v1/hardware/waste', (req: Request, res: Response) => {
  const traceId = (req.query.traceId as string) || '5664cdc8';
  const accelerator = (req.query.accelerator as string) || 'h100';

  const report: HardwareBleedReport = {
    workloadName: 'finetune-7b-v3',
    traceId,
    accelerator: `8x ${accelerator.toUpperCase()}`,
    numGpus: 8,
    primaryBottleneck: 'Dataloader Starvation (CPU/IO Bound)',
    bottleneckCategory: 'dataloader_starvation',
    symptom: 'GPU SM active cycles dropped to 38.2% (idle stalls) while PCIe TX was idle (<400 MB/s)',
    rootCause: 'Worker process I/O wait during mini-batch tensor assembly',
    remediationAction: 'Increase DataLoader num_workers=8 and set pin_memory=True',
    hourlyBleedUsd: 16.95,
    weeklyBleedUsd: 2847.20,
    monthlyBleedUsd: 12204.0,
    expectedImpact: {
      throughputGain: '+31%',
      weeklyCostSavings: '$967.00',
      wasteReduction: '-82%',
    },
  };
  res.json(report);
});

// GET /api/v1/waste (Standard legacy endpoint)
app.get('/api/v1/waste', (req: Request, res: Response) => {
  const accelerator = (req.query.accelerator as string) || 'h100';
  const gpus = parseInt((req.query.gpus as string) || '8', 10);

  res.json({
    workloadId: 'wl_active_fleet',
    accelerator: `${gpus}x ${accelerator.toUpperCase()}`,
    durationMs: 3600000.0,
    totalCostUsd: 28.0,
    totalWastedCostUsd: 5.82,
    totalWastePct: 20.8,
    hourlyBurnRateUsd: 28.0,
    hourlyFinancialBleedUsd: 5.82,
    topBottleneck: 'Framework Eager-Mode Overhead (Software Bound)',
    mfu: {
      acceleratorName: 'NVIDIA H100 SXM5',
      achievedTflops: 480.0,
      totalTheoreticalPeakTflops: 7912.0,
      mfuPct: 48.5,
      efficiencyRating: 'Optimal',
    },
    wasteComponents: [
      {
        category: 'framework_overhead',
        displayName: 'PyTorch Eager-Mode Overhead',
        wastePct: 12.0,
        hourlyBleedUsd: 3.36,
      },
      {
        category: 'nccl_overhead',
        displayName: 'NCCL Communication Wait',
        wastePct: 8.8,
        hourlyBleedUsd: 2.46,
      },
    ],
  });
});

if (process.env.NODE_ENV !== 'test') {
  app.listen(port, () => {
    console.log(`[airun-control-plane] Control plane API listening on port ${port}`);
  });
}

export default app;
