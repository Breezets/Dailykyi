<script setup lang="ts">
import { computed, onMounted, reactive, ref } from "vue";
import { Refresh } from "@element-plus/icons-vue";
import KyiCard from "@/components/KyiCard.vue";
import {
  getExpSummary,
  listExpSnapshots,
  type DailySourceBucket,
  type ExpSnapshotItem,
} from "@/api/exp";
import { getAccounts } from "@/api/account";
import type { Account } from "@/types";
import { ElMessage } from "element-plus";

const accounts = ref<Account[]>([]);
const loading = ref(false);
const items = ref<ExpSnapshotItem[]>([]);
const total = ref(0);
const summary = ref<DailySourceBucket[]>([]);
const summaryLoading = ref(false);

const PAGE_SIZE = 50;

const filter = reactive({
  account_uid: undefined as number | undefined,
  // 多选：task / passive / manual
  sources: [] as Array<"task" | "passive" | "manual">,
  /** Dailykyi / 站外 过滤（undefined=全部）*/
  origin: undefined as "Dailykyi" | "站外" | undefined,
  date: "" as string,
  page: 1,
});

const totalGain7 = computed(() =>
  summary.value.reduce((s, d) => s + d.total_gain, 0)
);
const platformGain7 = computed(() =>
  summary.value.reduce((s, d) => s + d.task, 0)
);
const passiveGain7 = computed(() =>
  summary.value.reduce((s, d) => s + d.passive, 0)
);
const manualGain7 = computed(() =>
  summary.value.reduce((s, d) => s + d.manual, 0)
);

/** 平台 vs 站外：大颜色区分（颜色反差更大）*/
function originStyle(origin: string): { color: string; bg: string; ring: string } {
  switch (origin) {
    case "Dailykyi":
      return {
        color: "#0F766E",
        bg: "rgba(15, 118, 110, 0.10)",
        ring: "rgba(15, 118, 110, 0.35)",
      };
    case "站外":
    default:
      return {
        color: "#EA580C",
        bg: "rgba(234, 88, 12, 0.10)",
        ring: "rgba(234, 88, 12, 0.35)",
      };
  }
}

/** 列表某条 触发方式（source：task/passive/manual）对应的小标签颜色（账号卡同色系）*/
function sourceStyle(src: string): { color: string; bg: string; label: string } {
  switch (src) {
    case "task":
      return { color: "var(--kyi-primary)", bg: "rgba(35,173,229,0.08)", label: "自动任务" };
    case "manual":
      return { color: "#8B5CF6", bg: "rgba(139,92,246,0.08)", label: "手动校验触发" };
    case "passive":
    default:
      return { color: "var(--kyi-secondary)", bg: "rgba(251,114,153,0.08)", label: "自动同步触发" };
  }
}

/** 根据 filter.origin 做前端本地过滤（后端不支持 origin query 时也能用）*/
const displayedItems = computed(() => {
  if (!filter.origin) return items.value;
  return items.value.filter((r) => r.origin === filter.origin);
});

function deltaText(d: number) {
  if (d > 0) return `+${d}`;
  if (d < 0) return `${d}`;
  return "—";
}
function deltaClass(d: number) {
  if (d > 0) return "delta-pos";
  if (d < 0) return "delta-neg";
  return "delta-zero";
}

onMounted(async () => {
  await loadAccounts();
  await loadSummary();
  await loadList();
});

async function loadAccounts() {
  try {
    accounts.value = await getAccounts();
  } catch {
    accounts.value = [];
  }
}

async function loadSummary() {
  summaryLoading.value = true;
  try {
    const res = await getExpSummary(7);
    summary.value = res.last_7_days || [];
  } catch {
    summary.value = [];
  } finally {
    summaryLoading.value = false;
  }
}

async function loadList() {
  loading.value = true;
  try {
    const res = await listExpSnapshots({
      account_uid: filter.account_uid,
      source: filter.sources.join(","),
      date: filter.date,
      limit: PAGE_SIZE,
      offset: (filter.page - 1) * PAGE_SIZE,
    });
    items.value = res.items || [];
    total.value = res.total || 0;
  } catch (err: any) {
    items.value = [];
    total.value = 0;
    ElMessage.error(err?.message || "加载失败");
  } finally {
    loading.value = false;
  }
}

function onFilterChange() {
  filter.page = 1;
  void loadList();
}

function onPageChange(p: number) {
  filter.page = p;
  void loadList();
}

async function onRefreshAll() {
  await Promise.all([loadSummary(), loadList()]);
  ElMessage.success("已刷新");
}

function formatTime(s: string) {
  if (!s) return "";
  return s.replace("T", " ").slice(0, 19);
}

/** 周汇总柱状图最大刻度（用于百分比）*/
const chartMax = computed(() => {
  const m = Math.max(1, ...summary.value.map((d) => Math.max(d.total_gain, 1)));
  // 取 5 的倍数向上取整
  return Math.ceil(m / 5) * 5;
});
</script>

<template>
  <div class="exp-log-view">
    <div class="page-header">
      <h2 class="page-title">经验日志</h2>
      <el-button type="primary" plain :icon="Refresh" @click="onRefreshAll">刷新</el-button>
    </div>

    <!-- 顶部 7 日汇总 -->
    <KyiCard title="近 7 日经验拆分" icon="📊" color="var(--kyi-primary)">
      <div class="stat-tiles">
        <div class="stat-tile tile-total">
          <div class="stat-label">7 日合计</div>
          <div class="stat-value">+{{ totalGain7 }}</div>
        </div>
        <div class="stat-tile tile-platform">
          <div class="stat-label">平台任务</div>
          <div class="stat-value">+{{ platformGain7 }}</div>
        </div>
        <div class="stat-tile tile-passive">
          <div class="stat-label">自动同步</div>
          <div class="stat-value">+{{ passiveGain7 }}</div>
        </div>
        <div class="stat-tile tile-manual">
          <div class="stat-label">手动校验</div>
          <div class="stat-value">+{{ manualGain7 }}</div>
        </div>
      </div>

      <div class="week-chart" v-loading="summaryLoading">
        <div v-if="!summary.length" class="empty-text">暂无快照数据</div>
        <div v-else class="week-bars">
          <div v-for="d in summary" :key="d.date" class="week-bar-col">
            <div class="week-bar-total" :style="{ height: `${(d.total_gain / chartMax) * 100}%` }">
              <div
                class="bar-seg seg-task"
                :style="{ height: `${d.total_gain ? (d.task / d.total_gain) * 100 : 0}%` }"
              ></div>
              <div
                class="bar-seg seg-passive"
                :style="{ height: `${d.total_gain ? (d.passive / d.total_gain) * 100 : 0}%` }"
              ></div>
              <div
                class="bar-seg seg-manual"
                :style="{ height: `${d.total_gain ? (d.manual / d.total_gain) * 100 : 0}%` }"
              ></div>
            </div>
            <div class="week-bar-val" v-if="d.total_gain > 0">+{{ d.total_gain }}</div>
            <div class="week-bar-date">{{ d.date.slice(5) }}</div>
          </div>
        </div>
        <div class="week-legend">
          <span class="lg lg-task">平台任务</span>
          <span class="lg lg-passive">自动同步</span>
          <span class="lg lg-manual">手动校验</span>
        </div>
      </div>
    </KyiCard>

    <!-- 筛选 + 列表 -->
    <KyiCard title="经验事件明细" icon="📈" color="var(--kyi-secondary)">
      <div class="filter-bar">
        <el-select
          v-model="filter.account_uid"
          clearable
          placeholder="全部账号"
          style="width: 180px"
          @change="onFilterChange"
        >
          <el-option
            v-for="a in accounts"
            :key="a.uid"
            :label="a.username || `UID:${a.uid}`"
            :value="a.uid"
          />
        </el-select>
        <el-select
          v-model="filter.origin"
          clearable
          placeholder="产生来源"
          style="width: 220px"
          @change="onFilterChange"
        >
          <el-option label="Dailykyi 自动任务" value="Dailykyi">
            <span style="color:#0F766E;font-weight:600">● Dailykyi 自动任务</span>
          </el-option>
          <el-option label="站外来源（APP/网页）" value="站外">
            <span style="color:#EA580C;font-weight:600">● 站外来源（APP/网页/手动操作）</span>
          </el-option>
        </el-select>
        <el-select
          v-model="filter.sources"
          multiple
          collapse-tags
          collapse-tags-tooltip
          placeholder="触发方式（全部）"
          style="width: 260px"
          @change="onFilterChange"
        >
          <el-option label="自动任务触发" value="task" />
          <el-option label="自动同步（每 6h）" value="passive" />
          <el-option label="手动校验触发" value="manual" />
        </el-select>
        <el-date-picker
          v-model="filter.date"
          type="date"
          value-format="YYYY-MM-DD"
          placeholder="选择日期"
          clearable
          @change="onFilterChange"
        />
        <el-button plain @click="onFilterChange">查询</el-button>
      </div>

      <div class="exp-table-wrap" v-loading="loading">
        <el-table
          :data="displayedItems"
          stripe
          empty-text="暂无经验快照记录"
          style="width: 100%"
        >
          <el-table-column prop="recorded_at" label="时间" width="180">
            <template #default="{ row }">{{ formatTime(row.recorded_at) }}</template>
          </el-table-column>
          <el-table-column label="账号" min-width="150">
            <template #default="{ row }">
              <span>{{ row.account_name || `UID:${row.account_uid}` }}</span>
              <span class="uid-hint" v-if="row.account_name">（{{ row.account_uid }}）</span>
            </template>
          </el-table-column>
          <el-table-column label="产生来源" width="160">
            <template #default="{ row }">
              <span
                class="origin-tag"
                :style="{
                  color: originStyle(row.origin).color,
                  background: originStyle(row.origin).bg,
                  borderColor: originStyle(row.origin).ring,
                }"
                :title="row.origin_label"
              >
                {{ row.origin === 'Dailykyi' ? 'Dailykyi' : '站外' }}
              </span>
            </template>
          </el-table-column>
          <el-table-column label="触发方式" width="150">
            <template #default="{ row }">
              <span
                class="src-tag"
                :style="{ color: sourceStyle(row.source).color, background: sourceStyle(row.source).bg }"
                :title="sourceStyle(row.source).label"
              >
                {{ sourceStyle(row.source).label }}
              </span>
            </template>
          </el-table-column>
          <el-table-column label="等级" width="80" prop="level" />
          <el-table-column label="当前经验" width="140" prop="exp" align="right" />
          <el-table-column label="硬币" width="100" prop="coins" align="right" />
          <el-table-column label="变化" width="240" align="right">
            <template #default="{ row }">
              <div class="delta-block">
                <span :class="['delta-num', deltaClass(row.delta)]">{{ deltaText(row.delta) }}</span>
                <span class="delta-tip" v-if="row.delta !== 0">
                  （{{ row.prev_exp }} → {{ row.exp }}）
                </span>
                <span class="delta-tip" v-else>经验无变化</span>
              </div>
            </template>
          </el-table-column>
        </el-table>

        <el-pagination
          v-if="total > 0"
          v-model:current-page="filter.page"
          :page-size="PAGE_SIZE"
          :total="total"
          layout="total, prev, pager, next"
          style="justify-content: center; margin-top: 16px"
          @current-change="onPageChange"
        />
      </div>
    </KyiCard>
  </div>
</template>

<style scoped>
.exp-log-view {
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

/* ==== 顶部汇总 ==== */
.stat-tiles {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 16px;
  margin-bottom: 20px;
}
@media (max-width: 960px) {
  .stat-tiles { grid-template-columns: repeat(2, minmax(0, 1fr)); }
}
.stat-tile {
  padding: 14px 18px;
  border-radius: var(--kyi-border-radius, 10px);
  border: 1px solid var(--kyi-border, #ebeef5);
}
.stat-label { font-size: 13px; color: var(--kyi-text-secondary); }
.stat-value {
  margin-top: 4px;
  font-size: 22px;
  font-weight: 700;
}
.tile-total .stat-value { color: var(--kyi-success); }
.tile-platform .stat-value { color: var(--kyi-primary); }
.tile-passive .stat-value { color: var(--kyi-secondary); }
.tile-manual .stat-value { color: #8B5CF6; }

/* ==== 7 日堆叠柱状图 ==== */
.week-chart { min-height: 220px; display: flex; flex-direction: column; }
.week-bars {
  display: grid;
  grid-template-columns: repeat(7, minmax(0, 1fr));
  gap: 10px;
  align-items: end;
  height: 180px;
  padding: 0 6px;
}
.week-bar-col {
  display: flex;
  flex-direction: column;
  align-items: center;
  height: 100%;
  justify-content: end;
  gap: 6px;
}
.week-bar-total {
  width: 36px;
  min-height: 2px;
  border-radius: 6px 6px 2px 2px;
  background: linear-gradient(180deg, rgba(35,173,229,0.1), rgba(251,114,153,0.1));
  display: flex;
  flex-direction: column-reverse;
  overflow: hidden;
  border: 1px solid rgba(35,173,229,0.15);
}
.bar-seg { width: 100%; }
.seg-task { background: var(--kyi-primary); }
.seg-passive { background: var(--kyi-secondary); }
.seg-manual { background: #8B5CF6; }
.week-bar-val {
  font-size: 12px;
  color: var(--kyi-success);
  font-weight: 600;
}
.week-bar-date { font-size: 12px; color: var(--kyi-text-secondary); }

.week-legend {
  display: flex;
  gap: 16px;
  justify-content: center;
  margin-top: 14px;
  font-size: 12px;
  color: var(--kyi-text-secondary);
}
.week-legend .lg {
  display: inline-flex;
  align-items: center;
  gap: 6px;
}
.week-legend .lg::before {
  content: "";
  width: 10px;
  height: 10px;
  border-radius: 2px;
  display: inline-block;
}
.lg-task::before { background: var(--kyi-primary); }
.lg-passive::before { background: var(--kyi-secondary); }
.lg-manual::before { background: #8B5CF6; }

/* ==== 过滤 ==== */
.filter-bar {
  display: flex;
  gap: 12px;
  flex-wrap: wrap;
  margin-bottom: 16px;
}
.uid-hint {
  color: var(--kyi-text-secondary);
  font-size: 12px;
  margin-left: 4px;
}

/* ==== 来源标签 ==== */
.src-tag {
  display: inline-block;
  padding: 2px 10px;
  border-radius: 999px;
  font-size: 12px;
  font-weight: 600;
}

/* 产生来源标签：Dailykyi（青绿，更抢眼）vs 站外（橙）*/
.origin-tag {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  padding: 3px 12px;
  border-radius: 999px;
  font-size: 12px;
  font-weight: 700;
  border: 1px solid;
}
.origin-tag::before {
  content: "";
  width: 6px;
  height: 6px;
  border-radius: 50%;
  display: inline-block;
  background: currentColor;
}

/* ==== 变化列 ==== */
.delta-block {
  display: inline-flex;
  align-items: baseline;
  gap: 4px;
  flex-wrap: wrap;
  justify-content: flex-end;
}
.delta-num { font-weight: 700; font-size: 15px; }
.delta-pos { color: var(--kyi-success); }
.delta-neg { color: var(--kyi-danger); }
.delta-zero { color: var(--kyi-text-secondary); font-weight: 500; }
.delta-tip { font-size: 12px; color: var(--kyi-text-secondary); }

.empty-text {
  color: var(--kyi-text-secondary);
  font-size: 14px;
  padding: 24px 0;
  text-align: center;
}
</style>
