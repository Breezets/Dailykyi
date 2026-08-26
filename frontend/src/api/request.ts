import axios, { type AxiosError, type InternalAxiosRequestConfig } from "axios";
import { ElMessage } from "element-plus";
import { useAuthStore } from "@/stores/auth";
import router from "@/router";

const request = axios.create({
  baseURL: "/api/v1",
  withCredentials: true,
  timeout: 10000,
});

// 请求拦截器：携带 token（后端使用 httpOnly cookie，Bearer 仅作兼容标记）
request.interceptors.request.use(
  (config: InternalAxiosRequestConfig & { _silent?: boolean }) => {
    const token = localStorage.getItem("dailykyi_token");
    if (token && config.headers) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
  },
  (error) => Promise.reject(error)
);

// 响应拦截器：统一错误处理
request.interceptors.response.use(
  (response) => response.data,
  (error: AxiosError<{ detail?: string; message?: string }>) => {
    const status = error.response?.status;
    const msg =
      error.response?.data?.detail ||
      error.response?.data?.message ||
      error.message ||
      "请求失败";

    if (status === 401 || status === 423) {
      // 401/423：清除登录态并跳转登录页
      const auth = useAuthStore();
      auth.clearAuth();
      if (router.currentRoute.value.path !== "/login") {
        router.replace("/login");
      }
      ElMessage.error(typeof msg === "string" ? msg : "登录失效，请重新登录");
    } else {
      ElMessage.error(typeof msg === "string" ? msg : "请求失败");
    }
    return Promise.reject(error);
  }
);

export default request;
