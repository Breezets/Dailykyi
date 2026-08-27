<script setup lang="ts">
import { ref, computed, onMounted } from "vue";
import { useAuthStore } from "@/stores/auth";
import { getDashboard, type DashboardResponse } from "@/api/dashboard";
import { getDailyHomeMascot } from "@/utils/mascot";

const auth = useAuthStore();
const username = computed(() => auth.user.username || "管理员");
const dailyMascot = getDailyHomeMascot();

const loading = ref(false);
const data = ref<DashboardResponse | null>(null);

onMounted(async () => {
  loading.value = true;
  try {
    data.value = await getDashboard();
  } catch {
    data.value = null;
  } finally {
    loading.value = false;
  }
});

const accountCount = computed(() => data.value?.accounts.length ?? 0);
const todayExp = computed(() => {
  const accounts = data.value?.accounts ?? [];
  return accounts.reduce((sum, a) => sum + a.today_exp_gained, 0);
});
const todayStats = computed(() => data.value?.today_stats);
const taskProgress = computed(() => {
  const s = todayStats.value;
  if (!s || s.total_tasks === 0) return "0%";
  return `${Math.round((s.success_count / s.total_tasks) * 100)}%`;
});

const stats = computed(() => [
  { label: "账号数", value: accountCount.value, icon: "👥", color: "var(--kyi-primary)" },
  { label: "今日经验", value: todayExp.value, icon: "⭐", color: "var(--kyi-secondary)" },
  { label: "任务进度", value: taskProgress.value, icon: "📊", color: "var(--kyi-success)" },
]);

const taskTypeMap: Record<string, string> = {
  coin: "投币",
  watch: "观看",
  share: "分享",
  live_sign: "直播签到",
  silver2coin: "银瓜子换币",
};

const statusColor: Record<string, string> = {
  success: "var(--kyi-success)",
  failed: "var(--kyi-danger)",
  skipped: "var(--kyi-text-secondary)",
};
</script>

<template>
  <div class="dashboard-view" v-loading="loading">
    <div class="welcome-banner">
      <div class="welcome-banner__content">
        <h2 class="welcome-banner__title">欢迎回来，{{ username }}</h2>
        <p class="welcome-banner__sub">{{ todayStats ? `今日已完成 ${todayStats.success_count}/${todayStats.total_tasks} 个任务` : '加载中...' }}</p>
      </div>
      <img :src="dailyMascot" alt="今日 2233" class="welcome-banner__mascot" />
    </div>

    <div class="stat-cards">
      <el-card
        v-for="item in stats"
        :key="item.label"
        class="stat-card"
        shadow="hover"
      >
        <div class="stat-card__icon" :style="{ background: item.color }">
          {{ item.icon }}
        </div>
        <div class="stat-card__body">
          <div class="stat-card__value">{{ item.value }}</div>
          <div class="stat-card__label">{{ item.label }}</div>
        </div>
      </el-card>
    </div>

    <div class="dashboard-grid">
      <!-- 账号概览 -->
      <el-card class="section-card" shadow="never">
        <template #header><span class="section-title">账号概览</span></template>
        <div v-if="!data?.accounts.length" class="empty-text">还没有账号</div>
        <div v-else class="account-list">
          <div v-for="acc in data.accounts" :key="acc.uid" class="account-item">
            <div class="account-avatar">{{ (acc.username || '?').charAt(0) }}</div>
            <div class="account-info">
              <div class="account-name">{{ acc.username || '未命名' }} <span class="account-level">Lv{{ acc.level }}</span></div>
              <div class="account-exp">
                经验 {{ acc.current_exp }} / {{ acc.next_level_exp }}
                <span class="account-coins">硬币 {{ acc.coins }}</span>
              </div>
            </div>
            <div class="account-today">+{{ acc.today_exp_gained }} exp</div>
          </div>
        </div>
      </el-card>

      <!-- LV6 预估 -->
      <el-card class="section-card lv6-card" shadow="never">
        <template #header>
          <span class="section-title">到达 LV6 预估</span>
        </template>
        <div v-if="!data?.accounts.length" class="empty-text">还没有账号</div>
        <div v-else class="lv6-list">
          <div v-for="acc in data.accounts" :key="acc.uid" class="lv6-row">
            <div class="lv6-name">{{ acc.username || `UID:${acc.uid}` }}</div>
            <div v-if="acc.lv6_estimate?.already_reached" class="lv6-reached">
              已达 LV{{ acc.lv6_estimate.current_level }} ✨
            </div>
            <div v-else-if="acc.lv6_estimate" class="lv6-detail">
              <div class="lv6-progress-text">
                还差 <strong>{{ acc.lv6_estimate.exp_remaining }}</strong> 经验
                ({{ acc.lv6_estimate.current_exp }}/{{ acc.lv6_estimate.lv6_threshold }})
              </div>
              <div v-if="acc.lv6_estimate.avg_daily_exp > 0" class="lv6-eta">
                按日均 <strong>{{ acc.lv6_estimate.avg_daily_exp }}</strong> exp 算：
                <strong>{{ acc.lv6_estimate.est_days_to_lv6 }}</strong> 天后
                <span class="lv6-date">({{ acc.lv6_estimate.est_date }})</span>
              </div>
              <div v-else class="lv6-no-data">
                数据不足：需积累 2 次以上经验快照（每 6h 一次，需等待 ≥6h）
              </div>
            </div>
          </div>
        </div>
      </el-card>

      <!-- 今日任务统计 -->
      <el-card class="section-card" shadow="never">
        <template #header><span class="section-title">今日任务</span></template>
        <div v-if="!todayStats || todayStats.total_tasks === 0" class="empty-text">今日暂无任务记录</div>
        <div v-else class="task-stats">
          <div class="task-stat-row">
            <span>总任务</span><strong>{{ todayStats.total_tasks }}</strong>
          </div>
          <div class="task-stat-row">
            <span style="color: var(--kyi-success)">成功</span>
            <strong style="color: var(--kyi-success)">{{ todayStats.success_count }}</strong>
          </div>
          <div class="task-stat-row">
            <span style="color: var(--kyi-danger)">失败</span>
            <strong style="color: var(--kyi-danger)">{{ todayStats.failed_count }}</strong>
          </div>
          <div class="task-stat-row">
            <span style="color: var(--kyi-text-secondary)">跳过</span>
            <strong style="color: var(--kyi-text-secondary)">{{ todayStats.skipped_count }}</strong>
          </div>
        </div>
      </el-card>
    </div>

    <!-- 最近日志 -->
    <el-card class="section-card" shadow="never">
      <template #header><span class="section-title">最近执行</span></template>
      <div v-if="!data?.recent_logs.length" class="empty-text">暂无执行记录</div>
      <div v-else class="recent-logs">
        <div v-for="log in data.recent_logs" :key="log.id" class="log-row">
          <span class="log-time">{{ log.created_at?.slice(11, 16) }}</span>
          <span class="log-account">{{ log.account_name || log.account_uid }}</span>
          <span class="log-type">{{ taskTypeMap[log.task_type] || log.task_type }}</span>
          <span class="log-status" :style="{ color: statusColor[log.status] || 'inherit' }">{{ log.status }}</span>
          <span class="log-exp" v-if="log.exp_gained">+{{ log.exp_gained }}exp</span>
          <span class="log-msg" v-if="log.message">{{ log.message }}</span>
        </div>
      </div>
    </el-card>
  </div>
</template>

<style scoped>
.dashboard-view {
  display: flex;
  flex-direction: column;
  gap: 24px;
}

.welcome-banner {
  position: relative;
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 28px 36px;
  background: linear-gradient(135deg, rgba(251, 114, 153, 0.08), rgba(35, 173, 229, 0.08));
  border: 1px solid var(--kyi-border, #ebeef5);
  border-radius: 16px;
  overflow: hidden;
  min-height: 180px;
}

.welcome-banner__content {
  position: relative;
  z-index: 2;
  flex: 1;
  min-width: 0;
}

.welcome-banner__title {
  margin: 0;
  font-size: 24px;
  font-weight: 700;
  background: linear-gradient(90deg, #FB7299, #23ADE5);
  -webkit-background-clip: text;
  background-clip: text;
  color: transparent;
}

.welcome-banner__sub {
  margin: 8px 0 0;
  font-size: 13px;
  color: var(--kyi-text-secondary);
}

.welcome-banner__mascot {
  width: 200px;
  height: 140px;
  object-fit: cover;          /* 关键：多比例图片自适应裁剪 */
  object-position: center;     /* 聚焦画面中央，避免人物被裁掉 */
  border-radius: 12px;
  box-shadow: 0 6px 20px rgba(251, 114, 153, 0.18), 0 6px 20px rgba(35, 173, 229, 0.18);
  transform: rotate(-2deg);
  transition: transform 0.3s ease;
  flex-shrink: 0;
  margin-left: 24px;
}

.welcome-banner__mascot:hover {
  transform: rotate(0deg) scale(1.04);
}

.stat-cards {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
  gap: 20px;
}

.stat-card {
  border-radius: var(--kyi-border-radius);
}

.stat-card :deep(.el-card__body) {
  display: flex;
  align-items: center;
  gap: 16px;
  padding: 20px;
}

.stat-card__icon {
  width: 48px;
  height: 48px;
  border-radius: 12px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 22px;
  color: #fff;
  flex-shrink: 0;
}

.stat-card__value {
  font-size: 24px;
  font-weight: 700;
  color: var(--kyi-text);
}

.stat-card__label {
  margin-top: 4px;
  font-size: 13px;
  color: var(--kyi-text-secondary);
}

.dashboard-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 20px;
}

.section-card {
  border-radius: var(--kyi-border-radius);
}

.section-title {
  font-weight: 600;
  color: var(--kyi-text);
}

.empty-text {
  color: var(--kyi-text-secondary);
  font-size: 14px;
  padding: 20px 0;
  text-align: center;
}

.account-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.account-item {
  display: flex;
  align-items: center;
  gap: 12px;
}

.account-avatar {
  width: 36px;
  height: 36px;
  border-radius: 50%;
  background: var(--kyi-primary);
  color: #fff;
  display: flex;
  align-items: center;
  justify-content: center;
  font-weight: 700;
  flex-shrink: 0;
}

.account-info {
  flex: 1;
  min-width: 0;
}

.account-name {
  font-size: 14px;
  color: var(--kyi-text);
}

.account-level {
  font-size: 12px;
  color: var(--kyi-secondary);
  margin-left: 4px;
}

.account-exp {
  font-size: 12px;
  color: var(--kyi-text-secondary);
  margin-top: 2px;
}

.account-coins {
  margin-left: 8px;
}

.account-today {
  font-size: 14px;
  font-weight: 600;
  color: var(--kyi-success);
}

/* LV6 预估卡片 */
.lv6-card {
  background: linear-gradient(135deg, rgba(251, 114, 153, 0.04), rgba(35, 173, 229, 0.04));
}

.lv6-list {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.lv6-row {
  display: flex;
  flex-direction: column;
  gap: 6px;
  padding: 12px 14px;
  border-radius: 10px;
  background: var(--kyi-card-bg, rgba(255, 255, 255, 0.5));
  border: 1px solid var(--kyi-border, #ebeef5);
}

.lv6-name {
  font-size: 14px;
  font-weight: 600;
  color: var(--kyi-text);
}

.lv6-reached {
  font-size: 13px;
  color: var(--kyi-secondary);
  font-weight: 600;
}

.lv6-detail {
  font-size: 13px;
  color: var(--kyi-text-secondary);
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.lv6-progress-text strong,
.lv6-eta strong {
  color: var(--kyi-primary);
  font-size: 14px;
}

.lv6-date {
  color: var(--kyi-text-secondary);
  font-size: 12px;
  margin-left: 4px;
}

.lv6-no-data {
  color: var(--kyi-text-secondary);
  font-size: 12px;
  font-style: italic;
}

.task-stats {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.task-stat-row {
  display: flex;
  justify-content: space-between;
  font-size: 14px;
  color: var(--kyi-text);
}

.recent-logs {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.log-row {
  display: flex;
  align-items: center;
  gap: 12px;
  font-size: 13px;
  padding: 6px 0;
  border-bottom: 1px solid var(--kyi-border, #ebeef5);
}

.log-row:last-child {
  border-bottom: none;
}

.log-time {
  color: var(--kyi-text-secondary);
  min-width: 40px;
}

.log-account {
  min-width: 80px;
  color: var(--kyi-text);
}

.log-type {
  min-width: 60px;
  color: var(--kyi-primary);
}

.log-status {
  min-width: 50px;
  font-weight: 600;
}

.log-exp {
  color: var(--kyi-success);
}

.log-msg {
  flex: 1;
  color: var(--kyi-text-secondary);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
</style>
