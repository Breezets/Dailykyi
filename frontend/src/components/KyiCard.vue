<script setup lang="ts">
import { computed } from "vue";

const props = defineProps<{
  title: string;
  icon?: string;
  color?: string;
}>();

const borderColor = computed(() => props.color || "var(--kyi-primary)");
</script>

<template>
  <div class="kyi-card">
    <div class="kyi-card__header" :style="{ borderLeftColor: borderColor }">
      <span v-if="icon" class="kyi-card__icon">{{ icon }}</span>
      <span class="kyi-card__title">{{ title }}</span>
    </div>
    <div class="kyi-card__body">
      <slot />
    </div>
  </div>
</template>

<style scoped>
.kyi-card {
  background: var(--kyi-card-bg);
  border-radius: var(--kyi-border-radius);
  box-shadow: 0 4px 16px rgba(0, 0, 0, 0.04);
  overflow: hidden;
}

.kyi-card__header {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 16px 20px;
  font-size: 16px;
  font-weight: 600;
  color: var(--kyi-text);
  border-bottom: 1px solid #ebeef5;
  border-left-width: 4px;
  border-left-style: solid;
}

.kyi-card__icon {
  font-size: 18px;
}

.kyi-card__body {
  padding: 20px;
}
</style>
