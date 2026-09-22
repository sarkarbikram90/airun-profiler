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
import { PostgresStore } from './db.js';

const app = express();
const port = process.env.PORT || 4000;

app.use(express.json());

export const dbStore = new PostgresStore();
dbStore.init().catch((err) => {
  console.warn('[ControlPlane] dbStore.init non-fatal warning:', err);
});

// Health check probe
app.get('/healthz', async (_req: Request, res: Response) => {
  const dbHealth = await dbStore.getHealth();
  res.json({
    status: 'ok',
    service: '@airun/control-plane',
    version: '0.1.7',
    timestamp: new Date().toISOString(),
    database: dbHealth,
  });
});

// GET /api/v1/golden-signals
app.get('/api/v1/golden-signals', async (_req: Request, res: Response) => {
  const signals = await dbStore.getGoldenSignals();
  res.json(signals);
});

// GET /api/v1/recommendations
app.get('/api/v1/recommendations', async (_req: Request, res: Response) => {
  const recs = await dbStore.getRecommendations();
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
  await dbStore.applyRecommendation(recId);

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

// POST /api/v1/runs
app.post('/api/v1/runs', async (req: Request, res: Response) => {
  const run = req.body;
  if (!run.runId || !run.workloadId) {
    return res.status(400).json({ error: 'runId and workloadId are required' });
  }
  await dbStore.insertRun(run);
  res.status(201).json({ status: 'created', runId: run.runId });
});

// POST /v1/traces (Standard OTLP HTTP Ingestion)
app.post('/v1/traces', async (req: Request, res: Response) => {
  const payload = req.body;
  const resourceSpans = payload?.resourceSpans || [];
  const ingestedRunIds: string[] = [];

  for (const rs of resourceSpans) {
    for (const ss of rs.scopeSpans || []) {
      for (const s of ss.spans || []) {
        const traceId = s.traceId || `tr_${Date.now()}`;
        const runId = `run_${traceId.slice(0, 16)}`;
        await dbStore.insertRun({
          runId,
          workloadId: 'otlp-workload',
          traceId,
          status: s.status?.code === 2 ? 'failed' : 'completed',
          startedAt: new Date().toISOString(),
          durationMs: 120.0,
          criticalPathMs: 100.0,
          totalTokens: 1000,
          totalCostUsd: 0.005,
          wastedCostUsd: 0.0,
          mfuPct: 45.0,
          achievedTflops: 400.0,
        });
        ingestedRunIds.push(runId);
      }
    }
  }

  res.json({
    status: 'success',
    ingestedRuns: ingestedRunIds,
    count: ingestedRunIds.length,
  });
});

// GET /api/v1/events
app.get('/api/v1/events', (_req: Request, res: Response) => {
  res.json({
    count: eventDispatcher.getHistory().length,
    events: eventDispatcher.getHistory(),
  });
});

// GET /api/v1/federation/clusters
app.get('/api/v1/federation/clusters', async (_req: Request, res: Response) => {
  const clusters = await dbStore.getFederatedClusters();
  res.json({
    status: 'ok',
    count: clusters.length,
    clusters,
  });
});

// GET /api/v1/federation/overview
app.get('/api/v1/federation/overview', async (_req: Request, res: Response) => {
  const overview = await dbStore.getFederationOverview();
  res.json({
    status: 'ok',
    overview,
  });
});

// POST /api/v1/federation/clusters
app.post('/api/v1/federation/clusters', async (req: Request, res: Response) => {
  const cluster = req.body;
  if (!cluster.clusterId || !cluster.name || !cluster.provider) {
    res.status(400).json({ error: 'Missing required cluster fields (clusterId, name, provider).' });
    return;
  }
  const saved = await dbStore.upsertFederatedCluster({
    ...cluster,
    lastHeartbeat: new Date().toISOString(),
  });
  res.status(201).json({ status: 'registered', cluster: saved });
});

// POST /api/v1/federation/placement
app.post('/api/v1/federation/placement', async (req: Request, res: Response) => {
  const { workloadType, minGpus } = req.body;
  const placement = await dbStore.recommendPlacement(workloadType || 'generic_ai_workload', minGpus || 8);
  res.json({ status: 'ok', placement });
});

import http from 'node:http';
import { WebSocketServer, WebSocket } from 'ws';

export const server = http.createServer(app);
export const wss = new WebSocketServer({ server, path: '/ws/live' });

wss.on('connection', (ws) => {
  ws.send(JSON.stringify({ type: 'connected', service: '@airun/control-plane', timestamp: new Date().toISOString() }));
});

export function broadcastEvent(event: unknown): void {
  const msg = JSON.stringify(event);
  for (const client of wss.clients) {
    if (client.readyState === WebSocket.OPEN) {
      client.send(msg);
    }
  }
}

eventDispatcher.on('*', (event: AirunEventEnvelope) => {
  broadcastEvent(event);
});

const isTestEnv = process.env.NODE_ENV === 'test' || process.argv.some((arg) => arg.includes('test'));

if (!isTestEnv) {
  server.listen(port, () => {
    console.log(`[airun-control-plane] Control plane API & WebSockets listening on port ${port}`);
  });
}

export { EventDispatcher } from './events.js';
export default app;

