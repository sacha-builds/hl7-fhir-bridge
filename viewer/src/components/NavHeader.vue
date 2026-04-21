<script setup lang="ts">
import { useMessageStore } from '@/stores/messages';
import LiveDot from './LiveDot.vue';

const messages = useMessageStore();
</script>

<template>
  <header class="nav">
    <div class="nav-inner">
      <router-link to="/" class="brand">
        <span class="brand-icon">⚕</span>
        <span class="brand-text">HL7 v2 → FHIR Bridge</span>
      </router-link>

      <nav class="nav-links">
        <router-link to="/" exact-active-class="active">Inbox</router-link>
        <router-link to="/patients" active-class="active">Patients</router-link>
        <router-link to="/metrics" active-class="active">Metrics</router-link>
      </nav>

      <div class="nav-status">
        <LiveDot :state="messages.connState" />
        <span class="status-label">
          {{ messages.isLive ? 'live' : messages.connState }}
        </span>
      </div>
    </div>
  </header>
</template>

<style scoped>
.nav {
  border-bottom: 1px solid var(--border);
  background: var(--surface);
}
.nav-inner {
  max-width: 1200px;
  margin: 0 auto;
  padding: 0.75rem 1.5rem;
  display: flex;
  align-items: center;
  gap: 2rem;
}
.brand {
  color: var(--text);
  font-weight: 600;
  font-size: 0.95rem;
  display: flex;
  align-items: center;
  gap: 0.5rem;
}
.brand:hover {
  text-decoration: none;
}
.brand-icon {
  font-size: 1.1rem;
  color: var(--accent-2);
}
.nav-links {
  display: flex;
  gap: 1rem;
  flex: 1;
}
.nav-links a {
  color: var(--muted);
  font-size: 0.9rem;
  padding: 0.25rem 0;
}
.nav-links a.active,
.nav-links a:hover {
  color: var(--text);
  text-decoration: none;
}
.nav-status {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  font-size: 0.8rem;
  color: var(--muted);
}
.status-label {
  font-family: ui-monospace, SFMono-Regular, Menlo, monospace;
  font-size: 0.75rem;
}
</style>
