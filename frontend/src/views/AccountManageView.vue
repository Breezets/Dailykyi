<script setup lang="ts">
import { ref, onMounted } from "vue";
import { useRouter } from "vue-router";
import { ElMessage, ElMessageBox } from "element-plus";
import { RefreshRight, Delete } from "@element-plus/icons-vue";
import KyiCard from "@/components/KyiCard.vue";
import KyiQrModal from "@/components/KyiQrModal.vue";
import { getAccounts, deleteAccount, refreshCookie } from "@/api/account";
import type { Account } from "@/types";

const router = useRouter();

const accounts = ref<Account[]>([]);
const loading = ref(false);
const qrVisible = ref(false);

async function fetchAccounts(): Promise<void> {
  loading.value = true;
  try {
    accounts.value = await getAccounts();
  } catch {
    accounts.value = [];
  } finally {
    loading.value = false;
  }
}

onMounted(fetchAccounts);

function avatarText(account: Account): string {
  return account.username ? account.username.charAt(0).toUpperCase() : "?";
}

function expPercent(account: Account): number {
  if (account.next_level_exp <= 0) return 0;
  const cur = account.current_exp || 0;
  const next = account.next_level_exp;
  return Math.min(100, Math.max(0, Math.round((cur / next) * 100)));
}

async function handleRefresh(uid: number): Promise<void> {
  try {
    await refreshCookie(uid);
    ElMessage.success("Cookie 刷新成功");
    await fetchAccounts();
  } catch {
    // 错误已由 request 拦截器提示
  }
}

async function handleDelete(account: Account): Promise<void> {
  try {
    await ElMessageBox.confirm(
      `确定删除账号 ${account.username || account.uid} 吗？`,
      "确认删除",
      { type: "warning" }
    );
    await deleteAccount(account.uid);
    ElMessage.success("删除成功");
    await fetchAccounts();
  } catch {
    // 取消或失败
  }
}

function goTasks(uid: number): void {
  void router.push(`/tasks?uid=${uid}`);
}

function onQrConfirmed(): void {
  void fetchAccounts();
}
</script>

<template>
  <div class="account-manage">
    <div class="page-header">
      <h2 class="page-title">账号管理</h2>
      <el-button type="primary" :color="'var(--kyi-primary)'" @click="qrVisible = true">
        + 添加账号
      </el-button>
    </div>

    <div v-if="!loading && accounts.length === 0" class="empty-state">
      <el-empty description="还没有账号，点击上方按钮添加 ~" />
    </div>

    <div v-else v-loading="loading" class="account-list">
      <KyiCard
        v-for="account in accounts"
        :key="account.uid"
        :title="account.username || `账号 ${account.uid}`"
        icon="👤"
      >
        <div class="account-card__body">
          <div class="account-card__left">
            <el-avatar :size="56" class="account-avatar">{{ avatarText(account) }}</el-avatar>
          </div>

          <div class="account-card__center">
            <div class="account-name">{{ account.username || "未命名" }}</div>
            <div class="account-meta">
              <span class="meta-item">UID: {{ account.uid }}</span>
              <span class="meta-item">Lv{{ account.level }}</span>
              <span class="meta-item">硬币: {{ account.coins }}</span>
            </div>
            <div class="account-exp">
              <el-progress
                :percentage="expPercent(account)"
                :stroke-width="8"
                :color="'var(--kyi-primary)'"
                :show-text="false"
              />
              <span class="exp-text">
                {{ account.current_exp }} / {{ account.next_level_exp }} 经验
              </span>
            </div>
          </div>

          <div class="account-card__right">
            <el-button size="small" @click="goTasks(account.uid)">配置任务</el-button>
            <el-button size="small" :icon="RefreshRight" @click="handleRefresh(account.uid)">
              刷新 Cookie
            </el-button>
            <el-popconfirm
              title="确定删除该账号吗？"
              confirm-button-text="删除"
              cancel-button-text="取消"
              @confirm="handleDelete(account)"
            >
              <template #reference>
                <el-button size="small" type="danger" :icon="Delete">删除</el-button>
              </template>
            </el-popconfirm>
          </div>
        </div>
      </KyiCard>
    </div>

    <KyiQrModal v-model="qrVisible" @confirmed="onQrConfirmed" />
  </div>
</template>

<style scoped>
.account-manage {
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.page-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.page-title {
  margin: 0;
  font-size: 20px;
  color: var(--kyi-text);
}

.account-list {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(420px, 1fr));
  gap: 16px;
}

.account-card__body {
  display: flex;
  align-items: center;
  gap: 16px;
}

.account-card__center {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.account-avatar {
  background: var(--kyi-primary);
  color: #fff;
  font-weight: 600;
}

.account-name {
  font-size: 16px;
  font-weight: 600;
  color: var(--kyi-text);
}

.account-meta {
  display: flex;
  gap: 12px;
  font-size: 13px;
  color: var(--kyi-text-secondary);
}

.account-exp {
  display: flex;
  align-items: center;
  gap: 10px;
}

.account-exp :deep(.el-progress) {
  flex: 1;
}

.exp-text {
  font-size: 12px;
  color: var(--kyi-text-secondary);
  white-space: nowrap;
}

.account-card__right {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.empty-state {
  margin-top: 40px;
}
</style>
