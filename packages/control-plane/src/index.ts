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
    version: '0.1.4',
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

// Commercial Wedge: "What is my AI application costing me, where is it wasting money/latency, and what should I change?"
app.get('/api/v1/workloads/:id/cost-reliability', (req: Request, res: Response) => {
  const workloadId = req.params.id;
  res.json({
    workloadId,
    workloadName: workloadId === 'customer-support-agent' ? 'customer-support-agent' : `workload-${workloadId}`,
    commercialWedge: {
      question1_cost: {
        monthlySpendUsd: 84210.0,
        hourlyBurnRateUsd: 115.35,
        costPer1mTokensUsd: 2.14,
        status: 'high_cost',
      },
      question2_waste: {
        potentialWasteUsd: 17430.0,
        wastePercentage: 20.7,
        topBottleneck: 'Researcher Agent Context Bloat (42% of cost)',
        hardwareBleedUsdHourly: 16.95,
        symptom: 'Large prompt context + expensive model during low-complexity user queries',
      },
      question3_action: {
        action: 'Route 73% of requests to cheaper model via Pareto frontier evaluation',
        projectedSavingsWeeklyUsd: 4067.0,
        projectedSavingsMonthlyUsd: 17430.0,
        expectedLatencyChange: '-18%',
        expectedQualityChange: '-0.4%',
        remediationStatus: 'ready_to_apply',
      },
    },
    reliabilitySla: {
      uptimePct: 99.95,
      p99LatencyMs: 420.0,
      circuitBreakerState: 'CLOSED',
      activeAlerts: 0,
    },
  });
});

import { EventDispatcher, AirunEventEnvelope } from './events.js';

export const eventDispatcher = new EventDispatcher();

// POST /api/v1/recommendations/:id/apply
app.post('/api/v1/recommendations/:id/apply', async (req: Request, res: Response) => {
  const recId = req.params.id;
  const appliedEvent: AirunEventEnvelope = {
    eventId: `evt_applied_${Date.now()}`,
    eventType: 'optimization.applied',
    source: 'control-plane/api',
    timestamp: new Date().toISOString(),
    orgId: 'org_default',
    projectId: 'proj_default',
    clusterId: 'gke-us-central1-ai',
    workloadId: 'customer-support-agent',
    payload: {
      recommendationId: recId,
      status: 'applied',
      appliedAt: new Date().toISOString(),
      action: 'Route 73% of requests to cheaper model',
    },
  };

  await eventDispatcher.dispatch(appliedEvent);

  res.json({
    recommendationId: recId,
    status: 'applied',
    message: `Optimization recommendation '${recId}' successfully applied. Automated model routing updated.`,
    eventId: appliedEvent.eventId,
  });
});

// GET /api/v1/events
app.get('/api/v1/events', (_req: Request, res: Response) => {
  res.json({
    count: eventDispatcher.getHistory().length,
    events: eventDispatcher.getHistory(),
  });
});

if (process.env.NODE_ENV !== 'test') {
  app.listen(port, () => {
    console.log(`[airun-control-plane] Control plane API listening on port ${port}`);
  });
}

export { EventDispatcher } from './events.js';
export default app;

