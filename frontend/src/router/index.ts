import { createRouter, createWebHistory, type RouteRecordRaw } from "vue-router";
import { useAuthStore } from "@/stores/auth";

const routes: RouteRecordRaw[] = [
  {
    path: "/login",
    name: "login",
    component: () => import("@/views/LoginView.vue"),
    meta: { title: "登录" },
  },
  {
    path: "/dashboard",
    name: "dashboard",
    component: () => import("@/views/DashboardView.vue"),
    meta: { title: "首页" },
  },
  {
    path: "/tasks",
    name: "tasks",
    component: () => import("@/views/TaskConfigView.vue"),
    meta: { title: "任务配置" },
  },
  {
    path: "/accounts",
    name: "accounts",
    component: () => import("@/views/AccountManageView.vue"),
    meta: { title: "账号管理" },
  },
  {
    path: "/logs",
    name: "logs",
    component: () => import("@/views/LogViewerView.vue"),
    meta: { title: "执行日志" },
  },
  {
    path: "/exp-logs",
    name: "exp-logs",
    component: () => import("@/views/ExpLogView.vue"),
    meta: { title: "经验日志" },
  },
  {
    path: "/settings",
    name: "settings",
    component: () => import("@/views/SystemSettingsView.vue"),
    meta: { title: "系统设置" },
  },
  {
    path: "/",
    redirect: "/dashboard",
  },
  {
    path: "/:pathMatch(.*)*",
    redirect: "/dashboard",
  },
];

const router = createRouter({
  history: createWebHistory(),
  routes,
});

// 路由守卫：未登录跳转 /login
router.beforeEach((to) => {
  const auth = useAuthStore();
  if (!auth.token && to.path !== "/login") {
    return { path: "/login" };
  }
  if (auth.token && to.path === "/login") {
    return { path: "/dashboard" };
  }
  return true;
});

// 设置页面标题
const appTitle = "Dailykyi";
router.afterEach((to) => {
  const title = (to.meta.title as string) || "";
  document.title = title ? `${title} · ${appTitle}` : appTitle;
});

export default router;
