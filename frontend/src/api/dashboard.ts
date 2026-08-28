/** 仪表盘 API */

import request from "./request";

export interface Lv6Estimate {
  lv6_threshold: number;
  current_level: number;
  current_exp: number;
  exp_remaining: number;
  avg_daily_exp: number;
  est_days_to_lv6: number | null;
  est_date: string | null;
  already_reached: boolean;
}

/** 0.2.1 新增：今日经验拆分（总/平台/其他设备） */
export interface TodayExpSplit {
  total: number;          // 今日总经验
  platform: number;       // 平台通过执行任务获得
  other: number;          // 其他设备 / 其他方式获得
  baseline_exp: number;   // 计算起点（24h 前快照 exp）
  current_exp: number;    // 当前经验
  has_baseline_snapshot: boolean; // 是否有 24h 基线快照
}

export interface DashboardAccount {
  uid: number;
  username: string | null;
  avatar_url: string | null;
  level: number;
  current_exp: number;
  next_level_exp: number;
  coins: number;
  today_exp_gained: number;
  today_exp_split: TodayExpSplit | null;
  lv6_estimate: Lv6Estimate | null;
}

export interface DashboardStats {
  total_tasks: number;
  success_count: number;
  failed_count: number;
  skipped_count: number;
}

export interface DashboardLog {
  id: number;
  account_uid: number;
  account_name: string | null;
  task_type: string;
  status: string;
  message: string | null;
  exp_gained: number;
  created_at: string;
}

export interface DashboardUpcoming {
  job_id: string;
  account_uid: number;
  task_type: string;
  next_run_time: string | null;
}

export interface DashboardResponse {
  accounts: DashboardAccount[];
  today_stats: DashboardStats;
  recent_logs: DashboardLog[];
  upcoming: DashboardUpcoming[];
}

export async function getDashboard(): Promise<DashboardResponse> {
  return request.get<unknown, DashboardResponse>("/dashboard");
}
