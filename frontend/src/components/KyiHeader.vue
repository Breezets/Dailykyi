<script setup lang="ts">
import { computed, inject, type Ref } from "vue";
import { useRoute } from "vue-router";
import { ArrowDown, Fold } from "@element-plus/icons-vue";
import { useAuthStore } from "@/stores/auth";

const route = useRoute();
const auth = useAuthStore();

const toggleMobileSidebar = inject<() => void>("toggleMobileSidebar", () => {});
const isMobile = computed(() => window.innerWidth <= 768);

const title = computed(() => (route.meta.title as string) || "Dailykyi");

const avatarText = computed(() => {
  const name = auth.user.username || "?";
  return name.charAt(0).toUpperCase();
});

async function handleLogout(): Promise<void> {
  await auth.logout();
}
</script>

<template>
  <header class="header">
    <div class="header__left">
      <el-button
        v-if="isMobile"
        text
        :icon="Fold"
        class="hamburger"
        aria-label="打开菜单"
        @click="toggleMobileSidebar"
      />
      <div class="header__title">{{ title }}</div>
    </div>

    <div class="header__right">
      <el-dropdown trigger="click" @command="handleLogout">
        <div class="user-chip">
          <el-avatar :size="32" class="user-avatar">{{ avatarText }}</el-avatar>
          <span class="user-name">{{ auth.user.username }}</span>
          <el-icon class="user-arrow"><ArrowDown /></el-icon>
        </div>
        <template #dropdown>
          <el-dropdown-menu>
            <el-dropdown-item command="logout">退出登录</el-dropdown-item>
          </el-dropdown-menu>
        </template>
      </el-dropdown>
    </div>
  </header>
</template>

<style scoped>
.header {
  height: var(--kyi-header-height);
  background: var(--kyi-card-bg);
  border-bottom: 1px solid var(--kyi-border, #ebeef5);
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 24px;
}

.header__left {
  display: flex;
  align-items: center;
  gap: 8px;
  min-width: 0;
}

.hamburger {
  color: var(--kyi-text);
  font-size: 20px;
  padding: 6px;
}

.header__title {
  font-size: 18px;
  font-weight: 600;
  color: var(--kyi-text);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  max-width: 60vw;
}

.header__right {
  display: flex;
  align-items: center;
}

.user-chip {
  display: flex;
  align-items: center;
  gap: 8px;
  cursor: pointer;
  padding: 4px 8px;
  border-radius: 20px;
  transition: background 0.18s ease;
}

.user-chip:hover {
  background: var(--kyi-sidebar-active-bg);
}

.user-avatar {
  background: var(--kyi-primary);
  color: #fff;
  font-weight: 600;
}

.user-name {
  font-size: 14px;
  color: var(--kyi-text);
}

.user-arrow {
  font-size: 12px;
  color: var(--kyi-text-secondary);
}

/* ============ 手机端 ============ */
@media (max-width: 768px) {
  .header {
    padding: 0 10px 0 8px;
  }
  .header__title {
    font-size: 15px;
    max-width: 45vw;
  }
  .user-name {
    display: none;
  }
  .user-chip {
    padding: 2px 4px;
  }
}
</style>
