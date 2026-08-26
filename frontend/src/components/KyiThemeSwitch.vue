<script setup lang="ts">
import { useThemeStore } from "@/stores/theme";

const theme = useThemeStore();
</script>

<template>
  <div class="theme-switch">
    <button
      class="theme-btn theme-btn--22"
      :class="{ 'theme-btn--active': theme.is22 }"
      @click="theme.setTheme('22')"
    >
      22
    </button>
    <button
      class="theme-btn theme-btn--33"
      :class="{ 'theme-btn--active': theme.is33 }"
      @click="theme.setTheme('33')"
    >
      33
    </button>
  </div>
</template>

<style scoped>
.theme-switch {
  display: flex;
  gap: 8px;
  background: var(--kyi-bg);
  padding: 4px;
  border-radius: 10px;
}

.theme-btn {
  flex: 1;
  padding: 6px 0;
  border: none;
  border-radius: 8px;
  font-size: 13px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.18s ease;
  background: transparent;
  color: var(--kyi-text-secondary);
}

.theme-btn--22.theme-btn--active {
  background: var(--kyi-primary);
  color: #fff;
}

.theme-btn--33.theme-btn--active {
  background: var(--kyi-secondary);
  color: #fff;
}
</style>
