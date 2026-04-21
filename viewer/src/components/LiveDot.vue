<script setup lang="ts">
defineProps<{ state: 'disconnected' | 'connecting' | 'connected' }>();
</script>

<template>
  <span class="dot" :data-state="state" aria-hidden="true"></span>
</template>

<style scoped>
.dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  display: inline-block;
  background: var(--muted-2);
}
.dot[data-state='connected'] {
  background: var(--ok);
  box-shadow: 0 0 0 3px color-mix(in srgb, var(--ok) 20%, transparent);
}
.dot[data-state='connecting'] {
  background: var(--warn);
  animation: pulse 1.2s infinite;
}
@keyframes pulse {
  0%,
  100% {
    opacity: 1;
  }
  50% {
    opacity: 0.4;
  }
}
</style>
