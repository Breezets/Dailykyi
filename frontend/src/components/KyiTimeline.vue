<script setup lang="ts">
import { computed } from "vue";
import { Check, Close, Loading, QuestionFilled } from "@element-plus/icons-vue";
import { formatDate } from "@/utils/date";
import type { TaskLog } from "@/types";

const props = defineProps<{
  logs: TaskLog[];
}>();

interface DisplayItem {
  id: number;
  time: string;
  title: string;
  status: TaskLog["status"];
  statusIcon: typeof Check;
  statusColor: string;
  message: string;
  exp_gained: number;
  exp_after: number | null;   // 0.2.1：任务完成后当前经验
  exp_text: string;          // 0.2.1：直接显示的文字：「获得 50，当前 12345」
}

const items = computed<DisplayItem[]>(() =>
  props.logs.map((log) => {
    const statusMap: Record<
      TaskLog["status"],
      { icon: typeof Check; color: string }
    > = {
      success: { icon: Check, color: "var(--kyi-success)" },
      failed: { icon: Close, color: "var(--kyi-danger)" },
      skipped: { icon: QuestionFilled, color: "var(--kyi-warning)" },
      running: { icon: Loading, color: "var(--kyi-secondary)" },
      pending: { icon: Loading, color: "var(--kyi-text-secondary)" },
    };
    const mapped = statusMap[log.status] || statusMap.pending;

    // 0.2.1：从 detail / after_exp 解析当前经验
    const gained = Number(log.exp_gained || 0);
    const rawDetail = (log as any)?.detail as any;
    let detailObj: any = null;
    if (rawDetail != null && rawDetail !== "") {
      if (typeof rawDetail === "object") {
        detailObj = rawDetail;
      } else if (typeof rawDetail === "string") {
        try {
          detailObj = JSON.parse(rawDetail);
        } catch {
          // ignore
        }
      }
    }
    const after = detailObj?.after_exp != null ? Number(detailObj.after_exp) : null;
    let expText = "";
    if (gained > 0 && after != null && !Number.isNaN(after) && after > 0) {
      expText = `获得 ${gained}，当前 ${after}`;
    } else if (gained > 0) {
      expText = `+${gained} 经验`;
    }

    // 标题 task_type 改成中文友好名
    const taskTypeMap: Record<string, string> = {
      coin: "投币",
      watch: "观看",
      share: "分享",
      live_sign: "直播签到",
      silver2coin: "银瓜子换币",
    };
    const taskName = taskTypeMap[log.task_type] || log.task_type;

    return {
      id: log.id,
      time: formatDate(log.created_at, "HH:mm:ss"),
      title: `${log.account_name || log.account_uid} · ${taskName}`,
      status: log.status,
      statusIcon: mapped.icon,
      statusColor: mapped.color,
      message: log.message || "",
      exp_gained: gained,
      exp_after: after,
      exp_text: expText,
    };
  })
);
</script>

<template>
  <el-timeline>
    <el-timeline-item
      v-for="item in items"
      :key="item.id"
      :type="item.status === 'success' ? 'success' : item.status === 'failed' ? 'danger' : 'primary'"
      :hollow="item.status !== 'success'"
      :timestamp="item.time"
    >
      <div class="timeline-item">
        <div class="timeline-item__title">
          <span>{{ item.title }}</span>
          <el-tag size="small" :color="item.statusColor" effect="dark" round>
            <el-icon class="status-icon"><component :is="item.statusIcon" /></el-icon>
            {{ item.status }}
          </el-tag>
        </div>
        <div class="timeline-item__message">{{ item.message }}</div>
        <!-- 0.2.1：升级为「获得 X，当前 Y」格式，兼容老日志只有 +X -->
        <div v-if="item.exp_text" class="timeline-item__exp">{{ item.exp_text }}</div>
      </div>
    </el-timeline-item>
  </el-timeline>
</template>

<style scoped>
.timeline-item {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.timeline-item__title {
  display: flex;
  align-items: center;
  justify-content: space-between;
  font-weight: 600;
  color: var(--kyi-text);
}

.status-icon {
  margin-right: 4px;
  vertical-align: middle;
}

.timeline-item__message {
  font-size: 13px;
  color: var(--kyi-text-secondary);
  word-break: break-all;
}

.timeline-item__exp {
  font-size: 13px;
  color: var(--kyi-primary);
  font-weight: 600;
  padding: 2px 8px;
  background: rgba(35, 173, 229, 0.08);
  border-radius: 4px;
  display: inline-block;
  width: fit-content;
}
</style>
