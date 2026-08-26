import { defineStore } from "pinia";
import { ref } from "vue";
import router from "@/router";
import request from "@/api/request";

interface UserInfo {
  username: string;
  avatar: string;
}

interface LoginPayload {
  username: string;
  password: string;
}

interface LoginResponse {
  token: string;
  username: string;
}

interface MeResponse {
  username: string;
}

const TOKEN_KEY = "dailykyi_token";

export const useAuthStore = defineStore("auth", () => {
  const token = ref<string | null>(localStorage.getItem(TOKEN_KEY));
  const user = ref<UserInfo>({ username: "", avatar: "" });
  const isLoggedIn = ref(false);

  function setAuth(t: string, info: UserInfo): void {
    token.value = t;
    user.value = info;
    isLoggedIn.value = true;
    localStorage.setItem(TOKEN_KEY, t);
  }

  function clearAuth(): void {
    token.value = null;
    user.value = { username: "", avatar: "" };
    isLoggedIn.value = false;
    localStorage.removeItem(TOKEN_KEY);
  }

  async function login(username: string, password: string): Promise<void> {
    const data = await request.post<unknown, LoginResponse>("/auth/login", {
      username,
      password,
    } as LoginPayload);
    setAuth(data.token, { username: data.username, avatar: "" });
    router.push("/dashboard");
  }

  async function logout(): Promise<void> {
    try {
      await request.post("/auth/logout");
    } catch {
      // 登出接口失败也允许前端退出
    }
    clearAuth();
    window.location.href = "/login";
  }

  async function init(): Promise<void> {
    const saved = localStorage.getItem(TOKEN_KEY);
    if (!saved) return;
    token.value = saved;
    try {
      const me = await request.get<unknown, MeResponse>("/auth/me");
      user.value = { username: me.username, avatar: "" };
      isLoggedIn.value = true;
    } catch {
      clearAuth();
    }
  }

  async function changePassword(
    oldPassword: string,
    newPassword: string
  ): Promise<void> {
    await request.post("/auth/change-password", {
      old_password: oldPassword,
      new_password: newPassword,
    });
  }

  return {
    token,
    user,
    isLoggedIn,
    setAuth,
    clearAuth,
    login,
    changePassword,
    logout,
    init,
  };
});
