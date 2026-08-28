<script setup lang="ts">
import { ref, reactive, computed, watch, onMounted } from "vue";
import { useRoute } from "vue-router";
import { ElMessage, ElMessageBox } from "element-plus";
import {
  Coin,
  VideoPlay,
  Share,
  StarFilled,
  Money,
} from "@element-plus/icons-vue";
import KyiCard from "@/components/KyiCard.vue";
import { getAccounts } from "@/api/account";
import { getTaskConfigs, updateTaskConfig, triggerTask } from "@/api/task";
import { getLogById } from "@/api/log";
import type { Account, TaskConfig, CoinTier } from "@/types";

const route = useRoute();

const accounts = ref<Account[]>([]);
const selectedUid = ref<number | undefined>(undefined);
const taskConfigs = ref<TaskConfig[]>([]);
const loading = ref(false);
const saving = ref(false);

// 投币配置表单
const coinForm = reactive({
  enabled: true,
  mode: "fixed" as "fixed" | "smart",
  fixed_limit: 5,
  smart_tiers: [{ min_coins: 0, daily_limit: 5 }] as CoinTier[],
  reserve_coins: 10,
  target_mode: "recommend" as "specified" | "recommend",
  target_uids: [] as number[],
  fallback_to_recommend: true,
});

const coinSchedule = reactive({
  schedule_mode: "random" as "fixed" | "random",
  fixed_time: "08:00",
  random_start: "08:00",
  random_end: "23:00",
  min_interval_minutes: 30,
});

// 其他任务简单表单
const taskSimple = reactive<Record<string, { enabled: boolean; duration_seconds: number; source: string }>>({
  watch: { enabled: true, duration_seconds: 310, source: "recommend" },
  share: { enabled: true, duration_seconds: 30, source: "recommend" },
  live_sign: { enabled: false, duration_seconds: 30, source: "recommend" },
  silver2coin: { enabled: false, duration_seconds: 30, source: "recommend" },
});

// 观看/分享调度配置
const simpleSchedule = reactive<Record<string, { schedule_mode: "fixed" | "random"; fixed_time: string; random_start: string; random_end: string; min_interval_minutes: number }>>({
  watch: { schedule_mode: "random", fixed_time: "08:00", random_start: "08:00", random_end: "23:00", min_interval_minutes: 60 },
  share: { schedule_mode: "random", fixed_time: "08:00", random_start: "08:00", random_end: "23:00", min_interval_minutes: 60 },
});

const testing = ref(false);

const uidInput = ref("");
const activeTab = ref("coin");

const currentAccount = computed(() =>
  accounts.value.find((a) => a.uid === selectedUid.value)
);

const plannedCoins = computed((): number => {
  const coins = currentAccount.value?.coins ?? 0;
  let plan = 0;
  if (coinForm.mode === "fixed") {
    plan = coinForm.fixed_limit;
  } else {
    const tiers = [...coinForm.smart_tiers].sort((a, b) => b.min_coins - a.min_coins);
    for (const tier of tiers) {
      if (coins >= tier.min_coins) {
        plan = tier.daily_limit;
        break;
      }
    }
  }
  if (plan + coinForm.reserve_coins > coins) {
    plan = Math.max(0, coins - coinForm.reserve_coins);
  }
  return plan;
});

onMounted(async () => {
  await loadAccounts();
  const queryUid = Number(route.query.uid);
  if (queryUid && accounts.value.some((a) => a.uid === queryUid)) {
    selectedUid.value = queryUid;
  }
});

async function loadAccounts(): Promise<void> {
  try {
    accounts.value = await getAccounts();
    if (accounts.value.length > 0 && !selectedUid.value) {
      selectedUid.value = accounts.value[0].uid;
    }
  } catch {
    accounts.value = [];
  }
}

watch(selectedUid, async (uid) => {
  if (!uid) return;
  await loadTaskConfigs(uid);
});

async function loadTaskConfigs(uid: number): Promise<void> {
  loading.value = true;
  try {
    taskConfigs.value = await getTaskConfigs(uid);
    applyConfigsToForms();
  } catch {
    taskConfigs.value = [];
  } finally {
    loading.value = false;
  }
}

function getTaskConfig(taskType: string): TaskConfig | undefined {
  return taskConfigs.value.find((c) => c.task_type === taskType);
}

function applyConfigsToForms(): void {
  const coinCfg = getTaskConfig("coin");
  if (coinCfg) {
    const cfg = (coinCfg.config || {}) as Record<string, unknown>;
    coinForm.enabled = coinCfg.enabled;
    coinForm.mode = (cfg.mode as "fixed" | "smart") || "fixed";
    coinForm.fixed_limit = (cfg.fixed_limit as number) ?? 5;
    coinForm.smart_tiers = Array.isArray(cfg.smart_tiers)
      ? (cfg.smart_tiers as CoinTier[])
      : [{ min_coins: 0, daily_limit: 5 }];
    coinForm.reserve_coins = (cfg.reserve_coins as number) ?? 10;
    coinForm.target_mode = (cfg.target_mode as "specified" | "recommend") || "recommend";
    coinForm.target_uids = Array.isArray(cfg.target_uids) ? (cfg.target_uids as number[]) : [];
    coinForm.fallback_to_recommend = (cfg.fallback_to_recommend as boolean) ?? true;

    coinSchedule.schedule_mode = (coinCfg.schedule_mode as "fixed" | "random") || "random";
    const sc = (coinCfg.schedule_config || {}) as Record<string, unknown>;
    coinSchedule.fixed_time = sc.hour != null
      ? `${String(sc.hour).padStart(2, "0")}:${String(sc.minute ?? 0).padStart(2, "0")}`
      : "08:00";
    if (sc.time_range && typeof sc.time_range === "object") {
      const tr = sc.time_range as Record<string, string>;
      coinSchedule.random_start = tr.start || "08:00";
      coinSchedule.random_end = tr.end || "23:00";
    } else {
      coinSchedule.random_start = "08:00";
      coinSchedule.random_end = "23:00";
    }
    coinSchedule.min_interval_minutes = (sc.min_interval_minutes as number) ?? 30;
  }

  for (const type of ["watch", "share", "live_sign", "silver2coin"] as const) {
    const cfg = getTaskConfig(type);
    const config = (cfg?.config || {}) as Record<string, unknown>;
    taskSimple[type] = {
      enabled: cfg?.enabled ?? true,
      duration_seconds: (config.duration_seconds as number) ?? (type === "watch" ? 310 : 30),
      source: (config.source as string) || "recommend",
    };
    // 观看/分享有调度配置
    if (type === "watch" || type === "share") {
      const sch = simpleSchedule[type];
      sch.schedule_mode = (cfg?.schedule_mode as "fixed" | "random") || "random";
      const sc = (cfg?.schedule_config || {}) as Record<string, unknown>;
      sch.fixed_time = sc.hour != null
        ? `${String(sc.hour).padStart(2, "0")}:${String(sc.minute ?? 0).padStart(2, "0")}`
        : "08:00";
      if (sc.time_range && typeof sc.time_range === "object") {
        const tr = sc.time_range as Record<string, string>;
        sch.random_start = tr.start || "08:00";
        sch.random_end = tr.end || "23:00";
      }
      sch.min_interval_minutes = (sc.min_interval_minutes as number) ?? 60;
    }
  }
}

function addSmartTier(): void {
  if (coinForm.smart_tiers.length >= 5) {
    ElMessage.warning("最多 5 个档位");
    return;
  }
  coinForm.smart_tiers.push({ min_coins: 0, daily_limit: 5 });
}

function removeSmartTier(index: number): void {
  coinForm.smart_tiers.splice(index, 1);
}

function addTargetUid(): void {
  const uid = Number(uidInput.value);
  if (!uid || uid <= 0) {
    ElMessage.warning("请输入有效 UID");
    return;
  }
  if (!coinForm.target_uids.includes(uid)) {
    coinForm.target_uids.push(uid);
  }
  uidInput.value = "";
}

function removeTargetUid(index: number): void {
  coinForm.target_uids.splice(index, 1);
}

function parseTime(time: string): { hour: number; minute: number } {
  const [h, m] = time.split(":").map(Number);
  return { hour: isNaN(h) ? 8 : h, minute: isNaN(m) ? 0 : m };
}

function buildCoinPayload(): { config: Record<string, unknown>; schedule_config: Record<string, unknown>; enabled: boolean; schedule_mode: string } {
  const config: Record<string, unknown> = {
    mode: coinForm.mode,
    fixed_limit: coinForm.fixed_limit,
    smart_tiers: coinForm.smart_tiers,
    reserve_coins: coinForm.reserve_coins,
    target_mode: coinForm.target_mode,
    target_uids: coinForm.target_uids,
    fallback_to_recommend: coinForm.fallback_to_recommend,
  };
  const schedule_config: Record<string, unknown> =
    coinSchedule.schedule_mode === "fixed"
      ? { hour: parseTime(coinSchedule.fixed_time).hour, minute: parseTime(coinSchedule.fixed_time).minute }
      : {
          time_range: { start: coinSchedule.random_start, end: coinSchedule.random_end },
          min_interval_minutes: coinSchedule.min_interval_minutes,
          count: 3,
        };
  return { config, schedule_config, enabled: coinForm.enabled, schedule_mode: coinSchedule.schedule_mode };
}

async function saveCoinConfig(): Promise<void> {
  if (!selectedUid.value) return;
  saving.value = true;
  try {
    await updateTaskConfig(selectedUid.value, "coin", buildCoinPayload());
    ElMessage.success("投币任务配置已保存");
    await loadTaskConfigs(selectedUid.value);
  } finally {
    saving.value = false;
  }
}

async function saveSimpleConfig(taskType: string): Promise<void> {
  if (!selectedUid.value) return;
  const data = taskSimple[taskType];
  saving.value = true;
  try {
    const config: Record<string, unknown> = {};
    if (taskType === "watch") {
      config.duration_seconds = data.duration_seconds;
      config.source = data.source;
    }
    // 观看/分享有调度配置
    let scheduleMode = "random";
    let scheduleConfig: Record<string, unknown> = {};
    if (taskType === "watch" || taskType === "share") {
      const sch = simpleSchedule[taskType];
      scheduleMode = sch.schedule_mode;
      scheduleConfig = sch.schedule_mode === "fixed"
        ? { hour: parseTime(sch.fixed_time).hour, minute: parseTime(sch.fixed_time).minute }
        : {
            time_range: { start: sch.random_start, end: sch.random_end },
            min_interval_minutes: sch.min_interval_minutes,
            count: 3,
          };
    }
    await updateTaskConfig(selectedUid.value, taskType, {
      config,
      schedule_config: scheduleConfig,
      enabled: data.enabled,
      schedule_mode: scheduleMode,
    });
    ElMessage.success("配置已保存");
    await loadTaskConfigs(selectedUid.value);
  } finally {
    saving.value = false;
  }
}

async function sleep(ms: number): Promise<void> {
  await new Promise((r) => setTimeout(r, ms));
}

async function testTask(taskType: string): Promise<void> {
  if (!selectedUid.value) return;
  testing.value = true;
  const taskNames: Record<string, string> = {
    coin: "投币", watch: "观看", share: "分享",
    live_sign: "直播签到", silver2coin: "银瓜子换币",
  };
  const label = taskNames[taskType] || taskType;
  try {
    const res = await triggerTask(selectedUid.value, taskType);

    // 如果 trigger 返回 running，轮询日志最终状态（最长 90s）
    let finalStatus = res.status;
    let finalMessage = "";
    let finalExp = 0;
    if (res.status === "running" || res.status === "pending") {
      ElMessage.info(`${label}任务开始执行，请稍候...`);
      const maxWait = 90_000;
      const step = 2_500;
      const logId = (res as unknown as { task_log_id?: number }).task_log_id;
      const started = Date.now();
      while (Date.now() - started < maxWait) {
        await sleep(step);
        if (!logId) break;
        try {
          const log = await getLogById(logId);
          if (log.status === "success" || log.status === "failed" || log.status === "skipped") {
            finalStatus = log.status;
            finalMessage = log.message || "";
            finalExp = log.exp_gained || 0;
            break;
          }
        } catch {
          // 404/网络错误忽略，下轮再试
        }
      }
    }

    if (finalStatus === "success") {
      ElMessage.success(
        finalExp > 0 ? `${label} 任务成功，获得经验 +${finalExp}` : `${label} 任务成功`
      );
    } else if (finalStatus === "skipped") {
      ElMessage.warning(`${label} 任务被跳过（${finalMessage || "可能今日已执行"}）`);
    } else if (finalStatus === "running" || finalStatus === "pending") {
      ElMessage.info(`${label} 任务仍在后台执行中，请到执行日志查看结果`);
    } else {
      ElMessage.error(`${label} 任务失败：${finalMessage || "未知错误"}`);
    }
    await loadTaskConfigs(selectedUid.value);
  } catch (e) {
    const msg = (e as { message?: string })?.message || "";
    ElMessage.error(`${label} 任务触发失败：${msg || "请检查后端日志"}`);
  } finally {
    testing.value = false;
  }
}

/** 0.2.1：开关切换即"保存生效"，不再需要用户再手动点保存。
 *
 *  - 开启：直接调 updateTaskConfig 保存 enabled=true（保留当前该任务表单其他值）
 *  - 关闭：弹「确定关闭该任务吗？」，确认 → 调 updateTaskConfig 保存 enabled=false
 *           取消 → 把开关重新拨回去，不调用后端
 *
 *  注意：enabled=false 时，UI 会通过 :disabled 让卡片内除开关外的控件全部不可交互，
 *        并整体变灰（见 :class="cardDisabled(...) 和 CSS）。
 */
async function saveCoinPayloadOnly(partial: { enabled?: boolean }): Promise<void> {
  if (!selectedUid.value) return;
  const payload = buildCoinPayload();
  if (partial.enabled !== undefined) payload.enabled = partial.enabled;
  await updateTaskConfig(selectedUid.value, "coin", payload);
}

async function saveSimplePayloadOnly(
  taskType: "watch" | "share",
  partial: { enabled?: boolean }
): Promise<void> {
  if (!selectedUid.value) return;
  const data = taskSimple[taskType];
  const config: Record<string, unknown> = {};
  if (taskType === "watch") {
    config.duration_seconds = data.duration_seconds;
    config.source = data.source;
  }
  const sch = simpleSchedule[taskType];
  const scheduleMode = sch.schedule_mode;
  const scheduleConfig = sch.schedule_mode === "fixed"
    ? { hour: parseTime(sch.fixed_time).hour, minute: parseTime(sch.fixed_time).minute }
    : {
        time_range: { start: sch.random_start, end: sch.random_end },
        min_interval_minutes: sch.min_interval_minutes,
        count: 3,
      };
  await updateTaskConfig(selectedUid.value, taskType, {
    config,
    schedule_config: scheduleConfig,
    enabled: partial.enabled ?? data.enabled,
    schedule_mode: scheduleMode,
  });
}

const switchSaving = reactive<Record<string, boolean>>({
  coin: false, watch: false, share: false,
});

const taskNamesZh: Record<string, string> = {
  coin: "投币", watch: "观看", share: "分享",
};

async function toggleTaskEnabled(taskType: "coin" | "watch" | "share", nextEnabled: boolean): Promise<void> {
  // 关闭：先弹确认，取消则回滚开关
  if (!nextEnabled) {
    try {
      await ElMessageBox.confirm(
        "关闭后该任务不会再执行，确定关闭该任务吗？",
        "关闭任务",
        { confirmButtonText: "关闭", cancelButtonText: "取消", type: "warning" },
      );
    } catch {
      // 用户取消：把开关回滚到 true
      if (taskType === "coin") {
        coinForm.enabled = true;
      } else {
        taskSimple[taskType].enabled = true;
      }
      return;
    }
  }

  switchSaving[taskType] = true;
  const zh = taskNamesZh[taskType] || taskType;
  try {
    if (taskType === "coin") {
      await saveCoinPayloadOnly({ enabled: nextEnabled });
    } else {
      await saveSimplePayloadOnly(taskType, { enabled: nextEnabled });
    }
    ElMessage.success(nextEnabled ? `${zh}任务已启用` : `${zh}任务已关闭`);
    if (selectedUid.value != null) {
      await loadTaskConfigs(selectedUid.value);
    }
  } catch (err: any) {
    // 失败：把开关回滚
    ElMessage.error(`保存失败：${err?.message || "未知错误"}`);
    if (taskType === "coin") {
      coinForm.enabled = !nextEnabled;
    } else {
      taskSimple[taskType].enabled = !nextEnabled;
    }
  } finally {
    switchSaving[taskType] = false;
  }
}

/** 用于给除开关外元素加 :disabled 的 getter。 */
function isTaskDisabled(taskType: "coin" | "watch" | "share"): boolean {
  if (taskType === "coin") return !coinForm.enabled;
  return !taskSimple[taskType].enabled;
}

// 直播签到 / 银瓜子换币：开关固定关闭，点击给"开发中"提示
function notifyDeveloping(): void {
  ElMessage.info("功能开发中，敬请期待 ~");
}
</script>

<template>
  <div class="task-config">
    <div class="page-header">
      <h2 class="page-title">任务配置</h2>
      <el-select
        v-model="selectedUid"
        placeholder="选择账号"
        style="width: 220px"
        :disabled="accounts.length === 0"
      >
        <el-option
          v-for="acc in accounts"
          :key="acc.uid"
          :label="`${acc.username || '未命名'} (UID:${acc.uid})`"
          :value="acc.uid"
        />
      </el-select>
    </div>

    <div v-if="!selectedUid" class="empty-state">
      <el-empty description="还没有账号，请先去账号管理添加 ~" />
    </div>

    <div v-else v-loading="loading">
      <el-tabs v-model="activeTab" type="border-card">
        <!-- 投币 -->
        <el-tab-pane name="coin" label="投币">
          <template #label>
            <span class="tab-label"><el-icon><Coin /></el-icon> 投币</span>
          </template>

          <KyiCard
            title="投币任务"
            icon="🪙"
            color="var(--kyi-primary)"
            :class="{ 'disabled-task-card': isTaskDisabled('coin') }"
          >
            <div class="coin-summary">
              当前账号有 <strong>{{ currentAccount?.coins ?? 0 }}</strong> 个硬币，
              所以今天会投 <strong>{{ plannedCoins }}</strong> 个币
              （预计经验 +{{ plannedCoins * 10 }}）
            </div>

            <el-form label-width="120px" class="config-form">
              <el-form-item label="启用任务">
                <!-- 开关永远允许切换；关闭后其他控件变灰禁用 -->
                <el-switch
                  v-model="coinForm.enabled"
                  active-text="开"
                  inactive-text="关"
                  :loading="switchSaving.coin"
                  @change="(v: any) => toggleTaskEnabled('coin', v as boolean)"
                />
                <span class="inline-tip" v-if="isTaskDisabled('coin')">
                  已关闭：其他选项暂时不可编辑（打开开关即可恢复）
                </span>
              </el-form-item>

              <el-form-item label="投币模式">
                <el-radio-group v-model="coinForm.mode" :disabled="isTaskDisabled('coin')">
                  <el-radio-button label="fixed">固定数量</el-radio-button>
                  <el-radio-button label="smart">智能档位</el-radio-button>
                </el-radio-group>
              </el-form-item>

              <template v-if="coinForm.mode === 'fixed'">
                <el-form-item label="每日投币数">
                  <el-slider
                    v-model="coinForm.fixed_limit"
                    :min="1"
                    :max="5"
                    show-stops
                    :disabled="isTaskDisabled('coin')"
                  />
                  <div class="form-tip">可获得 {{ coinForm.fixed_limit * 10 }} 经验</div>
                </el-form-item>
              </template>

              <template v-else>
                <el-form-item label="智能档位">
                  <div class="tier-list">
                    <div
                      v-for="(tier, idx) in coinForm.smart_tiers"
                      :key="idx"
                      class="tier-row"
                      :class="{ 'row-disabled': isTaskDisabled('coin') }"
                    >
                      <span>当硬币 ≥</span>
                      <el-input-number
                        v-model="tier.min_coins"
                        :min="0"
                        :step="10"
                        :disabled="isTaskDisabled('coin')"
                      />
                      <span>时，每天投</span>
                      <el-input-number
                        v-model="tier.daily_limit"
                        :min="1"
                        :max="5"
                        :disabled="isTaskDisabled('coin')"
                      />
                      <span>个</span>
                      <el-button
                        type="danger"
                        link
                        :disabled="isTaskDisabled('coin')"
                        @click="removeSmartTier(idx)"
                      >删除</el-button>
                    </div>
                    <el-button
                      type="primary"
                      link
                      :disabled="isTaskDisabled('coin')"
                      @click="addSmartTier"
                    >+ 添加档位</el-button>
                  </div>
                </el-form-item>
              </template>

              <el-form-item label="保留硬币">
                <el-input-number
                  v-model="coinForm.reserve_coins"
                  :min="0"
                  :step="1"
                  :disabled="isTaskDisabled('coin')"
                />
                <span class="form-tip">剩余硬币不会低于该值</span>
              </el-form-item>

              <el-form-item label="目标来源">
                <el-radio-group v-model="coinForm.target_mode" :disabled="isTaskDisabled('coin')">
                  <el-radio-button label="specified">指定 UP</el-radio-button>
                  <el-radio-button label="recommend">推荐视频</el-radio-button>
                </el-radio-group>
              </el-form-item>

              <template v-if="coinForm.target_mode === 'specified'">
                <el-form-item label="UID 列表">
                  <div class="uid-input-row">
                    <el-input
                      v-model="uidInput"
                      placeholder="输入 UID 后回车或点击添加"
                      :disabled="isTaskDisabled('coin')"
                      @keyup.enter="addTargetUid"
                    />
                    <el-button
                      type="primary"
                      :disabled="isTaskDisabled('coin')"
                      @click="addTargetUid"
                    >添加</el-button>
                  </div>
                  <div class="uid-tags">
                    <el-tag
                      v-for="(uid, idx) in coinForm.target_uids"
                      :key="uid"
                      :closable="!isTaskDisabled('coin')"
                      @close="removeTargetUid(idx)"
                    >
                      {{ uid }}
                    </el-tag>
                  </div>
                  <el-checkbox
                    v-model="coinForm.fallback_to_recommend"
                    :disabled="isTaskDisabled('coin')"
                  >
                    指定 UP 视频不足时 fallback 到推荐
                  </el-checkbox>
                </el-form-item>
              </template>

              <el-form-item label="调度方式">
                <el-radio-group v-model="coinSchedule.schedule_mode" :disabled="isTaskDisabled('coin')">
                  <el-radio-button label="fixed">固定时间</el-radio-button>
                  <el-radio-button label="random">随机时间</el-radio-button>
                </el-radio-group>
              </el-form-item>

              <el-form-item v-if="coinSchedule.schedule_mode === 'fixed'" label="执行时间">
                <el-time-picker
                  v-model="coinSchedule.fixed_time"
                  format="HH:mm"
                  value-format="HH:mm"
                  :disabled="isTaskDisabled('coin')"
                />
              </el-form-item>

              <template v-else>
                <el-form-item label="时间范围">
                  <el-time-picker
                    v-model="coinSchedule.random_start"
                    format="HH:mm"
                    value-format="HH:mm"
                    placeholder="开始"
                    :disabled="isTaskDisabled('coin')"
                  />
                  <span style="margin: 0 8px">至</span>
                  <el-time-picker
                    v-model="coinSchedule.random_end"
                    format="HH:mm"
                    value-format="HH:mm"
                    placeholder="结束"
                    :disabled="isTaskDisabled('coin')"
                  />
                </el-form-item>
                <el-form-item label="最小间隔">
                  <el-input-number
                    v-model="coinSchedule.min_interval_minutes"
                    :min="5"
                    :max="240"
                    :step="5"
                    :disabled="isTaskDisabled('coin')"
                  />
                  <span class="form-tip">分钟</span>
                </el-form-item>
              </template>

              <el-form-item>
                <el-button
                  type="primary"
                  :loading="saving"
                  :disabled="isTaskDisabled('coin')"
                  @click="saveCoinConfig"
                >保存投币配置</el-button>
                <el-button
                  :loading="testing"
                  :disabled="isTaskDisabled('coin')"
                  @click="testTask('coin')"
                >立即测试</el-button>
              </el-form-item>
            </el-form>
          </KyiCard>
        </el-tab-pane>

        <!-- 观看 -->
        <el-tab-pane name="watch" label="观看">
          <template #label>
            <span class="tab-label"><el-icon><VideoPlay /></el-icon> 观看</span>
          </template>
          <KyiCard
            title="观看任务"
            icon="▶️"
            color="var(--kyi-secondary)"
            :class="{ 'disabled-task-card': isTaskDisabled('watch') }"
          >
            <el-form label-width="120px" class="config-form">
              <el-form-item label="启用任务">
                <el-switch
                  v-model="taskSimple.watch.enabled"
                  :loading="switchSaving.watch"
                  @change="(v: any) => toggleTaskEnabled('watch', v as boolean)"
                />
                <span class="inline-tip" v-if="isTaskDisabled('watch')">
                  已关闭：其他选项暂时不可编辑（打开开关即可恢复）
                </span>
              </el-form-item>
              <el-form-item label="观看时长">
                <el-radio-group
                  v-model="taskSimple.watch.duration_seconds"
                  :disabled="isTaskDisabled('watch')"
                >
                  <el-radio-button :label="300">300 秒（5 分钟·保底）</el-radio-button>
                  <el-radio-button :label="310">310 秒（推荐）</el-radio-button>
                  <el-radio-button :label="350">350 秒（保守）</el-radio-button>
                </el-radio-group>
                <div class="form-tip">B 站规则：连续观看视频累计 ≥ 300 秒才能拿 +5 经验，时长不够拿不到</div>
              </el-form-item>
              <el-form-item label="调度方式">
                <el-radio-group
                  v-model="simpleSchedule.watch.schedule_mode"
                  :disabled="isTaskDisabled('watch')"
                >
                  <el-radio-button label="fixed">固定时间</el-radio-button>
                  <el-radio-button label="random">随机时间</el-radio-button>
                </el-radio-group>
              </el-form-item>
              <el-form-item v-if="simpleSchedule.watch.schedule_mode === 'fixed'" label="执行时间">
                <el-time-picker
                  v-model="simpleSchedule.watch.fixed_time"
                  format="HH:mm"
                  value-format="HH:mm"
                  :disabled="isTaskDisabled('watch')"
                />
              </el-form-item>
              <template v-else>
                <el-form-item label="时间范围">
                  <el-time-picker
                    v-model="simpleSchedule.watch.random_start"
                    format="HH:mm"
                    value-format="HH:mm"
                    placeholder="开始"
                    :disabled="isTaskDisabled('watch')"
                  />
                  <span style="margin: 0 8px">至</span>
                  <el-time-picker
                    v-model="simpleSchedule.watch.random_end"
                    format="HH:mm"
                    value-format="HH:mm"
                    placeholder="结束"
                    :disabled="isTaskDisabled('watch')"
                  />
                </el-form-item>
                <el-form-item label="最小间隔">
                  <el-input-number
                    v-model="simpleSchedule.watch.min_interval_minutes"
                    :min="5"
                    :max="240"
                    :step="5"
                    :disabled="isTaskDisabled('watch')"
                  />
                  <span class="form-tip">分钟</span>
                </el-form-item>
              </template>
              <el-form-item>
                <el-button
                  type="primary"
                  :loading="saving"
                  :disabled="isTaskDisabled('watch')"
                  @click="saveSimpleConfig('watch')"
                >保存观看配置</el-button>
                <el-button
                  :loading="testing"
                  :disabled="isTaskDisabled('watch')"
                  @click="testTask('watch')"
                >立即测试</el-button>
              </el-form-item>
            </el-form>
          </KyiCard>
        </el-tab-pane>

        <!-- 分享 -->
        <el-tab-pane name="share" label="分享">
          <template #label>
            <span class="tab-label"><el-icon><Share /></el-icon> 分享</span>
          </template>
          <KyiCard
            title="分享任务"
            icon="🔗"
            color="var(--kyi-success)"
            :class="{ 'disabled-task-card': isTaskDisabled('share') }"
          >
            <el-form label-width="120px" class="config-form">
              <el-form-item label="启用任务">
                <el-switch
                  v-model="taskSimple.share.enabled"
                  active-text="开"
                  inactive-text="关"
                  :loading="switchSaving.share"
                  @change="(v: any) => toggleTaskEnabled('share', v as boolean)"
                />
                <span class="inline-tip" v-if="isTaskDisabled('share')">
                  已关闭：其他选项暂时不可编辑（打开开关即可恢复）
                </span>
              </el-form-item>
              <el-form-item label="调度方式">
                <el-radio-group
                  v-model="simpleSchedule.share.schedule_mode"
                  :disabled="isTaskDisabled('share')"
                >
                  <el-radio-button label="fixed">固定时间</el-radio-button>
                  <el-radio-button label="random">随机时间</el-radio-button>
                </el-radio-group>
              </el-form-item>
              <el-form-item v-if="simpleSchedule.share.schedule_mode === 'fixed'" label="执行时间">
                <el-time-picker
                  v-model="simpleSchedule.share.fixed_time"
                  format="HH:mm"
                  value-format="HH:mm"
                  :disabled="isTaskDisabled('share')"
                />
              </el-form-item>
              <template v-else>
                <el-form-item label="时间范围">
                  <el-time-picker
                    v-model="simpleSchedule.share.random_start"
                    format="HH:mm"
                    value-format="HH:mm"
                    placeholder="开始"
                    :disabled="isTaskDisabled('share')"
                  />
                  <span style="margin: 0 8px">至</span>
                  <el-time-picker
                    v-model="simpleSchedule.share.random_end"
                    format="HH:mm"
                    value-format="HH:mm"
                    placeholder="结束"
                    :disabled="isTaskDisabled('share')"
                  />
                </el-form-item>
                <el-form-item label="最小间隔">
                  <el-input-number
                    v-model="simpleSchedule.share.min_interval_minutes"
                    :min="5"
                    :max="240"
                    :step="5"
                    :disabled="isTaskDisabled('share')"
                  />
                  <span class="form-tip">分钟</span>
                </el-form-item>
              </template>
              <el-form-item>
                <el-button
                  type="primary"
                  :loading="saving"
                  :disabled="isTaskDisabled('share')"
                  @click="saveSimpleConfig('share')"
                >保存分享配置</el-button>
                <el-button
                  :loading="testing"
                  :disabled="isTaskDisabled('share')"
                  @click="testTask('share')"
                >立即测试</el-button>
              </el-form-item>
            </el-form>
          </KyiCard>
        </el-tab-pane>

        <!-- 直播签到 -->
        <el-tab-pane name="live_sign" label="直播签到">
          <template #label>
            <span class="tab-label"><el-icon><StarFilled /></el-icon> 直播签到</span>
          </template>
          <KyiCard title="直播签到任务" icon="🎁" color="var(--kyi-warning)">
            <div class="coming-soon">
              <div class="coming-soon__icon">🚧</div>
              <div class="coming-soon__title">功能开发中</div>
              <div class="coming-soon__desc">直播签到功能正在紧锣密鼓地开发中，敬请期待 ~</div>
              <el-button type="primary" plain @click="notifyDeveloping">查看进度</el-button>
            </div>
          </KyiCard>
        </el-tab-pane>

        <!-- 银瓜子换币 -->
        <el-tab-pane name="silver2coin" label="银瓜子换币">
          <template #label>
            <span class="tab-label"><el-icon><Money /></el-icon> 银瓜子换币</span>
          </template>
          <KyiCard title="银瓜子兑换硬币" icon="💰" color="var(--kyi-danger)">
            <div class="coming-soon">
              <div class="coming-soon__icon">🚧</div>
              <div class="coming-soon__title">功能开发中</div>
              <div class="coming-soon__desc">银瓜子自动换硬币功能正在开发中，敬请期待 ~</div>
              <el-button type="primary" plain @click="notifyDeveloping">查看进度</el-button>
            </div>
          </KyiCard>
        </el-tab-pane>
      </el-tabs>
    </div>
  </div>
</template>

<style scoped>
.task-config {
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

.tab-label {
  display: inline-flex;
  align-items: center;
  gap: 4px;
}

.config-form {
  max-width: 720px;
}

.coin-summary {
  margin-bottom: 20px;
  padding: 12px 16px;
  background: var(--kyi-sidebar-active-bg);
  border-radius: 8px;
  color: var(--kyi-text);
  font-size: 14px;
}

.coin-summary strong {
  color: var(--kyi-primary);
}

.form-tip {
  margin-left: 12px;
  font-size: 12px;
  color: var(--kyi-text-secondary);
}

.tier-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.tier-row {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 14px;
  color: var(--kyi-text);
}

.uid-input-row {
  display: flex;
  gap: 8px;
}

.uid-tags {
  margin-top: 8px;
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.empty-state {
  margin-top: 40px;
}

.coming-soon {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 40px 20px;
  text-align: center;
  gap: 12px;
}

.coming-soon__icon {
  font-size: 56px;
  filter: grayscale(0.2);
  animation: swaying 2.5s ease-in-out infinite;
}

@keyframes swaying {
  0%, 100% { transform: rotate(-6deg); }
  50%      { transform: rotate(6deg); }
}

.coming-soon__title {
  font-size: 18px;
  font-weight: 700;
  color: var(--kyi-text);
}

.coming-soon__desc {
  font-size: 13px;
  color: var(--kyi-text-secondary);
  max-width: 360px;
}

/* 0.2.1 任务禁用态：整卡变灰（"启用任务"开关除外） */
.disabled-task-card {
  position: relative;
  filter: grayscale(0.2);
  opacity: 0.82;
  background-color: rgba(144, 147, 153, 0.03) !important;
  border: 1px dashed rgba(144, 147, 153, 0.35) !important;
  transition: opacity 0.2s ease;
}
.disabled-task-card:hover {
  opacity: 0.92;
}

/* 开关行内提示 */
.inline-tip {
  margin-left: 12px;
  font-size: 12px;
  color: var(--kyi-text-secondary);
  font-style: italic;
}

/* 禁用态 tier-row：按钮/输入框视觉更淡 */
.row-disabled {
  opacity: 0.85;
}
</style>
