<script setup lang="ts">
import { reactive, ref } from "vue";
import { User, Lock } from "@element-plus/icons-vue";
import { useAuthStore } from "@/stores/auth";
import { SITE } from "@/constants/site";

const auth = useAuthStore();

const loginForm = reactive({
  username: "",
  password: "",
});
const loading = ref(false);
const errorMsg = ref("");

async function handleLogin(): Promise<void> {
  if (!loginForm.username || !loginForm.password) {
    errorMsg.value = "请输入用户名和密码";
    return;
  }
  errorMsg.value = "";
  loading.value = true;
  try {
    await auth.login(loginForm.username, loginForm.password);
  } catch {
    errorMsg.value = "登录失败，请检查用户名和密码";
  } finally {
    loading.value = false;
  }
}
</script>

<template>
  <div class="login-page">
    <div class="login-card">
      <div class="login-card__brand">
        <div class="dailykyi-logo">
          <svg class="kyi-logo" viewBox="0 0 64 64" xmlns="http://www.w3.org/2000/svg">
            <defs>
              <linearGradient id="bgGradL" x1="0%" y1="0%" x2="100%" y2="100%">
                <stop offset="0%" stop-color="#FB7299" />
                <stop offset="50%" stop-color="#FB7299" />
                <stop offset="50%" stop-color="#23ADE5" />
                <stop offset="100%" stop-color="#23ADE5" />
              </linearGradient>
              <linearGradient id="screenGradL" x1="0%" y1="0%" x2="100%" y2="100%">
                <stop offset="0%" stop-color="#ffffff" stop-opacity="0.32" />
                <stop offset="100%" stop-color="#ffffff" stop-opacity="0.08" />
              </linearGradient>
            </defs>
            <rect x="6" y="14" width="52" height="40" rx="12" fill="url(#bgGradL)" />
            <rect x="10" y="18" width="44" height="32" rx="8" fill="url(#screenGradL)" />
            <g transform="translate(21 26)">
              <path d="M0 6 L0 16 Q0 24 11 24 L16 24 Q22 24 22 16 L22 6 Z" fill="#ffffff" opacity="0.94"/>
              <path d="M11 6 L11 16 Q11 20 16 20 Q20 20 20 16 L20 6 Z" fill="url(#bgGradL)"/>
              <circle cx="5.5" cy="11.5" r="1.3" fill="#2b2b2b"/>
              <circle cx="17" cy="11.5" r="1.3" fill="#2b2b2b"/>
            </g>
            <line x1="18" y1="14" x2="11" y2="4" stroke="#FB7299" stroke-width="2.5" stroke-linecap="round"/>
            <line x1="46" y1="14" x2="53" y2="4" stroke="#23ADE5" stroke-width="2.5" stroke-linecap="round"/>
            <circle cx="11" cy="4" r="2.4" fill="#FB7299"/>
            <circle cx="53" cy="4" r="2.4" fill="#23ADE5"/>
          </svg>
          <div class="tv-text">Dailykyi</div>
        </div>
        <div class="brand-sub">每日姬 · B 站日常助手</div>
      </div>

      <el-form class="login-form" @submit.prevent="handleLogin">
        <el-input
          v-model="loginForm.username"
          size="large"
          placeholder="用户名"
          :prefix-icon="User"
        />
        <el-input
          v-model="loginForm.password"
          size="large"
          type="password"
          show-password
          placeholder="密码"
          :prefix-icon="Lock"
          @keyup.enter="handleLogin"
        />

        <div v-if="errorMsg" class="login-error">{{ errorMsg }}</div>

        <el-button
          type="primary"
          size="large"
          class="login-btn"
          :loading="loading"
          @click="handleLogin"
        >
          登录
        </el-button>
      </el-form>

      <div class="login-footer">
        <div class="login-footer__links">
          <a :href="SITE.docs" target="_blank" rel="noopener noreferrer">使用文档</a>
          <span class="sep">·</span>
          <a :href="SITE.github" target="_blank" rel="noopener noreferrer">GitHub</a>
          <span class="sep">·</span>
          <a :href="SITE.bilibili" target="_blank" rel="noopener noreferrer">B 站</a>
        </div>
        <div class="login-footer__meta">
          {{ SITE.copyright }} · {{ SITE.license }} · v{{ SITE.version }}
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.login-page {
  position: fixed;
  inset: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  background: var(--kyi-bg-gradient);
}

.login-card {
  width: 420px;
  padding: 40px 36px 28px;
  background: var(--kyi-card-bg);
  border-radius: 18px;
  box-shadow: 0 16px 48px rgba(0, 0, 0, 0.08);
}

.login-card__brand {
  display: flex;
  flex-direction: column;
  align-items: center;
  margin-bottom: 28px;
}

.dailykyi-logo {
  display: flex;
  align-items: center;
  gap: 12px;
}

.kyi-logo {
  width: 48px;
  height: 48px;
  filter: drop-shadow(0 4px 8px rgba(251, 114, 153, 0.2))
          drop-shadow(0 4px 8px rgba(35, 173, 229, 0.2));
}

.tv-text {
  font-size: 28px;
  font-weight: 700;
  letter-spacing: 0.5px;
  background: linear-gradient(90deg, #FB7299 0%, #23ADE5 100%);
  -webkit-background-clip: text;
  background-clip: text;
  color: transparent;
}

.brand-sub {
  margin-top: 8px;
  font-size: 13px;
  color: var(--kyi-text-secondary);
  letter-spacing: 0.5px;
}

.login-form {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.login-error {
  color: var(--kyi-danger);
  font-size: 13px;
  margin-top: -4px;
}

.login-btn {
  width: 100%;
  background: var(--kyi-primary);
  border-color: var(--kyi-primary);
}

.login-btn:hover,
.login-btn:focus {
  background: var(--kyi-primary-light);
  border-color: var(--kyi-primary-light);
}

.login-footer {
  margin-top: 20px;
  padding-top: 16px;
  border-top: 1px solid #f0f2f5;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 6px;
  font-size: 12px;
  color: var(--kyi-text-secondary);
}

.login-footer__links {
  display: flex;
  align-items: center;
  gap: 10px;
}

.login-footer__links a {
  color: var(--kyi-text-secondary);
  text-decoration: none;
  transition: color 0.2s ease;
}

.login-footer__links a:hover {
  color: var(--kyi-primary);
}

.login-footer__links .sep {
  opacity: 0.4;
}

.login-footer__meta {
  opacity: 0.8;
}
</style>
