import { test, describe, before, after } from 'node:test';
import assert from 'node:assert';
import { server, dbStore, wss } from '../index.js';
import { PostgresStore } from '../db.js';
import { WebSocket } from 'ws';

describe('Control Plane, WebSockets & PostgresStore Integration', () => {
  let baseUrl: string;
  let wsUrl: string;

  before(async () => {
    await new Promise<void>((resolve) => {
      server.listen(0, () => {
        const addr = server.address();
        if (addr && typeof addr === 'object') {
          baseUrl = `http://127.0.0.1:${addr.port}`;
          wsUrl = `ws://127.0.0.1:${addr.port}/ws/live`;
        }
        resolve();
      });
    });
  });

  after(async () => {
    wss.close();
    await dbStore.close();
    await new Promise<void>((resolve) => {
      server.close(() => resolve());
    });
  });

  test('GET /healthz returns ok with database health info', async () => {
    const res = await fetch(`${baseUrl}/healthz`);
    assert.strictEqual(res.status, 200);
    const body = await res.json() as any;
    assert.strictEqual(body.status, 'ok');
    assert.strictEqual(body.service, '@airun/control-plane');
    assert.ok(body.database);
    assert.strictEqual(body.database.status, 'in-memory-fallback');
  });

  test('GET /api/v1/golden-signals returns valid metrics', async () => {
    const res = await fetch(`${baseUrl}/api/v1/golden-signals`);
    assert.strictEqual(res.status, 200);
    const body = await res.json() as any;
    assert.ok(body.economics);
    assert.ok(body.efficiency);
    assert.ok(body.reliability);
    assert.ok(body.infrastructure);
    assert.strictEqual(typeof body.economics.financialBleedHourlyUsd, 'number');
  });

  test('GET /api/v1/recommendations returns active recommendations', async () => {
    const res = await fetch(`${baseUrl}/api/v1/recommendations`);
    assert.strictEqual(res.status, 200);
    const recs = await res.json() as any[];
    assert.ok(Array.isArray(recs));
    assert.ok(recs.length >= 2);
    assert.strictEqual(recs[0].recommendationId, 'rec_01');
  });

  test('POST /api/v1/runs validates and stores a run', async () => {
    const runPayload = {
      runId: 'run_test_001',
      workloadId: 'wl_test_llm',
      traceId: 'tr_test_999',
      status: 'completed',
      startedAt: new Date().toISOString(),
      durationMs: 1240.5,
      criticalPathMs: 1100.2,
      totalTokens: 15000,
      totalCostUsd: 12.50,
      wastedCostUsd: 2.10,
      mfuPct: 52.4,
      achievedTflops: 512.0,
    };

    const res = await fetch(`${baseUrl}/api/v1/runs`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(runPayload),
    });

    assert.strictEqual(res.status, 201);
    const body = await res.json() as any;
    assert.strictEqual(body.status, 'created');
    assert.strictEqual(body.runId, 'run_test_001');
  });

  test('POST /v1/traces ingests OTLP resource spans', async () => {
    const otlpPayload = {
      resourceSpans: [
        {
          scopeSpans: [
            {
              spans: [
                {
                  traceId: 'tr_otlp_cp_test',
                  spanId: 'span_cp_1',
                  name: 'vllm_generation',
                  status: { code: 1 },
                },
              ],
            },
          ],
        },
      ],
    };

    const res = await fetch(`${baseUrl}/v1/traces`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(otlpPayload),
    });

    assert.strictEqual(res.status, 200);
    const body = await res.json() as any;
    assert.strictEqual(body.status, 'success');
    assert.strictEqual(body.count, 1);
  });

  test('WebSocket /ws/live streams real-time connection and event broadcast', async () => {
    const messages: any[] = [];
    const ws = new WebSocket(wsUrl);

    await new Promise<void>((resolve, reject) => {
      ws.on('open', () => resolve());
      ws.on('error', (err) => reject(err));
      ws.on('message', (data) => {
        messages.push(JSON.parse(data.toString()));
      });
    });

    assert.ok(messages.length >= 1);
    assert.strictEqual(messages[0].type, 'connected');

    // Trigger an applied recommendation to verify broadcast
    await fetch(`${baseUrl}/api/v1/recommendations/rec_01/apply`, {
      method: 'POST',
    });

    // Wait a brief moment for websocket message delivery
    await new Promise((resolve) => setTimeout(resolve, 50));

    const broadcastMsg = messages.find((m) => m.eventType === 'optimization.applied');
    assert.ok(broadcastMsg);
    assert.strictEqual(broadcastMsg.eventType, 'optimization.applied');
    ws.close();
  });

  test('PostgresStore standalone instance operates with in-memory fallback', async () => {
    const store = new PostgresStore();
    await store.init();
    const health = await store.getHealth();
    assert.strictEqual(health.status, 'in-memory-fallback');

    await store.insertRun({
      runId: 'run_direct_01',
      workloadId: 'wl_direct',
      traceId: 'tr_direct',
      status: 'completed',
      startedAt: new Date().toISOString(),
      durationMs: 500,
      criticalPathMs: 400,
      totalTokens: 2000,
      totalCostUsd: 1.5,
      wastedCostUsd: 0.3,
      mfuPct: 45.0,
      achievedTflops: 400.0,
    });

    const signals = await store.getGoldenSignals();
    assert.ok(signals.economics.costPerEffectiveGpuHourUsd > 0);
    await store.close();
  });

  test('GET /api/v1/federation/clusters returns multi-cloud clusters', async () => {
    const res = await fetch(`${baseUrl}/api/v1/federation/clusters`);
    assert.strictEqual(res.status, 200);
    const data = await res.json() as any;
    assert.strictEqual(data.status, 'ok');
    assert.ok(data.count >= 4);
    assert.ok(data.clusters.some((c: any) => c.provider === 'gcp-gke'));
    assert.ok(data.clusters.some((c: any) => c.provider === 'aws-eks'));
    assert.ok(data.clusters.some((c: any) => c.provider === 'azure-aks'));
    assert.ok(data.clusters.some((c: any) => c.provider === 'on-prem'));
  });

  test('GET /api/v1/federation/overview computes multi-cloud aggregates', async () => {
    const res = await fetch(`${baseUrl}/api/v1/federation/overview`);
    assert.strictEqual(res.status, 200);
    const data = await res.json() as any;
    assert.strictEqual(data.status, 'ok');
    assert.ok(data.overview.totalClusters >= 4);
    assert.ok(data.overview.totalGpus > 200);
    assert.ok(data.overview.aggregateHourlySpendUsd > 0);
    assert.ok(data.overview.globalAverageMfuPct > 40.0);
  });

  test('POST /api/v1/federation/clusters registers a new cluster heartbeat', async () => {
    const newCluster = {
      clusterId: 'lambda-us-west-h100',
      name: 'Lambda Cloud H100 Cluster',
      provider: 'on-prem',
      region: 'us-west-1',
      acceleratorType: 'H100-SXM5-80GB',
      totalGpus: 16,
      activeGpus: 16,
      hourlyRatePerGpu: 2.49,
      averageMfuPct: 50.0,
      averageBleedHourlyUsd: 4.50,
      healthStatus: 'healthy',
    };

    const res = await fetch(`${baseUrl}/api/v1/federation/clusters`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(newCluster),
    });

    assert.strictEqual(res.status, 201);
    const data = await res.json() as any;
    assert.strictEqual(data.status, 'registered');
    assert.strictEqual(data.cluster.clusterId, 'lambda-us-west-h100');
  });

  test('POST /api/v1/federation/placement recommends optimal cluster for workload', async () => {
    const res = await fetch(`${baseUrl}/api/v1/federation/placement`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ workloadType: 'llm_pretraining', minGpus: 16 }),
    });

    assert.strictEqual(res.status, 200);
    const data = await res.json() as any;
    assert.strictEqual(data.status, 'ok');
    assert.ok(data.placement.recommendedCluster);
    assert.ok(data.placement.reason.includes('Ranked #1'));
  });
});
