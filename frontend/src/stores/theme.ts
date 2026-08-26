import { defineStore } from "pinia";
import { ref, computed, watch } from "vue";

export type ThemeName = "22" | "33";

const STORAGE_KEY = "dailykyi_theme";

function applyTheme(theme: ThemeName): void {
  document.documentElement.dataset.theme = theme;
}

function loadTheme(): ThemeName {
  const saved = localStorage.getItem(STORAGE_KEY);
  return saved === "33" ? "33" : "22";
}

export const useThemeStore = defineStore("theme", () => {
  const theme = ref<ThemeName>(loadTheme());

  // 初始化时同步到 DOM
  applyTheme(theme.value);

  // 监听 theme 变化，自动应用到 DOM 并持久化（v-model 直接改值也能生效）
  watch(theme, (next) => {
    localStorage.setItem(STORAGE_KEY, next);
    applyTheme(next);
  });

  const is22 = computed(() => theme.value === "22");
  const is33 = computed(() => theme.value === "33");

  function setTheme(next: ThemeName): void {
    theme.value = next;
  }

  return { theme, is22, is33, setTheme };
});
