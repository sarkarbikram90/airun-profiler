/**
 * TypeScript Distributed Event Backbone Definitions
 * Standardized across Python intelligence plane, Rust data plane, and GKE Pub/Sub.
 */

export type AirunEventType =
  | 'workload.started'
  | 'workload.completed'
  | 'trace.created'
  | 'gpu.alert'
  | 'provider.degraded'
  | 'provider.failed'
  | 'dr.drill.started'
  | 'dr.drill.completed'
  | 'optimization.detected'
  | 'optimization.applied';

export interface AirunEventEnvelope<T = any> {
  eventId: string;
  eventType: AirunEventType;
  source: string;
  timestamp: string;
  orgId: string;
  projectId: string;
  clusterId: string;
  workloadId?: string;
  traceId?: string;
  payload: T;
}

export interface WorkloadLifecyclePayload {
  workloadName: string;
  workloadType: 'training' | 'inference' | 'eval' | 'agent';
  modelName?: string;
  nodeId?: string;
  pid?: number;
  durationMs?: number;
  status: 'running' | 'completed' | 'failed';
}

export interface GpuAlertPayload {
  nodeId: string;
  gpuIndex: number;
  accelerator: string;
  alertType: 'thermal_throttling' | 'pcie_degradation' | 'xid_error' | 'memory_saturation';
  severity: 'info' | 'warning' | 'critical';
  description: string;
  metricValue: number;
  thresholdValue: number;
  hourlyFinancialBleedUsd: number;
}

export interface OptimizationPayload {
  workloadName: string;
  traceId?: string;
  category: 'dataloader_starvation' | 'nccl_overhead' | 'pcie_bottleneck' | 'framework_overhead' | 'model_switch';
  title: string;
  rootCause: string;
  remediationAction: string;
  potentialWeeklySavingsUsd: number;
  potentialMonthlySavingsUsd: number;
  estimatedEfficiencyGainPct: number;
  status: 'open' | 'applied' | 'dismissed';
}

export type EventHandler<T = any> = (event: AirunEventEnvelope<T>) => Promise<void> | void;

export class EventDispatcher {
  private handlers: Map<string, EventHandler[]> = new Map();
  private history: AirunEventEnvelope[] = [];

  public on(eventType: AirunEventType | '*', handler: EventHandler): void {
    const list = this.handlers.get(eventType) || [];
    list.push(handler);
    this.handlers.set(eventType, list);
  }

  public async dispatch(event: AirunEventEnvelope): Promise<void> {
    this.history.push(event);

    const specificHandlers = this.handlers.get(event.eventType) || [];
    const wildcardHandlers = this.handlers.get('*') || [];

    for (const handler of [...specificHandlers, ...wildcardHandlers]) {
      try {
        await handler(event);
      } catch (err) {
        console.error(`[control-plane] Error executing handler for ${event.eventType}:`, err);
      }
    }
  }

  public getHistory(): AirunEventEnvelope[] {
    return [...this.history];
  }
}
