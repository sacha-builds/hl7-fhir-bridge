<script setup lang="ts">
import { ref } from 'vue';
import { useRouter } from 'vue-router';
import { storeToRefs } from 'pinia';
import { sendDemoMessage } from '@/api/bridge';
import { useMessageStore } from '@/stores/messages';

const router = useRouter();
const store = useMessageStore();
const { messages, loading } = storeToRefs(store);
const clearing = ref(false);
const sending = ref(false);
const lastSent = ref<string | null>(null);
const sendError = ref<string | null>(null);

function openMessage(id: string) {
  router.push({ name: 'message', params: { id } });
}

async function clearInbox() {
  if (!window.confirm('Clear the entire inbox and reset metrics?')) return;
  clearing.value = true;
  try {
    await store.clearInbox();
  } finally {
    clearing.value = false;
  }
}

async function sendDemo() {
  sending.value = true;
  sendError.value = null;
  try {
    const { fixture } = await sendDemoMessage();
    lastSent.value = fixture;
  } catch (err) {
    sendError.value = err instanceof Error ? err.message : 'failed';
  } finally {
    sending.value = false;
  }
}

function relativeTime(iso: string): string {
  const seconds = Math.max(0, Math.floor((Date.now() - new Date(iso).getTime()) / 1000));
  if (seconds < 60) return `${seconds}s ago`;
  if (seconds < 3600) return `${Math.floor(seconds / 60)}m ago`;
  if (seconds < 86400) return `${Math.floor(seconds / 3600)}h ago`;
  return new Date(iso).toLocaleString();
}

function chipClass(code: string): string {
  if (code === 'AA') return 'ok';
  if (code === 'AE' || code === 'AR') return 'error';
  return '';
}
</script>

<style scoped>
.header-row {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: 1rem;
  margin-bottom: 1rem;
}
.header-row h1 {
  margin-bottom: 0.25rem;
}
.header-row .muted {
  margin: 0;
}
.actions {
  display: flex;
  gap: 0.5rem;
  flex-wrap: wrap;
  align-items: center;
}
button.primary,
button.secondary {
  border-radius: 6px;
  padding: 0.4rem 0.8rem;
  font-size: 0.85rem;
  cursor: pointer;
}
button.primary {
  background: var(--accent);
  color: #0b0d12;
  border: 1px solid var(--accent);
  font-weight: 600;
}
button.primary:hover:not(:disabled) {
  filter: brightness(1.1);
}
button.secondary {
  background: var(--surface-2);
  color: var(--text);
  border: 1px solid var(--border-strong);
}
button.secondary:hover:not(:disabled) {
  background: var(--surface);
}
button.primary:disabled,
button.secondary:disabled {
  opacity: 0.6;
  cursor: default;
}
.hint {
  font-size: 0.75rem;
  color: var(--muted);
}
.hint.error {
  color: var(--error);
}
</style>

<template>
  <section>
    <div class="header-row">
      <div>
        <h1>Inbox</h1>
        <p class="muted">Live stream of HL7 v2 messages received over MLLP.</p>
      </div>
      <div class="actions">
        <button class="primary" :disabled="sending" @click="sendDemo">
          {{ sending ? 'Sending…' : 'Send demo message' }}
        </button>
        <button v-if="messages.length" class="secondary" :disabled="clearing" @click="clearInbox">
          {{ clearing ? 'Clearing…' : 'Clear inbox' }}
        </button>
      </div>
    </div>

    <p v-if="lastSent" class="hint">
      Sent <span class="mono">{{ lastSent }}</span> — watch for it below.
    </p>
    <p v-if="sendError" class="hint error">{{ sendError }}</p>

    <div class="card" style="padding: 0">
      <table v-if="messages.length">
        <thead>
          <tr>
            <th>Received</th>
            <th>Type</th>
            <th>ACK</th>
            <th>Resources</th>
            <th></th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="msg in messages" :key="msg.id" class="clickable" @click="openMessage(msg.id)">
            <td class="mono">{{ relativeTime(msg.received_at) }}</td>
            <td class="mono">{{ msg.message_type }}</td>
            <td>
              <span class="chip" :class="chipClass(msg.ack_code)">{{ msg.ack_code }}</span>
            </td>
            <td>{{ msg.resource_count }}</td>
            <td class="muted" style="font-size: 0.8rem">
              <span v-if="msg.error">{{ msg.error }}</span>
            </td>
          </tr>
        </tbody>
      </table>
      <p v-else-if="loading" style="padding: 2rem; text-align: center" class="muted">Loading…</p>
      <p v-else style="padding: 2rem; text-align: center" class="muted">
        No messages yet. Click <strong>Send demo message</strong> above, or stream v2 over MLLP to
        <span class="mono">localhost:2575</span>.
      </p>
    </div>
  </section>
</template>
