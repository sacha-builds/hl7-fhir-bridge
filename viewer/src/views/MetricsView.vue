<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref } from 'vue';
import { getMetrics, type MetricsSnapshot } from '@/api/bridge';

const snapshot = ref<MetricsSnapshot | null>(null);
const error = ref<string | null>(null);
let pollHandle: number | null = null;

async function refresh() {
  try {
    snapshot.value = await getMetrics();
    error.value = null;
  } catch (err) {
    error.value = err instanceof Error ? err.message : 'failed';
  }
}

onMounted(async () => {
  await refresh();
  pollHandle = window.setInterval(refresh, 2000);
});

onBeforeUnmount(() => {
  if (pollHandle !== null) window.clearInterval(pollHandle);
});

function formatUptime(seconds: number): string {
  const s = Math.floor(seconds);
  const h = Math.floor(s / 3600);
  const m = Math.floor((s % 3600) / 60);
  const r = s % 60;
  if (h > 0) return `${h}h ${m}m ${r}s`;
  if (m > 0) return `${m}m ${r}s`;
  return `${r}s`;
}

const successRate = computed(() => {
  if (!snapshot.value || snapshot.value.messages_total === 0) return null;
  const aa = snapshot.value.messages_by_ack_code['AA'] ?? 0;
  return Math.round((aa / snapshot.value.messages_total) * 100);
});

const totalResources = computed(() => {
  if (!snapshot.value) return 0;
  return Object.values(snapshot.value.resources_written).reduce((a, b) => a + b, 0);
});
</script>

<template>
  <section>
    <h1>Metrics</h1>
    <p class="muted">Live in-memory counters from the bridge. Polls every 2s.</p>

    <p v-if="error" class="muted">{{ error }}</p>

    <div v-if="snapshot" class="tile-grid">
      <div class="tile">
        <div class="tile-label">Uptime</div>
        <div class="tile-value">{{ formatUptime(snapshot.uptime_seconds) }}</div>
      </div>
      <div class="tile">
        <div class="tile-label">Messages processed</div>
        <div class="tile-value">{{ snapshot.messages_total }}</div>
      </div>
      <div class="tile">
        <div class="tile-label">Accept rate</div>
        <div class="tile-value">
          <template v-if="successRate !== null">{{ successRate }}%</template>
          <template v-else>—</template>
        </div>
      </div>
      <div class="tile">
        <div class="tile-label">Resources written</div>
        <div class="tile-value">{{ totalResources }}</div>
      </div>
    </div>

    <div v-if="snapshot" class="card">
      <h2>By message type</h2>
      <table>
        <thead>
          <tr>
            <th>Type</th>
            <th style="text-align: right">Count</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="(count, type) in snapshot.messages_by_type" :key="type">
            <td class="mono">{{ type }}</td>
            <td style="text-align: right">{{ count }}</td>
          </tr>
        </tbody>
      </table>
    </div>

    <div v-if="snapshot" class="card">
      <h2>By ACK code</h2>
      <table>
        <thead>
          <tr>
            <th>ACK</th>
            <th style="text-align: right">Count</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="(count, code) in snapshot.messages_by_ack_code" :key="code">
            <td>
              <span class="chip" :class="code === 'AA' ? 'ok' : 'error'">{{ code }}</span>
            </td>
            <td style="text-align: right">{{ count }}</td>
          </tr>
        </tbody>
      </table>
    </div>

    <div v-if="snapshot" class="card">
      <h2>FHIR resources written</h2>
      <table v-if="totalResources > 0">
        <thead>
          <tr>
            <th>Resource</th>
            <th style="text-align: right">Count</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="(count, type) in snapshot.resources_written" :key="type">
            <td>{{ type }}</td>
            <td style="text-align: right">{{ count }}</td>
          </tr>
        </tbody>
      </table>
      <p v-else class="muted">None yet.</p>
    </div>

    <div
      v-if="snapshot && Object.keys(snapshot.validation_issues_by_severity).length > 0"
      class="card"
    >
      <h2>Validation issues</h2>
      <table>
        <thead>
          <tr>
            <th>Severity</th>
            <th style="text-align: right">Count</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="(count, severity) in snapshot.validation_issues_by_severity" :key="severity">
            <td>
              <span class="chip" :class="severity === 'error' ? 'error' : 'warn'">
                {{ severity }}
              </span>
            </td>
            <td style="text-align: right">{{ count }}</td>
          </tr>
        </tbody>
      </table>
    </div>
  </section>
</template>

<style scoped>
.tile-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
  gap: 1rem;
  margin-bottom: 1rem;
}
.tile {
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: 10px;
  padding: 1rem 1.25rem;
  display: flex;
  flex-direction: column;
  gap: 0.35rem;
}
.tile-label {
  font-size: 0.75rem;
  text-transform: uppercase;
  letter-spacing: 0.05em;
  color: var(--muted);
}
.tile-value {
  font-size: 1.75rem;
  font-weight: 600;
  font-variant-numeric: tabular-nums;
}
</style>
