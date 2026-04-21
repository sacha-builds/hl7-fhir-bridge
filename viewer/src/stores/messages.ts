import { defineStore } from 'pinia';
import {
  getMessage,
  listMessages,
  openEventStream,
  type BridgeEvent,
  type MessageDetail,
  type MessageSummary,
} from '@/api/bridge';

type ConnState = 'disconnected' | 'connecting' | 'connected';

interface State {
  messages: MessageSummary[];
  details: Record<string, MessageDetail>;
  loading: boolean;
  connState: ConnState;
  ws: WebSocket | null;
  reconnectTimer: number | null;
}

export const useMessageStore = defineStore('messages', {
  state: (): State => ({
    messages: [],
    details: {},
    loading: false,
    connState: 'disconnected',
    ws: null,
    reconnectTimer: null,
  }),

  getters: {
    isLive: (state) => state.connState === 'connected',
  },

  actions: {
    async fetchInitial(): Promise<void> {
      this.loading = true;
      try {
        this.messages = await listMessages(100);
      } finally {
        this.loading = false;
      }
    },

    async ensureDetail(id: string): Promise<MessageDetail> {
      const cached = this.details[id];
      if (cached) return cached;
      const detail = await getMessage(id);
      this.details[id] = detail;
      return detail;
    },

    connectLive(): void {
      if (this.ws) return;
      this.connState = 'connecting';
      const ws = openEventStream((event: BridgeEvent) => this.handleEvent(event));
      ws.addEventListener('open', () => {
        this.connState = 'connected';
      });
      ws.addEventListener('close', () => {
        this.connState = 'disconnected';
        this.ws = null;
        this.scheduleReconnect();
      });
      ws.addEventListener('error', () => {
        this.connState = 'disconnected';
      });
      this.ws = ws;
    },

    disconnectLive(): void {
      if (this.reconnectTimer !== null) {
        window.clearTimeout(this.reconnectTimer);
        this.reconnectTimer = null;
      }
      this.ws?.close();
      this.ws = null;
      this.connState = 'disconnected';
    },

    scheduleReconnect(): void {
      if (this.reconnectTimer !== null) return;
      this.reconnectTimer = window.setTimeout(() => {
        this.reconnectTimer = null;
        this.connectLive();
      }, 2000);
    },

    handleEvent(event: BridgeEvent): void {
      if (event.event === 'message.received') {
        this.messages = [event.data, ...this.messages].slice(0, 200);
      }
    },
  },
});
