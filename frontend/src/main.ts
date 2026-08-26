import { createApp } from "vue";
import { createPinia } from "pinia";
import ElementPlus from "element-plus";
import "element-plus/dist/index.css";

import App from "./App.vue";
import router from "./router";
import { useAuthStore } from "./stores/auth";

// 样式：基础变量 + 主题
import "./assets/styles/variables.css";
import "./assets/styles/theme-22.css";
import "./assets/styles/theme-33.css";

const app = createApp(App);

// 主题初始化
const savedTheme = localStorage.getItem("dailykyi_theme");
document.documentElement.dataset.theme = savedTheme === "33" ? "33" : "22";

const pinia = createPinia();
app.use(pinia);
app.use(router);
app.use(ElementPlus);

// 挂载前初始化 auth 状态（路由守卫依赖 token 是否存在）
const auth = useAuthStore();
auth.init().finally(() => {
  app.mount("#app");
});
