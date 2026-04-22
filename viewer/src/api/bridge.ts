export interface ResourceRecord {
  resource_type: string;
  operation: 'create' | 'update';
  identifier_query: string | null;
  resource: Record<string, unknown>;
}

export interface ValidationIssue {
  resource_type: string;
  severity: 'error' | 'warning';
  path: string;
  message: string;
}

export interface MessageSummary {
  id: string;
  received_at: string;
  message_type: string;
  ack_code: string;
  resource_count: number;
  error: string | null;
}

export interface MessageDetail extends MessageSummary {
  raw_v2: string;
  ack: string;
  resources: ResourceRecord[];
  validation_issues: ValidationIssue[];
}

export type BridgeEvent =
  | { event: 'hello'; data: { version: string } }
  | { event: 'message.received'; data: MessageSummary }
  | { event: 'messages.cleared'; data: Record<string, never> };

export interface MetricsSnapshot {
  uptime_seconds: number;
  started_at: string;
  messages_total: number;
  messages_by_type: Record<string, number>;
  messages_by_ack_code: Record<string, number>;
  resources_written: Record<string, number>;
  validation_issues_by_severity: Record<string, number>;
}

const BASE = import.meta.env.VITE_BRIDGE_API_URL ?? 'http://localhost:8000';

export async function listMessages(limit = 100): Promise<MessageSummary[]> {
  const url = new URL(`${BASE}/v2/messages`);
  url.searchParams.set('limit', String(limit));
  const response = await fetch(url);
  if (!response.ok) throw new Error(`listMessages failed: ${response.status}`);
  return (await response.json()) as MessageSummary[];
}

export async function getMessage(id: string): Promise<MessageDetail> {
  const response = await fetch(`${BASE}/v2/messages/${id}`);
  if (!response.ok) throw new Error(`getMessage failed: ${response.status}`);
  return (await response.json()) as MessageDetail;
}

export async function replay(rawV2: string): Promise<{ ack: string }> {
  const response = await fetch(`${BASE}/v2/replay`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ message: rawV2 }),
  });
  if (!response.ok) throw new Error(`replay failed: ${response.status}`);
  return (await response.json()) as { ack: string };
}

export async function getHealth(): Promise<{ status: string; version: string }> {
  const response = await fetch(`${BASE}/health`);
  if (!response.ok) throw new Error(`health failed: ${response.status}`);
  return (await response.json()) as { status: string; version: string };
}

export async function getMetrics(): Promise<MetricsSnapshot> {
  const response = await fetch(`${BASE}/metrics`);
  if (!response.ok) throw new Error(`metrics failed: ${response.status}`);
  return (await response.json()) as MetricsSnapshot;
}

export async function clearMessages(): Promise<void> {
  const response = await fetch(`${BASE}/v2/messages`, { method: 'DELETE' });
  if (!response.ok) throw new Error(`clearMessages failed: ${response.status}`);
}

export async function sendDemoMessage(): Promise<{ fixture: string | null }> {
  const response = await fetch(`${BASE}/v2/demo/random`, { method: 'POST' });
  if (!response.ok) throw new Error(`sendDemoMessage failed: ${response.status}`);
  return (await response.json()) as { fixture: string | null };
}

export function openEventStream(onEvent: (event: BridgeEvent) => void): WebSocket {
  const wsUrl = BASE.replace(/^http/, 'ws') + '/ws/messages';
  const ws = new WebSocket(wsUrl);
  ws.addEventListener('message', (evt) => {
    try {
      const parsed = JSON.parse(evt.data) as BridgeEvent;
      onEvent(parsed);
    } catch (err) {
      console.error('bad ws payload', err);
    }
  });
  return ws;
}
