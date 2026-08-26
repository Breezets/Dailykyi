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
  exp: number;
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
    return {
      id: log.id,
      time: formatDate(log.created_at, "HH:mm:ss"),
      title: `${log.account_name || log.account_uid} · ${log.task_type}`,
      status: log.status,
      statusIcon: mapped.icon,
      statusColor: mapped.color,
      message: log.message || "",
      exp: log.exp_gained || 0,
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
        <div v-if="item.exp > 0" class="timeline-item__exp">+{{ item.exp }} 经验</div>
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
  font-size: 12px;
  color: var(--kyi-primary);
}
</style>
