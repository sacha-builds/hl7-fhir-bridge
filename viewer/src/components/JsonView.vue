<script setup lang="ts">
import { computed } from 'vue';

const props = defineProps<{ data: unknown }>();

const formatted = computed(() => JSON.stringify(props.data, null, 2));
</script>

<template>
  <pre class="code-block json-view">{{ formatted }}</pre>
</template>

<style scoped>
.json-view {
  white-space: pre;
}
</style>
