<script setup lang="ts">
import { ref, watchEffect } from 'vue';
import { useMessageStore } from '@/stores/messages';
import type { MessageDetail } from '@/api/bridge';
import JsonView from '@/components/JsonView.vue';
import V2View from '@/components/V2View.vue';
import SplitPane from '@/components/SplitPane.vue';

const props = defineProps<{ id: string }>();
const store = useMessageStore();

const detail = ref<MessageDetail | null>(null);
const error = ref<string | null>(null);

watchEffect(async () => {
  detail.value = null;
  error.value = null;
  try {
    detail.value = await store.ensureDetail(props.id);
  } catch (err) {
    error.value = err instanceof Error ? err.message : 'failed to load message';
  }
});
</script>

<template>
  <section>
    <router-link to="/" class="muted">← Inbox</router-link>
    <h1 v-if="detail">{{ detail.message_type }}</h1>
    <p v-if="error" class="muted">{{ error }}</p>

    <div v-if="detail" class="meta-row">
      <span class="chip" :class="detail.ack_code === 'AA' ? 'ok' : 'error'">
        ACK {{ detail.ack_code }}
      </span>
      <span class="mono muted">{{ detail.received_at }}</span>
      <span class="muted">{{ detail.resource_count }} resource(s)</span>
    </div>

    <div v-if="detail && detail.validation_issues.length" class="card" style="margin-bottom: 1rem">
      <h3>Validation</h3>
      <ul class="issues">
        <li v-for="(issue, i) in detail.validation_issues" :key="i">
          <span class="chip" :class="issue.severity === 'error' ? 'error' : 'warn'">
            {{ issue.severity }}
          </span>
          <span class="mono">{{ issue.path }}</span>
          <span>{{ issue.message }}</span>
        </li>
      </ul>
    </div>

    <div v-if="detail" class="card">
      <SplitPane left-title="Raw HL7 v2" right-title="FHIR resources">
        <template #left>
          <V2View :raw="detail.raw_v2" />
        </template>
        <template #right>
          <div v-for="(r, i) in detail.resources" :key="i" class="resource-block">
            <div class="resource-header">
              <span class="chip">{{ r.operation }}</span>
              <span class="resource-type">{{ r.resource_type }}</span>
              <span v-if="r.identifier_query" class="mono muted">
                {{ r.identifier_query }}
              </span>
            </div>
            <JsonView :data="r.resource" />
          </div>
        </template>
      </SplitPane>
    </div>

    <div v-if="detail" class="card" style="margin-top: 1rem">
      <h3>ACK sent back</h3>
      <V2View :raw="detail.ack" />
    </div>
  </section>
</template>

<style scoped>
.meta-row {
  display: flex;
  gap: 1rem;
  align-items: center;
  margin-bottom: 1rem;
  font-size: 0.85rem;
}
.issues {
  list-style: none;
  padding: 0;
  margin: 0;
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
  font-size: 0.85rem;
}
.issues li {
  display: flex;
  gap: 0.75rem;
  align-items: center;
}
.resource-block + .resource-block {
  margin-top: 1rem;
}
.resource-header {
  display: flex;
  align-items: center;
  gap: 0.6rem;
  margin-bottom: 0.4rem;
}
.resource-type {
  font-weight: 600;
  font-size: 0.9rem;
}
</style>
