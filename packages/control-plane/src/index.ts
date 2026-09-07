/**
 * airun TypeScript Control Plane & API Gateway
 * Serves enterprise REST/WebSocket APIs backed by PostgreSQL and Pub/Sub event streaming.
 */

import express, { Request, Response } from 'express';
import { GoldenSignals, Recommendation } from './types.js';

const app = express();
const port = process.env.PORT || 4000;

app.use(express.json());

// Health check probe
app.get('/healthz', (_req: Request, res: Response) => {
  res.json({
    status: 'ok',
    service: '@airun/control-plane',
    version: '0.2.0',
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
      workloadId: 'wl_llama3_70b_finetune',
      category: 'nccl_overhead',
      title: 'Mitigate NCCL Communication Overhead',
      action: "Tune NCCL buffer sizes ('NCCL_BUFFSIZE=16777216') and enable gradient accumulation.",
      potentialWeeklySavingsUsd: 319.0,
      potentialMonthlySavingsUsd: 1381.0,
      estimatedEfficiencyGainPct: 6.8,
      status: 'open',
      createdAt: new Date().toISOString(),
    },
  ];
  res.json(recs);
});

// GET /api/v1/waste
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
  });
});

if (process.env.NODE_ENV !== 'test') {
  app.listen(port, () => {
    console.log(`[airun-control-plane] Listening on port ${port}`);
  });
}

export default app;
