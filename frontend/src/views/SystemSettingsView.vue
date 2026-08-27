<script setup lang="ts">
import { ref, reactive, onMounted } from "vue";
import { ElMessage, ElMessageBox } from "element-plus";
import request from "@/api/request";
import { useThemeStore } from "@/stores/theme";
import { useAuthStore } from "@/stores/auth";
import {
  getSystemConfig,
  updateSystemConfig,
  testFailureNotification,
  checkUpgrade,
  runUpgrade,
  type TestFailureResult,
  type UpgradeCheckResult,
} from "@/api/system";
import KyiCard from "@/components/KyiCard.vue";

const theme = useThemeStore();
const auth = useAuthStore();

const notifyForm = reactive({
  server_chan_key: "",
  notify_on_failure: true,
  notify_on_success: false,
  notify_daily_summary: false,
  notify_cookie_warning: true,
  notify_risk_alert: true,
  dnd_enabled: false,
  dnd_start: "23:00",
  dnd_end: "08:00",
});

const riskForm = reactive({
  delay_min: 5,
  delay_max: 15,
  max_retries: 3,
  failure_threshold: 5,
});

const passwordForm = reactive({
  oldPassword: "",
  newPassword: "",
  confirmPassword: "",
});

// Debug
const testingFail = ref(false);
const failTestResult = ref<TestFailureResult | null>(null);

// 版本升级（0.2.0）
const currentVersion = ref("");
const checkingUpgrade = ref(false);
const upgrading = ref(false);
const upgradeResult = ref<UpgradeCheckResult | null>(null);

const savingNotify = ref(false);
const savingRisk = ref(false);
const changingPassword = ref(false);

onMounted(() => {
  loadAll();
  checkVersion();
});

/** 获取当前版本（/ 根接口） */
async function checkVersion(): Promise<void> {
  try {
    const res = await request.get<unknown, { version?: string }>("/");
    currentVersion.value = res.version || "";
  } catch {
    // 忽略
  }
}

/** 检查更新 */
async function onCheckUpgrade(): Promise<void> {
  checkingUpgrade.value = true;
  upgradeResult.value = null;
  try {
    upgradeResult.value = await checkUpgrade();
  } catch (e) {
    const msg = (e as { message?: string })?.message || "";
    ElMessage.error(`检查更新失败：${msg || "请查看后端日志"}`);
  } finally {
    checkingUpgrade.value = false;
  }
}

/** 一键升级 */
async function onRunUpgrade(): Promise<void> {
  try {
    await ElMessageBox.confirm(
      "升级将执行：git pull → 重新构建前端 → 重建并重启容器。\n期间面板会短暂不可用，确认继续？",
      "一键升级",
      { type: "warning", confirmButtonText: "开始升级", cancelButtonText: "取消" }
    );
  } catch {
    return; // 用户取消
  }
  upgrading.value = true;
  try {
    const res = await runUpgrade();
    if (res.started) {
      ElMessage.success(res.message || "升级已在后台执行，请稍后刷新页面");
    } else {
      ElMessage.error(res.error || "升级未启动");
    }
  } catch (e) {
    const msg = (e as { message?: string })?.message || "";
    ElMessage.error(`升级失败：${msg || "请查看后端日志"}`);
  } finally {
    upgrading.value = false;
  }
}

async function loadAll(): Promise<void> {
  try {
    const config = await getSystemConfig();
    // 顶层平铺（现在的正确格式）兼容老嵌套 notify 对象
    const src: Record<string, unknown> = (config.notify as Record<string, unknown> | undefined) ?? {};
    notifyForm.server_chan_key = toStr(src.server_chan_key ?? config.server_chan_key, "");
    notifyForm.notify_on_failure = toBool(src.notify_on_failure ?? config.notify_on_failure, true);
    notifyForm.notify_on_success = toBool(src.notify_on_success ?? config.notify_on_success, false);
    notifyForm.notify_daily_summary = toBool(src.notify_daily_summary ?? config.notify_daily_summary, false);
    notifyForm.notify_cookie_warning = toBool(src.notify_cookie_warning ?? config.notify_cookie_warning, true);
    notifyForm.notify_risk_alert = toBool(src.notify_risk_alert ?? config.notify_risk_alert, true);
    notifyForm.dnd_enabled = toBool(src.dnd_enabled ?? config.dnd_enabled, false);
    notifyForm.dnd_start = toStr(src.dnd_start ?? config.dnd_start, "23:00");
    notifyForm.dnd_end = toStr(src.dnd_end ?? config.dnd_end, "08:00");

    const risk = (config.risk_control || {}) as Record<string, unknown>;
    riskForm.delay_min = toNum(risk.delay_min ?? config.delay_min, 5);
    riskForm.delay_max = toNum(risk.delay_max ?? config.delay_max, 15);
    riskForm.max_retries = toNum(risk.max_retries ?? config.max_retries, 3);
    riskForm.failure_threshold = toNum(risk.failure_threshold ?? config.failure_threshold, 5);
  } catch {
    // 静默失败
  }
}

function toBool(v: unknown, d: boolean): boolean {
  if (typeof v === "boolean") return v;
  if (v === "true" || v === "1" || v === 1) return true;
  if (v === "false" || v === "0" || v === 0) return false;
  return d;
}
function toStr(v: unknown, d: string): string {
  if (v == null) return d;
  return String(v);
}
function toNum(v: unknown, d: number): number {
  if (v == null || Number.isNaN(v)) return d;
  const n = Number(v);
  return Number.isFinite(n) ? n : d;
}

async function saveNotify(): Promise<void> {
  savingNotify.value = true;
  try {
    await updateSystemConfig({ ...notifyForm });
    ElMessage.success("通知设置已保存");
    // 保存后立刻重新从后端拉一次确认写入内容
    await loadAll();
  } catch {
    ElMessage.error("保存失败");
  } finally {
    savingNotify.value = false;
  }
}

async function saveRisk(): Promise<void> {
  savingRisk.value = true;
  try {
    await updateSystemConfig({ risk_control: { ...riskForm }, ...riskForm });
    ElMessage.success("风控设置已保存");
    await loadAll();
  } catch {
    ElMessage.error("保存失败");
  } finally {
    savingRisk.value = false;
  }
}

async function changePassword(): Promise<void> {
  if (!passwordForm.oldPassword || !passwordForm.newPassword) {
    ElMessage.warning("请填写完整");
    return;
  }
  if (passwordForm.newPassword !== passwordForm.confirmPassword) {
    ElMessage.warning("两次输入的新密码不一致");
    return;
  }
  changingPassword.value = true;
  try {
    await auth.changePassword(passwordForm.oldPassword, passwordForm.newPassword);
    ElMessage.success("密码修改成功，请重新登录");
    passwordForm.oldPassword = "";
    passwordForm.newPassword = "";
    passwordForm.confirmPassword = "";
    await auth.logout();
  } catch {
    // auth store 已处理错误提示
  } finally {
    changingPassword.value = false;
  }
}

/** Debug：真实失败通知测试 */
async function runTestFail(): Promise<void> {
  testingFail.value = true;
  failTestResult.value = null;
  try {
    const res = await testFailureNotification();
    failTestResult.value = res;
    if (res.sent) {
      ElMessage.success("已发送测试推送，请查看手机 Server酱 绑定端");
    } else if (!res.server_chan_key_configured) {
      ElMessage.warning("未检测到 Server酱 Key：请先填写 Key 并保存通知设置");
    } else if (!res.notify_on_failure) {
      ElMessage.warning("「任务失败时推送」开关未打开");
    } else {
      ElMessage.warning("未发送：请查看下方提示信息");
    }
  } catch (e) {
    const msg = (e as { message?: string })?.message || "";
    ElMessage.error(`测试失败：${msg || "请查看后端日志"}`);
  } finally {
    testingFail.value = false;
  }
}
</script>

<template>
  <div class="system-settings">
    <h2 class="page-title">系统设置</h2>

    <div class="settings-grid">
      <!-- 通知设置 -->
      <KyiCard title="通知设置" icon="🔔" color="var(--kyi-primary)">
        <el-form label-position="top">
          <el-form-item label="Server 酱 Key">
            <el-input
              v-model="notifyForm.server_chan_key"
              placeholder="SCTxxxxxx（到 sct.ftqq.com 获取）"
              clearable
            />
          </el-form-item>
          <el-form-item label="Bark Key">
            <el-input placeholder="功能开发中~" disabled />
          </el-form-item>
          <el-form-item label="推送时机">
            <div class="checkbox-list">
              <el-checkbox v-model="notifyForm.notify_on_failure">任务失败时推送（推荐开启）</el-checkbox>
              <el-checkbox v-model="notifyForm.notify_on_success">任务成功时推送</el-checkbox>
              <el-checkbox v-model="notifyForm.notify_daily_summary">每日完成后推送汇总</el-checkbox>
              <el-checkbox v-model="notifyForm.notify_cookie_warning">Cookie 过期预警</el-checkbox>
              <el-checkbox v-model="notifyForm.notify_risk_alert">风控 / 连续失败告警（推荐开启）</el-checkbox>
            </div>
          </el-form-item>
          <el-divider content-position="left">免打扰</el-divider>
          <el-form-item label="开启免打扰">
            <el-switch v-model="notifyForm.dnd_enabled" />
          </el-form-item>
          <el-form-item label="免打扰时段">
            <div class="time-range">
              <el-time-picker
                v-model="notifyForm.dnd_start"
                format="HH:mm"
                value-format="HH:mm"
                placeholder="开始"
                :disabled="!notifyForm.dnd_enabled"
                size="default"
              />
              <span class="time-tilde">~</span>
              <el-time-picker
                v-model="notifyForm.dnd_end"
                format="HH:mm"
                value-format="HH:mm"
                placeholder="结束"
                :disabled="!notifyForm.dnd_enabled"
                size="default"
              />
            </div>
          </el-form-item>
          <el-form-item>
            <div class="form-tip">免打扰时段内的普通通知将被跳过不发送，紧急告警（Cookie 过期、风控）不受限制照常推送。</div>
          </el-form-item>
          <el-form-item>
            <el-button type="primary" :loading="savingNotify" @click="saveNotify">保存通知设置</el-button>
          </el-form-item>
        </el-form>
      </KyiCard>

      <!-- 风控设置 -->
      <KyiCard title="风控设置" icon="🛡️" color="var(--kyi-warning)">
        <el-form label-position="top">
          <el-form-item label="请求间隔（秒）">
            <div class="range-row">
              <el-input-number v-model="riskForm.delay_min" :min="0" :step="1" />
              <span class="range-tilde">~</span>
              <el-input-number v-model="riskForm.delay_max" :min="0" :step="1" />
            </div>
          </el-form-item>
          <el-form-item label="最大重试次数">
            <el-input-number v-model="riskForm.max_retries" :min="0" :max="10" />
          </el-form-item>
          <el-form-item label="连续失败暂停">
            <div class="range-row">
              <el-input-number v-model="riskForm.failure_threshold" :min="1" :max="20" />
              <span class="form-tip">次后自动暂停该任务</span>
            </div>
          </el-form-item>
          <el-form-item>
            <el-button type="primary" :loading="savingRisk" @click="saveRisk">保存风控设置</el-button>
          </el-form-item>
        </el-form>
      </KyiCard>

      <!-- 外观设置 -->
      <KyiCard title="外观设置" icon="🎨" color="var(--kyi-secondary)">
        <el-form label-position="top">
          <el-form-item label="主题（即时生效，无需保存）">
            <el-radio-group v-model="theme.theme">
              <el-radio-button label="22">22 · 粉</el-radio-button>
              <el-radio-button label="33">33 · 蓝</el-radio-button>
            </el-radio-group>
          </el-form-item>
          <el-form-item>
            <div class="form-tip">主题 22 代表粉色（22 号），主题 33 代表蓝色（33 号），即时生效无需手动保存。</div>
          </el-form-item>
        </el-form>
      </KyiCard>

      <!-- 安全设置 -->
      <KyiCard title="安全设置" icon="🔒" color="var(--kyi-danger)">
        <el-form label-position="top">
          <el-form-item label="旧密码">
            <el-input v-model="passwordForm.oldPassword" type="password" show-password />
          </el-form-item>
          <el-form-item label="新密码">
            <el-input v-model="passwordForm.newPassword" type="password" show-password />
          </el-form-item>
          <el-form-item label="确认新密码">
            <el-input v-model="passwordForm.confirmPassword" type="password" show-password />
          </el-form-item>
          <el-form-item>
            <el-button type="primary" :loading="changingPassword" @click="changePassword">
              修改密码
            </el-button>
          </el-form-item>
        </el-form>
      </KyiCard>

      <!-- 版本与升级（0.2.0） -->
      <KyiCard title="版本与升级" icon="🚀" color="#23ADE5" class="debug-card version-card">
        <div class="version-banner">
          <div class="version-banner__mascots">
            <img src="/mascots/down/1.png" alt="22 & 33" class="version-banner__mascot-img" />
          </div>
          <div class="version-banner__text">
            <div class="version-banner__ver">v{{ currentVersion || "?" }}</div>
            <div class="version-banner__sub">22 &amp; 33 持续守护中</div>
          </div>
        </div>

        <div class="debug-section">
          <div class="debug-head">
            <div>
              <div class="debug-title">检查 GitHub 上的新版本</div>
              <div class="form-tip">
                仓库 breezets/Dailykyi。检查失败时（如网络不通）会静默降级，不影响使用。
              </div>
            </div>
            <el-button
              type="primary"
              plain
              :loading="checkingUpgrade"
              @click="onCheckUpgrade"
            >
              {{ checkingUpgrade ? "检查中..." : "检查更新" }}
            </el-button>
          </div>

          <div v-if="upgradeResult" class="debug-result">
            <div class="debug-result-row">
              <span>当前版本：</span>
              <span class="ver-current">v{{ upgradeResult.current }}</span>
            </div>
            <div class="debug-result-row">
              <span>最新版本：</span>
              <span v-if="upgradeResult.latest" class="ver-latest">v{{ upgradeResult.latest }}</span>
              <span v-else>—</span>
            </div>
            <div v-if="upgradeResult.error" class="debug-result-log">
              {{ upgradeResult.error }}
            </div>
            <template v-else-if="upgradeResult.has_update">
              <div class="debug-result-log version-notes">
                <div class="version-notes__title">本次更新内容</div>
                <div class="version-notes__body">{{ upgradeResult.notes || "（无更新说明）" }}</div>
              </div>
              <div class="upgrade-actions">
                <el-button
                  class="upgrade-btn"
                  :loading="upgrading"
                  @click="onRunUpgrade"
                >
                  {{ upgrading ? "升级中..." : "一键升级到最新版本" }}
                </el-button>
                <a
                  v-if="upgradeResult.release_url"
                  :href="upgradeResult.release_url"
                  target="_blank"
                  rel="noopener noreferrer"
                  class="upgrade-link"
                >在 GitHub 查看发布页 →</a>
              </div>
            </template>
            <div v-else class="debug-result-log version-uptodate">
              <span class="uptodate-icon">✨</span> 当前已是最新版本，22 &amp; 33 都放心啦
            </div>
          </div>
        </div>
      </KyiCard>

      <!-- 调试与诊断（Debug） -->
      <KyiCard title="调试与诊断" icon="🧪" color="#8C52FF" class="debug-card">
        <div class="debug-section">
          <div class="debug-head">
            <div>
              <div class="debug-title">失败通知真实测试</div>
              <div class="form-tip">
                会走完整 NotifyService.send_task_result(success=false) 链路，
                与真实任务失败时完全相同。用来验证 Server酱 Key、开关、免打扰时段。
              </div>
            </div>
            <el-button type="danger" plain :loading="testingFail" @click="runTestFail">
              {{ testingFail ? '测试中...' : '发送一次失败通知测试' }}
            </el-button>
          </div>
          <div v-if="failTestResult" class="debug-result">
            <div class="debug-result-row">
              <span>Server酱 Key 已配置：</span>
              <span :class="failTestResult.server_chan_key_configured ? 'ok' : 'bad'">{{ failTestResult.server_chan_key_configured ? '是' : '否' }}</span>
            </div>
            <div class="debug-result-row">
              <span>任务失败推送开关：</span>
              <span :class="failTestResult.notify_on_failure ? 'ok' : 'bad'">{{ failTestResult.notify_on_failure ? '开启' : '关闭' }}</span>
            </div>
            <div class="debug-result-row">
              <span>是否实际发起了推送：</span>
              <span :class="failTestResult.sent ? 'ok' : 'bad'">{{ failTestResult.sent ? '是，请查看手机' : '否' }}</span>
            </div>
            <div class="debug-result-row debug-account">
              <span>模拟账号：</span>
              <span>{{ failTestResult.account.username }} (UID {{ failTestResult.account.uid }}){{ failTestResult.account.used_real ? '' : ' · 演示账号' }}</span>
            </div>
            <div class="debug-result-log" v-if="failTestResult.log">{{ failTestResult.log }}</div>
          </div>
        </div>
      </KyiCard>
    </div>
  </div>
</template>

<style scoped>
.system-settings {
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.page-title {
  margin: 0;
  font-size: 20px;
  color: var(--kyi-text);
}

.settings-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(420px, 1fr));
  gap: 20px;
}

/* Debug card 占两列 */
.debug-card {
  grid-column: 1 / -1;
}

/* 版本与升级卡片：2233 主题美化 */
.version-card {
  background: linear-gradient(180deg, rgba(251, 114, 153, 0.04), rgba(35, 173, 229, 0.04));
}

.version-banner {
  display: flex;
  align-items: center;
  gap: 18px;
  padding: 20px 22px;
  border-radius: 14px;
  background: linear-gradient(135deg, rgba(251, 114, 153, 0.12), rgba(35, 173, 229, 0.12));
  border: 1px solid rgba(251, 114, 153, 0.18);
  margin-bottom: 18px;
}

.version-banner__mascots {
  display: flex;
  gap: 6px;
  flex-shrink: 0;
}

.version-banner__mascot-img {
  width: 64px;
  height: 64px;
  object-fit: cover;
  border-radius: 12px;
  box-shadow: 0 4px 12px rgba(251, 114, 153, 0.25), 0 2px 6px rgba(35, 173, 229, 0.18);
}

.version-banner__text {
  flex: 1;
  min-width: 0;
}

.version-banner__ver {
  font-size: 22px;
  font-weight: 700;
  background: linear-gradient(90deg, #FB7299, #23ADE5);
  -webkit-background-clip: text;
  background-clip: text;
  color: transparent;
  line-height: 1.2;
}

.version-banner__sub {
  margin-top: 4px;
  font-size: 12px;
  color: var(--kyi-text-secondary);
}

.ver-current {
  color: var(--kyi-text);
  font-weight: 600;
}

.ver-latest {
  color: var(--kyi-secondary);
  font-weight: 700;
}

.version-notes {
  background: linear-gradient(135deg, rgba(251, 114, 153, 0.06), rgba(35, 173, 229, 0.06));
  border: 1px solid rgba(251, 114, 153, 0.15);
}

.version-notes__title {
  font-weight: 600;
  margin-bottom: 6px;
  color: var(--kyi-text);
  font-size: 13px;
}

.version-notes__body {
  white-space: pre-wrap;
  font-size: 13px;
  color: var(--kyi-text-secondary);
  line-height: 1.6;
}

.upgrade-btn {
  background: linear-gradient(135deg, #FB7299, #23ADE5) !important;
  border: none !important;
  color: #fff !important;
  font-weight: 600;
  box-shadow: 0 4px 14px rgba(251, 114, 153, 0.25);
}

.upgrade-btn:hover {
  opacity: 0.92;
  box-shadow: 0 6px 18px rgba(35, 173, 229, 0.35);
}

.version-uptodate {
  text-align: center;
  color: var(--kyi-success);
  font-weight: 600;
  padding: 12px;
}

.uptodate-icon {
  margin-right: 4px;
}

.checkbox-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.time-range {
  display: flex;
  align-items: center;
  gap: 12px;
  flex-wrap: wrap;
}
.time-range .el-time-picker,
.time-range :deep(.el-time-picker) {
  width: 150px;
  min-width: 130px;
}
.time-tilde {
  color: var(--kyi-text-secondary);
  font-size: 13px;
}

.range-row {
  display: flex;
  align-items: center;
  gap: 12px;
  flex-wrap: wrap;
}
.range-tilde {
  color: var(--kyi-text-secondary);
}

.form-tip {
  font-size: 12px;
  color: var(--kyi-text-secondary);
  line-height: 1.6;
}

/* Debug 板块 */
.debug-section {
  display: flex;
  flex-direction: column;
  gap: 16px;
}
.debug-head {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 16px;
}
.debug-title {
  font-size: 14px;
  font-weight: 600;
  color: var(--kyi-text);
  margin-bottom: 4px;
}
.debug-result {
  background: var(--kyi-bg-soft, #f7f9fc);
  border: 1px solid var(--kyi-border, #ebeef5);
  border-radius: 10px;
  padding: 14px 16px;
  display: flex;
  flex-direction: column;
  gap: 8px;
}
.debug-result-row {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 13px;
  color: var(--kyi-text);
}
.debug-result-row span:first-child {
  color: var(--kyi-text-secondary);
  min-width: 150px;
}
.debug-result-row .ok {
  color: #27ae60;
  font-weight: 600;
}
.debug-result-row .bad {
  color: #e74c3c;
  font-weight: 600;
}
.debug-result-log {
  margin-top: 4px;
  padding: 10px 12px;
  background: var(--kyi-bg, #fff);
  border-radius: 8px;
  border-left: 3px solid var(--kyi-primary);
  font-size: 12.5px;
  color: var(--kyi-text);
  line-height: 1.7;
}

.upgrade-actions {
  display: flex;
  align-items: center;
  gap: 16px;
  margin-top: 4px;
  flex-wrap: wrap;
}
.upgrade-link {
  font-size: 13px;
  color: var(--kyi-primary);
  text-decoration: none;
}
.upgrade-link:hover {
  text-decoration: underline;
}

/* ============ 响应式：平板 ============ */
@media (max-width: 900px) {
  .settings-grid {
    grid-template-columns: 1fr;
  }
  .debug-head {
    flex-direction: column;
  }
}

/* ============ 响应式：手机端 ============ */
@media (max-width: 600px) {
  .system-settings {
    gap: 14px;
  }
  .page-title {
    font-size: 17px;
  }
  .time-range {
    flex-direction: column;
    align-items: stretch;
  }
  .time-range .el-time-picker,
  .time-range :deep(.el-time-picker) {
    width: 100%;
  }
  .time-tilde {
    align-self: center;
  }
  .range-row {
    flex-direction: column;
    align-items: stretch;
  }
  .range-row .el-input-number,
  .range-row :deep(.el-input-number) {
    width: 100%;
  }
  .debug-result-row {
    flex-direction: column;
    align-items: flex-start;
    gap: 2px;
  }
  .debug-result-row span:first-child {
    min-width: unset;
  }
}
</style>
