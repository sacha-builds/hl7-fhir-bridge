<script setup lang="ts">
import { computed } from 'vue';

const props = defineProps<{ raw: string }>();

interface Segment {
  name: string;
  rest: string;
}

const segments = computed<Segment[]>(() =>
  props.raw
    .replace(/\r\n/g, '\r')
    .replace(/\n/g, '\r')
    .split('\r')
    .filter((s) => s.length >= 3)
    .map((s) => ({ name: s.slice(0, 3), rest: s.slice(3) })),
);
</script>

<template>
  <pre class="code-block v2-view">
    <div v-for="(seg, i) in segments" :key="i" class="segment">
      <span class="seg-name">{{ seg.name }}</span><span class="seg-rest">{{ seg.rest }}</span>
    </div>
  </pre>
</template>

<style scoped>
.v2-view {
  display: block;
}
.segment {
  display: block;
}
.seg-name {
  color: var(--accent-2);
  font-weight: 600;
}
.seg-rest {
  color: var(--text);
}
</style>
