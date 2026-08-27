<script setup lang="ts">
import { computed, inject, type Ref, ref, onMounted, onBeforeUnmount } from "vue";
import { useRoute, useRouter } from "vue-router";
import { ArrowDown, Upload } from "@element-plus/icons-vue";
import { useAuthStore } from "@/stores/auth";
import { checkUpgrade, type UpgradeCheckResult } from "@/api/system";

const route = useRoute();
const router = useRouter();
const auth = useAuthStore();

const toggleMobileSidebar = inject<() => void>("toggleMobileSidebar", () => {});

const isMobile = ref(window.innerWidth <= 768);
function updateIsMobile(): void {
  isMobile.value = window.innerWidth <= 768;
}
onMounted(() => window.addEventListener("resize", updateIsMobile));
onBeforeUnmount(() => window.removeEventListener("resize", updateIsMobile));

const title = computed(() => (route.meta.title as string) || "Dailykyi");

const avatarText = computed(() => {
  const name = auth.user.username || "?";
  return name.charAt(0).toUpperCase();
});

async function handleLogout(): Promise<void> {
  await auth.logout();
}

// ====== 0.2.0：右上角快捷版本检测徽章（仅在新版本可用时显示） ======
const UPGRADE_CACHE_KEY = "kyi_upgrade_last_check";
const UPGRADE_RECHECK_INTERVAL = 4 * 60 * 60 * 1000; // 4 小时内不重复检查
const hasUpdate = ref(false);
const latestVersion = ref<string | null>(null);
const checking = ref(false);

async function checkUpgradeSilently(): Promise<void> {
  // 4 小时缓存：避免每次进 Dashboard 都打 GitHub API
  const last = localStorage.getItem(UPGRADE_CACHE_KEY);
  if (last) {
    try {
      const cached: UpgradeCheckResult = JSON.parse(last);
      const age = Date.now() - (cached.__ts ?? 0);
      if (age < UPGRADE_RECHECK_INTERVAL) {
        hasUpdate.value = cached.has_update;
        latestVersion.value = cached.latest;
        return;
      }
    } catch {
      // 缓存损坏 → 重新检查
    }
  }

  if (checking.value) return;
  checking.value = true;
  try {
    const res = await checkUpgrade();
    res.__ts = Date.now(); // 缓存时间戳
    localStorage.setItem(UPGRADE_CACHE_KEY, JSON.stringify(res));
    hasUpdate.value = res.has_update;
    latestVersion.value = res.latest;
  } catch {
    // 静默失败：网络不通时不打扰用户
    hasUpdate.value = false;
  } finally {
    checking.value = false;
  }
}

function goUpgrade(): void {
  router.push("/settings");
}

onMounted(() => {
  checkUpgradeSilently();
});
</script>

<template>
  <header class="header">
    <div class="header__left">
      <!-- 手机端：汉堡按钮（三横线，直观可见） -->
      <button
        v-if="isMobile"
        class="hamburger"
        :aria-label="toggleMobileSidebar.name"
        @click="toggleMobileSidebar"
      >
        <span class="hamburger__bar"></span>
        <span class="hamburger__bar"></span>
        <span class="hamburger__bar"></span>
      </button>
      <div class="header__title">{{ title }}</div>
    </div>

    <div class="header__right">
      <!-- 0.2.0：新版本检测徽章（仅有新版本时显示，点击跳到系统设置升级） -->
      <div
        v-if="hasUpdate"
        class="upgrade-badge"
        :title="`发现新版本 v${latestVersion}，点击去升级`"
        @click="goUpgrade"
      >
        <el-icon class="upgrade-badge__icon"><Upload /></el-icon>
        <span class="upgrade-badge__text">新版本</span>
        <span v-if="latestVersion" class="upgrade-badge__ver">v{{ latestVersion }}</span>
      </div>

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

/* 汉堡按钮：三横线 SVG 风格（纯 CSS，不依赖图标库） */
.hamburger {
  width: 36px;
  height: 36px;
  border-radius: 8px;
  border: 1px solid var(--kyi-border, #ebeef5);
  background: transparent;
  color: var(--kyi-text);
  display: inline-flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 4px;
  cursor: pointer;
  transition: background 0.18s ease, transform 0.18s ease;
  flex-shrink: 0;
}
.hamburger:hover {
  background: var(--kyi-sidebar-active-bg, rgba(0,0,0,0.05));
  transform: scale(1.04);
}
.hamburger:active {
  transform: scale(0.95);
}
.hamburger__bar {
  display: block;
  width: 18px;
  height: 2px;
  background: var(--kyi-text, #303133);
  border-radius: 2px;
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
  gap: 12px;
}

/* 新版本徽章（2233 双色渐变，仅 hasUpdate=true 时显示） */
.upgrade-badge {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 5px 10px 5px 8px;
  border-radius: 16px;
  cursor: pointer;
  background: linear-gradient(135deg, #FB7299, #23ADE5);
  color: #fff;
  font-size: 12px;
  font-weight: 600;
  box-shadow: 0 2px 8px rgba(251, 114, 153, 0.3);
  transition: transform 0.18s ease, box-shadow 0.18s ease;
  white-space: nowrap;
  max-width: 220px;
}

.upgrade-badge:hover {
  transform: scale(1.04);
  box-shadow: 0 4px 14px rgba(35, 173, 229, 0.4);
}

.upgrade-badge__icon {
  font-size: 14px;
}

.upgrade-badge__ver {
  font-weight: 700;
  opacity: 0.92;
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
