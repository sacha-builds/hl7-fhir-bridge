<script setup lang="ts">
import { useRouter } from 'vue-router';
import { storeToRefs } from 'pinia';
import { useMessageStore } from '@/stores/messages';

const router = useRouter();
const store = useMessageStore();
const { messages, loading } = storeToRefs(store);

function openMessage(id: string) {
  router.push({ name: 'message', params: { id } });
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

<template>
  <section>
    <h1>Inbox</h1>
    <p class="muted">Live stream of HL7 v2 messages received over MLLP.</p>

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
