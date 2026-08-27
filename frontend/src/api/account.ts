/** 账号管理 API（对应后端 /api/v1/accounts，若后端未实现需补充路由） */

import request from "./request";
import type { Account } from "@/types";

export async function getAccounts(): Promise<Account[]> {
  const res = await request.get<unknown, Account[]>("/accounts");
  return Array.isArray(res) ? res : [];
}

export async function getAccount(uid: number): Promise<Account> {
  return request.get<unknown, Account>(`/accounts/${uid}`);
}

export async function deleteAccount(uid: number): Promise<void> {
  await request.delete(`/accounts/${uid}`);
}

export async function refreshCookie(uid: number): Promise<void> {
  await request.post(`/accounts/${uid}/refresh`);
}

/** 立即检测所有账号 Cookie 有效性（0.2.0） */
export async function checkCookies(): Promise<{
  message: string;
  checked: number;
  ok: number;
  expired: number;
  warned_expiring: number;
}> {
  return request.post<unknown, {
    message: string;
    checked: number;
    ok: number;
    expired: number;
    warned_expiring: number;
  }>("/accounts/check-cookies");
}
