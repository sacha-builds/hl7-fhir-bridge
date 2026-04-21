<script setup lang="ts">
import { ref } from 'vue';
import { useRouter } from 'vue-router';
import { storeToRefs } from 'pinia';
import { useMessageStore } from '@/stores/messages';

const router = useRouter();
const store = useMessageStore();
const { messages, loading } = storeToRefs(store);
const clearing = ref(false);

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
button.secondary {
  background: var(--surface-2);
  color: var(--text);
  border: 1px solid var(--border-strong);
  border-radius: 6px;
  padding: 0.4rem 0.8rem;
  font-size: 0.85rem;
  cursor: pointer;
}
button.secondary:hover:not(:disabled) {
  background: var(--surface);
}
button.secondary:disabled {
  opacity: 0.6;
  cursor: default;
}
</style>

<template>
  <section>
    <div class="header-row">
      <div>
        <h1>Inbox</h1>
        <p class="muted">Live stream of HL7 v2 messages received over MLLP.</p>
      </div>
      <button v-if="messages.length" class="secondary" :disabled="clearing" @click="clearInbox">
        {{ clearing ? 'Clearing…' : 'Clear inbox' }}
      </button>
    </div>

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
        No messages yet. Send one over MLLP to <span class="mono">localhost:2575</span> or POST to
        <span class="mono">/v2/replay</span>.
      </p>
    </div>
  </section>
</template>
