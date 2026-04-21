<script setup lang="ts">
defineProps<{ leftTitle?: string; rightTitle?: string }>();
</script>

<template>
  <div class="split">
    <section class="pane">
      <h3 v-if="leftTitle">{{ leftTitle }}</h3>
      <slot name="left" />
    </section>
    <section class="pane">
      <h3 v-if="rightTitle">{{ rightTitle }}</h3>
      <slot name="right" />
    </section>
  </div>
</template>

<style scoped>
.split {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 1rem;
}
@media (max-width: 880px) {
  .split {
    grid-template-columns: 1fr;
  }
}
.pane {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
  min-width: 0;
}
</style>
