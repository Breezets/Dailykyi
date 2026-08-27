<script setup lang="ts">
import { ref, provide, onMounted, onBeforeUnmount, watch, nextTick } from "vue";
import { useAuthStore } from "@/stores/auth";
import KyiSidebar from "@/components/KyiSidebar.vue";
import KyiHeader from "@/components/KyiHeader.vue";
import LoginView from "@/views/LoginView.vue";
import { SITE } from "@/constants/site";
import { Document } from "@element-plus/icons-vue";

const auth = useAuthStore();
auth.init();

// 手机端侧边栏开合（仅 <=768px 有效）
const mobileSidebarOpen = ref(false);
const isMobile = ref(window.innerWidth <= 768);

function updateIsMobile(): void {
  isMobile.value = window.innerWidth <= 768;
  if (!isMobile.value) mobileSidebarOpen.value = false;
}
onMounted(() => window.addEventListener("resize", updateIsMobile));
onBeforeUnmount(() => window.removeEventListener("resize", updateIsMobile));

// 给子组件（KyiHeader）提供 hamburger 状态
provide("mobileSidebarOpen", mobileSidebarOpen);
provide("toggleMobileSidebar", () => {
  mobileSidebarOpen.value = !mobileSidebarOpen.value;
});

// 侧边栏打开时锁定 body 滚动
watch(
  () => [mobileSidebarOpen.value, isMobile.value],
  async ([open, mobile]) => {
    await nextTick();
    if (mobile && open) {
      document.body.style.overflow = "hidden";
    } else {
      document.body.style.overflow = "";
    }
  },
  { immediate: true }
);

function closeMobileSidebar(): void {
  if (isMobile.value) mobileSidebarOpen.value = false;
}
provide("closeMobileSidebar", closeMobileSidebar);
</script>

<template>
  <LoginView v-if="!auth.isLoggedIn" />
  <div v-else class="kyi-layout">
    <KyiSidebar
      :class="{ 'kyi-layout__sidebar': true, 'sidebar--mobile-open': isMobile && mobileSidebarOpen }"
      @click="closeMobileSidebar"
    />
    <!-- 手机端侧边栏遮罩 -->
    <div
      v-if="isMobile && mobileSidebarOpen"
      class="sidebar-mask"
      @click="closeMobileSidebar"
    ></div>

    <KyiHeader class="kyi-layout__header" />
    <div class="kyi-layout__body">
      <main class="kyi-layout__main">
        <router-view />
      </main>
      <footer class="kyi-layout__footer">
        <div class="footer-row">
          <span class="footer-copyright">{{ SITE.copyright }}</span>
          <span class="footer-sep">·</span>
          <span class="footer-license">{{ SITE.license }}</span>
          <span class="footer-sep">·</span>
          <span class="footer-version">v{{ SITE.version }}</span>
        </div>
        <div class="footer-row footer-row--links">
          <a :href="SITE.docs" target="_blank" rel="noopener noreferrer" class="footer-link">
            <el-icon><Document /></el-icon>
            <span>使用文档</span>
          </a>
          <a :href="SITE.github" target="_blank" rel="noopener noreferrer" class="footer-link">
            <svg class="gh-icon" viewBox="0 0 24 24" fill="currentColor">
              <path d="M12 .5C5.73.5.5 5.73.5 12c0 5.08 3.29 9.39 7.86 10.91.57.1.78-.25.78-.55 0-.27-.01-1.17-.02-2.12-3.2.69-3.87-1.37-3.87-1.37-.52-1.33-1.27-1.68-1.27-1.68-1.04-.71.08-.7.08-.7 1.15.08 1.76 1.18 1.76 1.18 1.02 1.76 2.69 1.25 3.35.96.1-.75.4-1.25.72-1.54-2.55-.29-5.23-1.28-5.23-5.7 0-1.26.45-2.29 1.18-3.1-.12-.29-.51-1.47.11-3.07 0 0 .97-.31 3.17 1.18a11 11 0 0 1 5.78 0c2.2-1.49 3.17-1.18 3.17-1.18.62 1.6.23 2.78.11 3.07.73.81 1.18 1.84 1.18 3.1 0 4.43-2.69 5.41-5.25 5.69.41.36.77 1.05.77 2.13 0 1.53-.01 2.77-.01 3.15 0 .3.21.66.79.55C20.21 21.39 23.5 17.07 23.5 12 23.5 5.73 18.27.5 12 .5z"/>
            </svg>
            <span>GitHub</span>
          </a>
          <a :href="SITE.bilibili" target="_blank" rel="noopener noreferrer" class="footer-link footer-link--bili">
            <svg class="bili-icon" viewBox="0 0 24 24" fill="currentColor">
              <path d="M17.813 4.653h.854c1.51.054 2.769.578 3.773 1.574 1.004.995 1.524 2.249 1.56 3.76v7.36c-.036 1.51-.556 2.769-1.56 3.773s-2.262 1.524-3.773 1.56H5.333c-1.51-.036-2.769-.556-3.773-1.56S.036 18.858 0 17.347v-7.36c.036-1.511.556-2.765 1.56-3.76 1.004-.996 2.262-1.52 3.773-1.574h.774l-1.174-1.12a1.234 1.234 0 0 1-.373-.906c0-.356.124-.658.373-.906l.053-.054c.284-.267.596-.4.933-.4.355 0 .658.133.906.4l2.32 2.214h5.2l2.319-2.214c.249-.267.551-.4.906-.4.337 0 .649.133.933.4l.054.054c.248.248.372.55.372.906 0 .355-.124.657-.373.906zM5.333 7.24c-.746.018-1.37.273-1.87.764-.5.49-.747 1.115-.747 1.874v7.36c.018.746.273 1.37.764 1.874.49.5 1.115.747 1.874.746h13.334c.746.018 1.37-.273 1.874-.764.5-.49.747-1.115.746-1.874v-7.36c-.018-.746-.273-1.37-.764-1.874-.49-.5-1.115-.747-1.874-.746H5.333zM8 11.107c.373 0 .684.124.933.373.25.249.383.569.4.96v1.173c-.017.391-.15.711-.4.96-.249.25-.56.383-.933.4H6.667c-.373-.017-.684-.15-.933-.4-.25-.249-.387-.569-.4-.96V12.44c0-.373.129-.684.386-.933.258-.25.57-.373.937-.373H8zm9.333 0c.373 0 .684.124.933.373.25.249.384.569.387.96v1.173c-.017.391-.15.711-.4.96-.249.25-.56.383-.933.4h-1.333c-.373-.017-.684-.15-.934-.4-.249-.249-.383-.569-.383-.96V12.44c.017-.391.15-.711.4-.96.249-.249.569-.373.96-.373h1.333z"/>
            </svg>
            <span>B 站 · {{ SITE.authorName }}</span>
          </a>
        </div>
      </footer>
    </div>
  </div>
</template>

<style scoped>
.kyi-layout {
  min-height: 100vh;
  background: var(--kyi-bg);
  display: flex;
  flex-direction: column;
}

.kyi-layout__sidebar {
  position: fixed;
  top: 0;
  left: 0;
  width: 220px;
  height: 100vh;
  z-index: 100;
  transition: transform 0.3s ease;
}

/* 手机端：侧边栏默认隐藏在左侧，打开时滑出 */
@media (max-width: 768px) {
  .kyi-layout__sidebar {
    width: 240px;
    transform: translateX(-100%);
    box-shadow: 2px 0 12px rgba(0, 0, 0, 0.1);
  }
  .kyi-layout__sidebar.sidebar--mobile-open {
    transform: translateX(0);
  }
}

.sidebar-mask {
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.4);
  z-index: 99;
  animation: mask-fade 0.2s ease;
}

@keyframes mask-fade {
  from { opacity: 0; }
  to { opacity: 1; }
}

.kyi-layout__header {
  position: fixed;
  top: 0;
  left: var(--kyi-sidebar-width);
  right: 0;
  height: var(--kyi-header-height);
  z-index: 90;
  transition: left 0.3s ease;
}

.kyi-layout__body {
  margin-left: var(--kyi-sidebar-width);
  margin-top: var(--kyi-header-height);
  min-height: calc(100vh - var(--kyi-header-height));
  display: flex;
  flex-direction: column;
  transition: margin-left 0.3s ease;
}

.kyi-layout__main {
  flex: 1;
  padding: 24px;
}

.kyi-layout__footer {
  padding: 20px 24px 24px;
  border-top: 1px solid var(--kyi-border, #ebeef5);
  display: flex;
  flex-direction: column;
  gap: 8px;
  font-size: 12px;
  color: var(--kyi-text-secondary);
  background: var(--kyi-card-bg, #fff);
}

.footer-row {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 8px;
}

.footer-row--links {
  gap: 20px;
}

.footer-sep {
  opacity: 0.4;
}

.footer-link {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  color: var(--kyi-text-secondary);
  text-decoration: none;
  transition: color 0.2s ease;
}

.footer-link:hover {
  color: var(--kyi-primary);
}

.footer-link--bili {
  color: var(--kyi-primary);
}

.footer-link--bili:hover {
  color: #ff8eb0;
}

.footer-link .el-icon {
  font-size: 14px;
}

.gh-icon,
.bili-icon {
  width: 14px;
  height: 14px;
}

/* ============ 手机端 ============ */
@media (max-width: 768px) {
  .kyi-layout__header {
    left: 0 !important;
  }
  .kyi-layout__body {
    margin-left: 0 !important;
  }
  .kyi-layout__main {
    padding: 14px 12px;
  }
  .kyi-layout__footer {
    padding: 14px 12px 18px;
  }
  .footer-row--links {
    gap: 14px;
  }
}
</style>
