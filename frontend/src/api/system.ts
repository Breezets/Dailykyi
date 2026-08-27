import request from "./request";

export interface TestFailureResult {
  sent: boolean;
  server_chan_key_configured: boolean;
  notify_on_failure: boolean;
  log: string;
  account: { uid: number; username: string | null; used_real: boolean };
}

export async function getSystemConfig(): Promise<Record<string, unknown>> {
  return request.get<unknown, Record<string, unknown>>("/system/config");
}

export async function updateSystemConfig(config: Record<string, unknown>): Promise<{ status: string }> {
  return request.put<unknown, { status: string }>("/system/config", config);
}

/** 真实失败通知测试（走完整 send_task_result(success=false) 链路） */
export async function testFailureNotification(): Promise<TestFailureResult> {
  return request.post<unknown, TestFailureResult>("/system/notify/test-failure");
}

// ====== 版本升级（0.2.0） ======

export interface UpgradeCheckResult {
  has_update: boolean;
  current: string;
  latest: string | null;
  release_url: string | null;
  notes: string | null;
  error: string | null;
  /** 客户端缓存时间戳（非后端返回） */
  __ts?: number;
}

export interface UpgradeExecuteResult {
  started: boolean;
  log_file?: string;
  message?: string;
  error?: string;
}

/** 检查 GitHub 是否有新版本 */
export async function checkUpgrade(): Promise<UpgradeCheckResult> {
  return request.get<unknown, UpgradeCheckResult>("/system/upgrade/check");
}

/** 一键升级（后台执行 update.sh） */
export async function runUpgrade(): Promise<UpgradeExecuteResult> {
  return request.post<unknown, UpgradeExecuteResult>("/system/upgrade/execute");
}
