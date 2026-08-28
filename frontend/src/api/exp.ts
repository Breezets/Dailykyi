/** 经验日志（ExpSnapshot 独立日志）API：对应后端 /api/v1/exp */

import request from "./request";

export interface ExpSnapshotItem {
  id: number;
  account_uid: number;
  account_name: string | null;
  exp: number;
  level: number;
  coins: number;
  /** task / passive / manual */
  source: string;
  source_label: string;
  /** Dailykyi / 站外 */
  origin: string;
  origin_label: string;
  recorded_at: string;
  /** 与上一条快照对比，净增减 */
  delta: number;
  /** 上一条快照经验值，用于 UI 展示 */
  prev_exp: number;
}

export interface ExpSnapshotListResponse {
  items: ExpSnapshotItem[];
  total: number;
}

export interface DailySourceBucket {
  date: string;
  total_gain: number;
  task: number;
  passive: number;
  manual: number;
  end_exp: number;
  start_exp: number;
}

export interface ExpSummaryResponse {
  last_7_days: DailySourceBucket[];
  accounts_covered: number[];
}

export interface ListExpParams {
  account_uid?: number;
  /** 多个英文逗号分隔：task,passive,manual */
  source?: string;
  date?: string;
  from_date?: string;
  to_date?: string;
  limit?: number;
  offset?: number;
}

export async function listExpSnapshots(params: ListExpParams = {}): Promise<ExpSnapshotListResponse> {
  const q: Record<string, any> = {};
  (Object.keys(params) as (keyof ListExpParams)[]).forEach((k) => {
    const v = params[k];
    if (v !== undefined && v !== null && v !== "") q[k] = v;
  });
  return request.get<unknown, ExpSnapshotListResponse>("/exp/snapshots", { params: q });
}

export async function getExpSummary(days = 7): Promise<ExpSummaryResponse> {
  return request.get<unknown, ExpSummaryResponse>("/exp/snapshots/summary", { params: { days } });
}
