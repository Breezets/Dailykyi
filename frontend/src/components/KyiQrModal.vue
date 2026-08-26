<script setup lang="ts">
import { ref, reactive, watch, onUnmounted } from "vue";
import { ElMessage } from "element-plus";
import QRCode from "qrcode";
import { getQrCode, getQrStatus, cookieLogin } from "@/api/auth";

const props = defineProps<{
  modelValue: boolean;
}>();

const emit = defineEmits<{
  (e: "update:modelValue", value: boolean): void;
  (e: "confirmed", uid?: number): void;
}>();

const visible = ref(props.modelValue);
const activeTab = ref("qr");
const qrDataUrl = ref("");
const qrcodeKey = ref("");
const statusText = ref("正在获取二维码...");

const cookieForm = reactive({
  SESSDATA: "",
  bili_jct: "",
  DedeUserID: "",
  buvid3: "",
  b_nutts: "",
  extra: "",
});
const cookieLoading = ref(false);
let timer: ReturnType<typeof setInterval> | null = null;

watch(
  () => props.modelValue,
  async (next) => {
    visible.value = next;
    if (next) {
      await startQrFlow();
    } else {
      clearTimer();
    }
  }
);

watch(visible, (next) => {
  emit("update:modelValue", next);
});

async function startQrFlow(): Promise<void> {
  clearTimer();
  qrDataUrl.value = "";
  qrcodeKey.value = "";
  statusText.value = "正在获取二维码...";
  try {
    const data = await getQrCode();
    qrcodeKey.value = data.qrcode_key;
    qrDataUrl.value = await QRCode.toDataURL(data.qrcode_url, {
      width: 200,
      margin: 2,
    });
    statusText.value = "等待扫码";
    timer = setInterval(pollStatus, 3000);
  } catch {
    statusText.value = "二维码获取失败";
  }
}

async function pollStatus(): Promise<void> {
  if (!qrcodeKey.value) return;
  try {
    const data = await getQrStatus(qrcodeKey.value);
    if (data.status === "waiting") {
      statusText.value = "等待扫码";
    } else if (data.status === "scanned") {
      statusText.value = "已扫码，确认中";
    } else if (data.status === "confirmed") {
      statusText.value = "登录成功！";
      ElMessage.success("扫码登录成功");
      clearTimer();
      visible.value = false;
      emit("confirmed", data.uid);
    } else if (data.status === "expired") {
      statusText.value = "二维码已过期，请重新获取";
      clearTimer();
    } else {
      statusText.value = data.message || "未知状态";
    }
  } catch {
    statusText.value = "状态查询失败";
  }
}

function buildCookieString(): string {
  const parts: string[] = [];
  const required = ["SESSDATA", "bili_jct", "DedeUserID", "buvid3"];
  for (const key of required) {
    const val = (cookieForm as Record<string, string>)[key].trim();
    if (val) parts.push(`${key}=${val}`);
  }
  if (cookieForm.b_nutts.trim()) parts.push(`b_nutts=${cookieForm.b_nutts.trim()}`);
  if (cookieForm.extra.trim()) {
    // 允许用户粘贴额外的 key=value 对
    parts.push(cookieForm.extra.trim());
  }
  return parts.join("; ");
}

async function submitCookieLogin(): Promise<void> {
  if (!cookieForm.SESSDATA.trim()) {
    ElMessage.warning("请填写 SESSDATA");
    return;
  }
  if (!cookieForm.bili_jct.trim()) {
    ElMessage.warning("请填写 bili_jct");
    return;
  }
  if (!cookieForm.DedeUserID.trim()) {
    ElMessage.warning("请填写 DedeUserID");
    return;
  }
  if (!cookieForm.buvid3.trim()) {
    ElMessage.warning("请填写 buvid3");
    return;
  }
  const cookie = buildCookieString();
  cookieLoading.value = true;
  try {
    const data = await cookieLogin(cookie);
    ElMessage.success("Cookie 登录成功");
    for (const k of Object.keys(cookieForm)) {
      (cookieForm as Record<string, string>)[k] = "";
    }
    visible.value = false;
    emit("confirmed", data.uid);
  } catch (err: unknown) {
    const msg = (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail || "Cookie 登录失败";
    ElMessage.error(msg);
  } finally {
    cookieLoading.value = false;
  }
}

function clearTimer(): void {
  if (timer) {
    clearInterval(timer);
    timer = null;
  }
}

onUnmounted(clearTimer);
</script>

<template>
  <el-dialog
    v-model="visible"
    title="添加账号"
    width="460px"
    align-center
    @closed="clearTimer"
  >
    <el-tabs v-model="activeTab" class="login-tabs">
      <el-tab-pane label="扫码登录" name="qr">
        <div class="qr-modal">
          <div class="qr-wrap">
            <img
              v-if="qrDataUrl"
              :src="qrDataUrl"
              alt="B站扫码登录"
              class="qr-image"
            />
            <div v-else class="qr-placeholder">加载中...</div>
          </div>
          <p class="qr-tip">请用 B 站 APP 扫码登录</p>
          <p class="qr-status" :class="{ 'qr-status--active': statusText !== '等待扫码' }">
            {{ statusText }}
          </p>
        </div>
      </el-tab-pane>

      <el-tab-pane label="Cookie 登录" name="cookie">
        <div class="cookie-modal">
          <el-form label-position="top" label-width="120px">
            <el-row :gutter="12">
              <el-col :span="12">
                <el-form-item label="SESSDATA <span style='color:var(--kyi-danger)'>*</span>">
                  <el-input
                    v-model="cookieForm.SESSDATA"
                    type="textarea"
                    :rows="2"
                    placeholder="在 Cookies 中找到 SESSDATA，复制 Value 粘贴"
                  />
                </el-form-item>
              </el-col>
              <el-col :span="12">
                <el-form-item label="bili_jct <span style='color:var(--kyi-danger)'>*</span>">
                  <el-input
                    v-model="cookieForm.bili_jct"
                    placeholder="找到 bili_jct，复制 Value 粘贴"
                  />
                </el-form-item>
              </el-col>
            </el-row>
            <el-row :gutter="12">
              <el-col :span="12">
                <el-form-item label="DedeUserID <span style='color:var(--kyi-danger)'>*</span>">
                  <el-input
                    v-model="cookieForm.DedeUserID"
                    placeholder="找到 DedeUserID，复制 Value 粘贴"
                  />
                </el-form-item>
              </el-col>
              <el-col :span="12">
                <el-form-item label="buvid3 <span style='color:var(--kyi-danger)'>*</span>">
                  <el-input
                    v-model="cookieForm.buvid3"
                    placeholder="找到 buvid3，复制 Value 粘贴"
                  />
                </el-form-item>
              </el-col>
            </el-row>
            <el-row :gutter="12">
              <el-col :span="12">
                <el-form-item label="b_nutts（推荐）">
                  <el-input
                    v-model="cookieForm.b_nutts"
                    placeholder="可选，建议填写"
                  />
                </el-form-item>
              </el-col>
              <el-col :span="12">
                <el-form-item label="其他 Cookie（可选）">
                  <el-input
                    v-model="cookieForm.extra"
                    placeholder="key1=val1; key2=val2 格式"
                  />
                </el-form-item>
              </el-col>
            </el-row>
          </el-form>

          <el-divider content-position="left">获取方法</el-divider>
          <div class="cookie-tip">
            <p>1. 浏览器打开 <a href="https://www.bilibili.com" target="_blank">bilibili.com</a> 并登录账号</p>
            <p>2. 按 <kbd>F12</kbd> → 顶部 <kbd>Application</kbd> → 左侧展开 <kbd>Cookies</kbd> → 点 <kbd>www.bilibili.com</kbd></p>
            <p>3. 在右侧表格中，按上面表单列出的名称依次找到 <b>Name</b>，双击对应的 <b>Value</b> 单元格复制，粘贴到上面对应输入框</p>
            <p class="cookie-tip-warn">Cookie 登录绕过风控，投币更稳定。所有 Cookie 仅保存在本地，加密存储</p>
          </div>

          <el-button
            type="primary"
            :loading="cookieLoading"
            @click="submitCookieLogin"
            class="cookie-btn"
          >
            登录
          </el-button>
        </div>
      </el-tab-pane>
    </el-tabs>
  </el-dialog>
</template>

<style scoped>
.login-tabs {
  --el-tabs-header-height: 40px;
}

.qr-modal {
  display: flex;
  flex-direction: column;
  align-items: center;
  padding: 12px 0;
}

.qr-wrap {
  width: 200px;
  height: 200px;
  border-radius: 12px;
  overflow: hidden;
  background: #f5f7fa;
  display: flex;
  align-items: center;
  justify-content: center;
}

.qr-image {
  width: 100%;
  height: 100%;
  object-fit: contain;
}

.qr-placeholder {
  color: var(--kyi-text-secondary);
}

.qr-tip {
  margin-top: 16px;
  font-size: 14px;
  color: var(--kyi-text);
}

.qr-status {
  margin-top: 8px;
  font-size: 13px;
  color: var(--kyi-text-secondary);
}

.qr-status--active {
  color: var(--kyi-primary);
}

.cookie-modal {
  padding: 8px 0;
}

.cookie-modal :deep(kbd) {
  display: inline-block;
  padding: 1px 6px;
  font-size: 11px;
  font-family: inherit;
  background: #f0f2f5;
  border: 1px solid #dcdfe6;
  border-bottom-width: 2px;
  border-radius: 4px;
  color: #606266;
}

.cookie-modal :deep(.el-form-item__label) {
  font-size: 13px;
}

.cookie-modal :deep(.el-col) {
  margin-bottom: -8px;
}

.cookie-tip {
  font-size: 12px;
  color: var(--kyi-text-secondary);
  line-height: 1.8;
  margin: 4px 0 12px;
}

.cookie-tip a {
  color: var(--kyi-primary);
}

.cookie-tip-warn {
  color: var(--kyi-warning);
  margin-top: 4px;
}

.cookie-btn {
  width: 100%;
}
</style>
