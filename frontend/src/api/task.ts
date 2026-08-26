/** 任务配置 API */

import request from "./request";
import type { TaskConfig } from "@/types";

export async function getTaskConfigs(uid: number): Promise<TaskConfig[]> {
  const res = await request.get<unknown, TaskConfig[]>(`/tasks/${uid}`);
  return Array.isArray(res) ? res : [];
}

export async function updateTaskConfig(
  uid: number,
  taskType: string,
  data: {
    config: Record<string, unknown>;
    schedule_config: Record<string, unknown>;
    enabled: boolean;
    schedule_mode?: string;
  }
): Promise<TaskConfig> {
  return request.put<unknown, TaskConfig>(`/tasks/${uid}/${taskType}`, data);
}

export async function triggerTask(
  uid: number,
  taskType: string
): Promise<{ task_log_id: number; status: string }> {
  return request.post<unknown, { task_log_id: number; status: string }>(
    `/tasks/${uid}/${taskType}/trigger`
  );
}

export async function previewTask(
  uid: number,
  taskType: string
): Promise<{ would_execute?: unknown[]; [key: string]: unknown }> {
  return request.get<unknown, { would_execute?: unknown[]; [key: string]: unknown }>(
    `/tasks/${uid}/${taskType}/preview`
  );
}
