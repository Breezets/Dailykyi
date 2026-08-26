/** Dailykyi 前端类型定义 */

export interface Account {
  uid: number;
  username: string;
  avatar_url?: string;
  level: number;
  current_exp: number;
  next_level_exp: number;
  coins: number;
  cookie_status?: string;
  is_active: boolean;
  today_exp_gained: number;
}

export interface TaskConfig {
  id: number;
  account_uid: number;
  task_type: string;
  enabled: boolean;
  config: Record<string, unknown>;
  schedule_mode: string;
  schedule_config: Record<string, unknown>;
  max_retries: number;
  cooldown_minutes: number;
  created_at: string;
  updated_at: string;
}

export interface TaskLog {
  id: number;
  account_uid: number;
  account_name: string;
  task_type: string;
  status: "pending" | "running" | "success" | "failed" | "skipped";
  message: string;
  detail: Record<string, unknown>;
  exp_gained: number;
  created_at: string;
}

export interface CoinTier {
  min_coins: number;
  daily_limit: number;
}

export interface CoinTaskConfig {
  enabled: boolean;
  mode: "fixed" | "smart";
  fixed_limit: number;
  smart_tiers: CoinTier[];
  reserve_coins: number;
  target_mode: "specified" | "recommend";
  target_uids: number[];
  fallback_to_recommend: boolean;
}

export interface ScheduleConfig {
  schedule_mode: "fixed" | "random";
  schedule_config: Record<string, unknown>;
}

export interface QrGenerateResponse {
  qrcode_key: string;
  qrcode_url: string;
}

export interface QrStatusResponse {
  status: "waiting" | "scanned" | "confirmed" | "expired" | "unknown";
  message?: string;
  uid?: number;
}
