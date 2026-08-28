<script setup lang="ts">
import { computed, ref, onMounted, onUnmounted, inject } from "vue";
import { useRoute } from "vue-router";
import {
  House,
  SetUp,
  User,
  Document,
  DataAnalysis,
  Setting,
} from "@element-plus/icons-vue";
import KyiThemeSwitch from "./KyiThemeSwitch.vue";
import { SITE } from "@/constants/site";
import { getAllSidebarMascots } from "@/utils/mascot";

const route = useRoute();

// 手机端：点击菜单项后自动关闭侧边栏
const closeMobileSidebar = inject<() => void>("closeMobileSidebar", () => {});

function onMenuNavigate(): void {
  closeMobileSidebar();
}

interface MenuItem {
  index: string;
  label: string;
  icon: typeof House;
}

const menus: MenuItem[] = [
  { index: "/dashboard", label: "首页", icon: House },
  { index: "/tasks", label: "任务配置", icon: SetUp },
  { index: "/accounts", label: "账号管理", icon: User },
  { index: "/logs", label: "执行日志", icon: Document },
  { index: "/exp-logs", label: "经验日志", icon: DataAnalysis },
  { index: "/settings", label: "系统设置", icon: Setting },
];

const activeIndex = computed(() => {
  const base = "/" + (route.path.split("/")[1] || "dashboard");
  return base === "/" ? "/dashboard" : base;
});

// 侧边栏小图轮播（1:1 方图，30 秒切换）
const mascots = getAllSidebarMascots();
const currentMascotIdx = ref(0);
let mascotTimer: ReturnType<typeof setInterval> | null = null;

onMounted(() => {
  mascotTimer = setInterval(() => {
    currentMascotIdx.value = (currentMascotIdx.value + 1) % mascots.length;
  }, 30000);
});

onUnmounted(() => {
  if (mascotTimer) clearInterval(mascotTimer);
});
</script>

<template>
  <aside class="sidebar">
    <div class="sidebar__logo">
      <div class="dailykyi-logo">
        <svg class="kyi-logo" viewBox="0 0 64 64" xmlns="http://www.w3.org/2000/svg">
          <defs>
            <linearGradient id="bgGrad" x1="0%" y1="0%" x2="100%" y2="100%">
              <stop offset="0%" stop-color="#FB7299" />
              <stop offset="50%" stop-color="#FB7299" />
              <stop offset="50%" stop-color="#23ADE5" />
              <stop offset="100%" stop-color="#23ADE5" />
            </linearGradient>
            <linearGradient id="screenGrad" x1="0%" y1="0%" x2="100%" y2="100%">
              <stop offset="0%" stop-color="#ffffff" stop-opacity="0.28" />
              <stop offset="100%" stop-color="#ffffff" stop-opacity="0.08" />
            </linearGradient>
          </defs>
          <!-- 圆角屏幕外框 -->
          <rect x="6" y="14" width="52" height="40" rx="12" fill="url(#bgGrad)" />
          <!-- 屏幕内高光 -->
          <rect x="10" y="18" width="44" height="32" rx="8" fill="url(#screenGrad)" />
          <!-- 屏幕中央 "D" 字 或双颜对扣 -->
          <g transform="translate(21 26)">
            <path d="M0 6 L0 16 Q0 24 11 24 L16 24 Q22 24 22 16 L22 6 Z"
                  fill="#ffffff" opacity="0.92"/>
            <path d="M11 6 L11 16 Q11 20 16 20 Q20 20 20 16 L20 6 Z"
                  fill="url(#bgGrad)"/>
            <!-- 22/33 小眼睛点缀 -->
            <circle cx="5.5" cy="11.5" r="1.2" fill="#2b2b2b"/>
            <circle cx="17" cy="11.5" r="1.2" fill="#2b2b2b"/>
          </g>
          <!-- 天线 -->
          <line x1="18" y1="14" x2="11" y2="4" stroke="#FB7299" stroke-width="2.5" stroke-linecap="round"/>
          <line x1="46" y1="14" x2="53" y2="4" stroke="#23ADE5" stroke-width="2.5" stroke-linecap="round"/>
          <circle cx="11" cy="4" r="2.4" fill="#FB7299"/>
          <circle cx="53" cy="4" r="2.4" fill="#23ADE5"/>
        </svg>
        <div class="tv-text">Dailykyi</div>
      </div>
    </div>

    <nav class="sidebar__menu">
      <router-link
        v-for="item in menus"
        :key="item.index"
        :to="item.index"
        class="menu-item"
        :class="{ 'menu-item--active': activeIndex === item.index }"
        @click="onMenuNavigate"
      >
        <el-icon class="menu-item__icon">
          <component :is="item.icon" />
        </el-icon>
        <span class="menu-item__label">{{ item.label }}</span>
      </router-link>
    </nav>

    <div class="sidebar__footer">
      <div class="sidebar__mascot">
        <transition name="mascot-fade" mode="out-in">
          <img
            :src="mascots[currentMascotIdx]"
            :key="currentMascotIdx"
            alt="2233 吉祥物"
            class="sidebar__mascot-img"
          />
        </transition>
        <div class="sidebar__mascot-tip">22 & 33 陪伴中</div>
      </div>
      <KyiThemeSwitch />
      <div class="sidebar__links">
        <a :href="SITE.docs" target="_blank" rel="noopener noreferrer" title="使用文档">
          <svg class="mini-icon" viewBox="0 0 24 24" fill="currentColor"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8l-6-6zm-1 7V3.5L18.5 9H13z"/></svg>
        </a>
        <a :href="SITE.github" target="_blank" rel="noopener noreferrer" title="GitHub">
          <svg class="mini-icon" viewBox="0 0 24 24" fill="currentColor"><path d="M12 .5C5.73.5.5 5.73.5 12c0 5.08 3.29 9.39 7.86 10.91.57.1.78-.25.78-.55 0-.27-.01-1.17-.02-2.12-3.2.69-3.87-1.37-3.87-1.37-.52-1.33-1.27-1.68-1.27-1.68-1.04-.71.08-.7.08-.7 1.15.08 1.76 1.18 1.76 1.18 1.02 1.76 2.69 1.25 3.35.96.1-.75.4-1.25.72-1.54-2.55-.29-5.23-1.28-5.23-5.7 0-1.26.45-2.29 1.18-3.1-.12-.29-.51-1.47.11-3.07 0 0 .97-.31 3.17 1.18a11 11 0 0 1 5.78 0c2.2-1.49 3.17-1.18 3.17-1.18.62 1.6.23 2.78.11 3.07.73.81 1.18 1.84 1.18 3.1 0 4.43-2.69 5.41-5.25 5.69.41.36.77 1.05.77 2.13 0 1.53-.01 2.77-.01 3.15 0 .3.21.66.79.55C20.21 21.39 23.5 17.07 23.5 12 23.5 5.73 18.27.5 12 .5z"/></svg>
        </a>
        <a :href="SITE.bilibili" target="_blank" rel="noopener noreferrer" title="B 站 · {{ SITE.authorName }}">
          <svg class="mini-icon bili" viewBox="0 0 24 24" fill="currentColor"><path d="M17.813 4.653h.854c1.51.054 2.769.578 3.773 1.574 1.004.995 1.524 2.249 1.56 3.76v7.36c-.036 1.51-.556 2.769-1.56 3.773s-2.262 1.524-3.773 1.56H5.333c-1.51-.036-2.769-.556-3.773-1.56S.036 18.858 0 17.347v-7.36c.036-1.511.556-2.765 1.56-3.76 1.004-.996 2.262-1.52 3.773-1.574h.774l-1.174-1.12a1.234 1.234 0 0 1-.373-.906c0-.356.124-.658.373-.906l.053-.054c.284-.267.596-.4.933-.4.355 0 .658.133.906.4l2.32 2.214h5.2l2.319-2.214c.249-.267.551-.4.906-.4.337 0 .649.133.933.4l.054.054c.248.248.372.55.372.906 0 .355-.124.657-.373.906zM5.333 7.24c-.746.018-1.37.273-1.87.764-.5.49-.747 1.115-.747 1.874v7.36c.018.746.273 1.37.764 1.874.49.5 1.115.747 1.874.746h13.334c.746.018 1.37-.273 1.874-.764.5-.49.747-1.115.746-1.874v-7.36c-.018-.746-.273-1.37-.764-1.874-.49-.5-1.115-.747-1.874-.746H5.333z"/></svg>
        </a>
      </div>
      <div class="sidebar__version">v{{ SITE.version }}</div>
    </div>
  </aside>
</template>

<style scoped>
.sidebar {
  width: var(--kyi-sidebar-width);
  height: 100vh;
  background: var(--kyi-sidebar-bg);
  display: flex;
  flex-direction: column;
  border-right: 1px solid #ebeef5;
}

.sidebar__logo {
  height: var(--kyi-header-height);
  display: flex;
  align-items: center;
  justify-content: center;
  border-bottom: 1px solid #ebeef5;
}

.dailykyi-logo {
  display: flex;
  align-items: center;
  gap: 10px;
}

.kyi-logo {
  width: 38px;
  height: 38px;
  filter: drop-shadow(0 2px 4px rgba(251, 114, 153, 0.18))
          drop-shadow(0 2px 4px rgba(35, 173, 229, 0.18));
}

.tv-text {
  font-size: 20px;
  font-weight: 700;
  letter-spacing: 0.5px;
  background: linear-gradient(90deg, #FB7299 0%, #23ADE5 100%);
  -webkit-background-clip: text;
  background-clip: text;
  color: transparent;
}

.sidebar__menu {
  flex: 1;
  padding: 12px 10px;
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.menu-item {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 12px 14px;
  border-radius: 10px;
  color: var(--kyi-sidebar-text);
  text-decoration: none;
  transition: transform 0.18s ease, background 0.18s ease;
}

.menu-item:hover {
  transform: translateX(4px);
  background: var(--kyi-sidebar-active-bg);
}

.menu-item--active {
  background: var(--kyi-primary);
  color: #fff;
  font-weight: 600;
}

.menu-item__icon {
  font-size: 18px;
}

.menu-item__label {
  font-size: 14px;
}

.sidebar__footer {
  padding: 14px 16px 16px;
  border-top: 1px solid #ebeef5;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 10px;
}

.sidebar__mascot {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 6px;
  padding: 4px 0 6px;
}

.sidebar__mascot-img {
  width: 120px;
  height: 120px;
  object-fit: cover;
  object-position: center;       /* 聚焦画面中央，避免人物被裁掉 */
  border-radius: 16px;            /* 方圆角，不再是圆形 */
  border: 2px solid var(--kyi-primary);
  box-shadow: 0 4px 12px rgba(251, 114, 153, 0.15), 0 4px 12px rgba(35, 173, 229, 0.15);
  transition: transform 0.3s ease, border-color 0.3s ease, box-shadow 0.3s ease;
  animation: mascot-bounce 4s ease-in-out infinite;
  cursor: pointer;
}

.sidebar__mascot-img:hover {
  transform: scale(1.05);
  border-color: var(--kyi-secondary, #23ADE5);
  box-shadow: 0 6px 18px rgba(251, 114, 153, 0.28), 0 6px 18px rgba(35, 173, 229, 0.28);
}

@keyframes mascot-bounce {
  0%, 100% { transform: translateY(0); }
  50%      { transform: translateY(-3px); }
}

/* 切换图片时的淡入淡出过渡 */
.mascot-fade-enter-active,
.mascot-fade-leave-active {
  transition: opacity 0.5s ease, transform 0.5s ease;
}

.mascot-fade-enter-from {
  opacity: 0;
  transform: translateY(8px) scale(0.96);
}

.mascot-fade-leave-to {
  opacity: 0;
  transform: translateY(-8px) scale(0.96);
}

.sidebar__mascot-tip {
  font-size: 11px;
  color: var(--kyi-text-secondary);
  opacity: 0.7;
  letter-spacing: 0.3px;
}

.sidebar__links {
  display: flex;
  align-items: center;
  gap: 14px;
}

.sidebar__links a {
  color: var(--kyi-sidebar-text, #606266);
  opacity: 0.55;
  transition: opacity 0.2s ease, color 0.2s ease;
}

.sidebar__links a:hover {
  opacity: 1;
  color: var(--kyi-primary);
}

.mini-icon {
  width: 18px;
  height: 18px;
}

.mini-icon.bili {
  color: var(--kyi-primary);
  opacity: 0.7;
}

.sidebar__version {
  font-size: 11px;
  color: var(--kyi-sidebar-text, #606266);
  opacity: 0.5;
  letter-spacing: 0.3px;
}
</style>
