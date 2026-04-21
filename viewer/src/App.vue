<script setup lang="ts">
import { onMounted, onBeforeUnmount } from 'vue';
import NavHeader from '@/components/NavHeader.vue';
import { useMessageStore } from '@/stores/messages';

const messages = useMessageStore();

onMounted(() => {
  messages.fetchInitial();
  messages.connectLive();
});

onBeforeUnmount(() => {
  messages.disconnectLive();
});
</script>

<template>
  <NavHeader />
  <main class="app-main">
    <router-view v-slot="{ Component }">
      <component :is="Component" />
    </router-view>
  </main>
</template>

<style scoped>
.app-main {
  max-width: 1200px;
  margin: 0 auto;
  padding: 1.5rem;
}
</style>
