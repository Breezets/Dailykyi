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
