/** 日志 API（对应后端 /api/v1/logs，若后端未实现需补充路由） */

import request from "./request";
import type { TaskLog } from "@/types";

export interface LogFilterParams {
  account_uid?: number;
  task_type?: string;
  status?: string;
  date?: string;
  limit?: number;
  offset?: number;
}

export async function getLogs(
  params: LogFilterParams = {}
): Promise<{ total: number; logs: TaskLog[] }> {
  const res = await request.get<unknown, { total: number; logs: TaskLog[] }>("/logs", {
    params,
  });
  return res || { total: 0, logs: [] };
}

/** 按 ID 查询单条日志 — 用于立即测试轮询执行结果 */
export async function getLogById(logId: number): Promise<TaskLog> {
  return request.get<unknown, TaskLog>(`/logs/${logId}`);
}

export function getLogStream(): EventSource {
  return new EventSource("/api/v1/logs/stream", { withCredentials: true });
}
