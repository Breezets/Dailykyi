<script setup lang="ts">
import { ref, reactive, computed, onMounted, onUnmounted, watch } from "vue";
import { ElMessage } from "element-plus";
import KyiCard from "@/components/KyiCard.vue";
import KyiTimeline from "@/components/KyiTimeline.vue";
import { getLogs, getLogStream } from "@/api/log";
import { getAccounts } from "@/api/account";
import { formatDate } from "@/utils/date";
import type { TaskLog, Account } from "@/types";

const taskTypes = [
  { label: "全部", value: "" },
  { label: "投币", value: "coin" },
  { label: "观看", value: "watch" },
  { label: "分享", value: "share" },
  { label: "直播签到", value: "live_sign" },
  { label: "银瓜子换币", value: "silver2coin" },
];

const statuses = [
  { label: "全部", value: "" },
  { label: "成功", value: "success" },
  { label: "失败", value: "failed" },
  { label: "跳过", value: "skipped" },
  { label: "运行中", value: "running" },
];

const accounts = ref<Account[]>([]);
const logs = ref<TaskLog[]>([]);
const total = ref(0);
const loading = ref(false);
const liveMode = ref(false);
let eventSource: EventSource | null = null;

const filter = reactive({
  account_uid: undefined as number | undefined,
  task_type: "",
  status: "",
  date: "",
  page: 1,
  page_size: 10,
});

const accountMap = computed(() => {
  const map = new Map<number, string>();
  accounts.value.forEach((a) => map.set(a.uid, a.username || `UID:${a.uid}`));
  return map;
});

const displayLogs = computed(() =>
  logs.value.map((log) => ({
    ...log,
    account_name: accountMap.value.get(log.account_uid) || `UID:${log.account_uid}`,
  }))
);

onMounted(async () => {
  await loadAccounts();
  await loadLogs();
});

onUnmounted(stopLiveStream);

watch(liveMode, (on) => {
  if (on) {
    startLiveStream();
  } else {
    stopLiveStream();
  }
});

async function loadAccounts(): Promise<void> {
  try {
    accounts.value = await getAccounts();
  } catch {
    accounts.value = [];
  }
}

async function loadLogs(): Promise<void> {
  loading.value = true;
  try {
    const params: Record<string, unknown> = {
      limit: filter.page_size,
      offset: (filter.page - 1) * filter.page_size,
    };
    if (filter.account_uid) params.account_uid = filter.account_uid;
    if (filter.task_type) params.task_type = filter.task_type;
    if (filter.status) params.status = filter.status;
    if (filter.date) params.date = filter.date;
    const res = await getLogs(params);
    logs.value = res.logs || [];
    total.value = res.total || 0;
  } catch {
    logs.value = [];
    total.value = 0;
  } finally {
    loading.value = false;
  }
}

function onFilterChange(): void {
  filter.page = 1;
  void loadLogs();
}

function onPageChange(page: number): void {
  filter.page = page;
  void loadLogs();
}

function startLiveStream(): void {
  stopLiveStream();
  eventSource = getLogStream();
  eventSource.onmessage = (e) => {
    try {
      const log = JSON.parse(e.data) as TaskLog;
      logs.value.unshift(log);
      total.value += 1;
    } catch {
      // ignore malformed event
    }
  };
  eventSource.onerror = () => {
    ElMessage.warning("日志实时连接中断");
    liveMode.value = false;
  };
}

function stopLiveStream(): void {
  if (eventSource) {
    eventSource.close();
    eventSource = null;
  }
}
</script>

<template>
  <div class="log-viewer">
    <div class="page-header">
      <h2 class="page-title">执行日志</h2>
      <div class="live-toggle">
        <span class="live-label">实时模式</span>
        <el-switch v-model="liveMode" />
      </div>
    </div>

    <KyiCard title="筛选" icon="🔍" color="var(--kyi-secondary)">
      <div class="filter-bar">
        <el-select
          v-model="filter.account_uid"
          clearable
          placeholder="选择账号"
          style="width: 180px"
          @change="onFilterChange"
        >
          <el-option
            v-for="acc in accounts"
            :key="acc.uid"
            :label="acc.username || `UID:${acc.uid}`"
            :value="acc.uid"
          />
        </el-select>

        <el-select
          v-model="filter.task_type"
          clearable
          placeholder="任务类型"
          style="width: 140px"
          @change="onFilterChange"
        >
          <el-option
            v-for="t in taskTypes"
            :key="t.value"
            :label="t.label"
            :value="t.value"
          />
        </el-select>

        <el-select
          v-model="filter.status"
          clearable
          placeholder="状态"
          style="width: 120px"
          @change="onFilterChange"
        >
          <el-option
            v-for="s in statuses"
            :key="s.value"
            :label="s.label"
            :value="s.value"
          />
        </el-select>

        <el-date-picker
          v-model="filter.date"
          type="date"
          placeholder="选择日期"
          value-format="YYYY-MM-DD"
          @change="onFilterChange"
        />
      </div>
    </KyiCard>

    <KyiCard title="日志列表" icon="📜" color="var(--kyi-primary)">
      <div v-loading="loading" class="log-list">
        <KyiTimeline :logs="displayLogs" />

        <el-pagination
          v-if="!liveMode && total > 0"
          v-model:current-page="filter.page"
          :page-size="filter.page_size"
          :total="total"
          layout="prev, pager, next"
          @current-change="onPageChange"
        />
      </div>
    </KyiCard>
  </div>
</template>

<style scoped>
.log-viewer {
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

.live-toggle {
  display: flex;
  align-items: center;
  gap: 8px;
}

.live-label {
  font-size: 14px;
  color: var(--kyi-text-secondary);
}

.filter-bar {
  display: flex;
  flex-wrap: wrap;
  gap: 12px;
}

.log-list {
  display: flex;
  flex-direction: column;
  gap: 16px;
}
</style>
