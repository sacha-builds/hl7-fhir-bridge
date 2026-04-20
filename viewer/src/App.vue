<script setup lang="ts">
import { ref, onMounted } from 'vue';

const bridgeApiUrl = import.meta.env.VITE_BRIDGE_API_URL ?? 'http://localhost:8000';
const fhirBaseUrl = import.meta.env.VITE_FHIR_BASE_URL ?? 'http://localhost:8080/fhir';

const bridgeStatus = ref<'checking' | 'ok' | 'unreachable'>('checking');
const bridgeVersion = ref<string | null>(null);

onMounted(async () => {
  try {
    const response = await fetch(`${bridgeApiUrl}/health`);
    if (!response.ok) throw new Error(`status ${response.status}`);
    const body = (await response.json()) as { status: string; version: string };
    bridgeStatus.value = body.status === 'ok' ? 'ok' : 'unreachable';
    bridgeVersion.value = body.version;
  } catch {
    bridgeStatus.value = 'unreachable';
  }
});
</script>

<template>
  <main>
    <header>
      <h1>HL7 v2 → FHIR Bridge Viewer</h1>
      <p class="subtitle">
        Phase 0 — scaffolding. Viewer shell is live; clinical features land in Phase 3.
      </p>
    </header>

    <section class="status-grid">
      <article class="status-card">
        <h2>Bridge service</h2>
        <p class="status" :data-state="bridgeStatus">
          <template v-if="bridgeStatus === 'checking'">Checking…</template>
          <template v-else-if="bridgeStatus === 'ok'"> Online — v{{ bridgeVersion }} </template>
          <template v-else>Unreachable</template>
        </p>
        <p class="endpoint">{{ bridgeApiUrl }}</p>
      </article>

      <article class="status-card">
        <h2>FHIR server</h2>
        <p class="endpoint">{{ fhirBaseUrl }}</p>
        <p class="muted">Local dev: HAPI FHIR via docker-compose. Deployed: Medplum cloud.</p>
      </article>
    </section>
  </main>
</template>

<style scoped>
main {
  max-width: 960px;
  margin: 0 auto;
  padding: 3rem 1.5rem;
}

header h1 {
  margin: 0 0 0.25rem;
  font-size: 1.75rem;
}

.subtitle {
  margin: 0 0 2rem;
  color: var(--muted);
}

.status-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(260px, 1fr));
  gap: 1rem;
}

.status-card {
  border: 1px solid var(--border);
  border-radius: 8px;
  padding: 1.25rem;
  background: var(--surface);
}

.status-card h2 {
  margin: 0 0 0.5rem;
  font-size: 1rem;
  font-weight: 600;
}

.status[data-state='ok'] {
  color: var(--ok);
}
.status[data-state='unreachable'] {
  color: var(--error);
}
.status[data-state='checking'] {
  color: var(--muted);
}

.endpoint {
  font-family: ui-monospace, SFMono-Regular, Menlo, monospace;
  font-size: 0.85rem;
  color: var(--muted);
  margin: 0.25rem 0;
}

.muted {
  color: var(--muted);
  font-size: 0.875rem;
  margin: 0.5rem 0 0;
}
</style>
