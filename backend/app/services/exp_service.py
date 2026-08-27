"""经验计算服务：基于 ExpSnapshot 快照对比计算每日增量，并提供 LV6 预估。

替代旧版"按 TaskLog.exp_gained 求和"算法：
  - 旧算法依赖任务上报数值（曾因 bug 误报 +5）
  - 旧算法对当日未执行任务段无法覆盖
  - 新算法用 accounts.current_exp 与 24h 前快照的差值，是 B 站服务端真实经验
"""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.account import Account
from app.models.exp_snapshot import ExpSnapshot
from app.models.task_log import TaskLog

# B 站 LV6 经验阈值（28800）= LV5 上限
LV6_EXP_THRESHOLD: int = 28800


async def compute_today_exp_gain(db: AsyncSession, acc: Account) -> int:
    """计算账号今日经验增量。

    优先算法（推荐）：取 24h 前 ±30 分钟容差范围内最近的一条 ExpSnapshot，
    差值 = max(0, current_exp - snapshot.exp)。

    Fallback：若无 24h 前的快照（首次启用或新装），降级为
    TaskLog.exp_gained 当日汇总。
    """
    now = datetime.now()
    # 24h 前 ±30 分钟容差窗口
    window_start = now - timedelta(hours=24, minutes=30)
    window_end = now - timedelta(hours=23, minutes=30)

    snap_result = await db.execute(
        select(ExpSnapshot)
        .where(
            ExpSnapshot.account_uid == acc.uid,
            ExpSnapshot.recorded_at >= window_start,
            ExpSnapshot.recorded_at <= window_end,
        )
        .order_by(ExpSnapshot.recorded_at.desc())
        .limit(1)
    )
    snap = snap_result.scalar_one_or_none()

    if snap is not None:
        diff = int(acc.current_exp or 0) - int(snap.exp or 0)
        return max(0, diff)

    # Fallback：当日 TaskLog 汇总
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    log_result = await db.execute(
        select(func.coalesce(func.sum(TaskLog.exp_gained), 0)).where(
            TaskLog.account_uid == acc.uid,
            TaskLog.created_at >= today_start,
        )
    )
    return int(log_result.scalar() or 0)


async def compute_lv6_estimate(
    db: AsyncSession, acc: Account, today_exp: int | None = None
) -> dict[str, Any]:
    """预估到达 LV6 所需时间。

    返回字段：
      - lv6_threshold: 28800
      - exp_remaining: 还需经验（max(0, 28800 - current_exp)）
      - avg_daily_exp: 近 7 天日均经验（取所有快照的最大-最小，避免单日抖动）
      - est_days_to_lv6: 预估天数（None 表示数据不足或已达标）
      - est_date: 预估达成日期（YYYY-MM-DD，None 表示数据不足或已达标）
      - already_reached: bool，是否已 LV6+
    """
    already_reached = int(acc.level or 0) >= 6 or int(acc.current_exp or 0) >= LV6_EXP_THRESHOLD
    exp_remaining = max(0, LV6_EXP_THRESHOLD - int(acc.current_exp or 0))

    # 取最近 7 天的快照算日均经验
    week_ago = datetime.now() - timedelta(days=7)
    snaps_result = await db.execute(
        select(ExpSnapshot)
        .where(
            ExpSnapshot.account_uid == acc.uid,
            ExpSnapshot.recorded_at >= week_ago,
        )
        .order_by(ExpSnapshot.recorded_at.asc())
    )
    snaps = list(snaps_result.scalars().all())

    avg_daily_exp: float = 0.0
    if len(snaps) >= 2:
        # 用最早和最新快照的差值，除以间隔天数
        earliest = snaps[0]
        latest = snaps[-1]
        delta_exp = max(0, int(latest.exp or 0) - int(earliest.exp or 0))
        delta_seconds = (latest.recorded_at - earliest.recorded_at).total_seconds()
        if delta_seconds > 0:
            days = delta_seconds / 86400.0
            avg_daily_exp = delta_exp / days if days > 0 else 0.0
    elif today_exp is not None and today_exp > 0:
        # 没有足够快照时，用今日增量作为日均参考
        avg_daily_exp = float(today_exp)

    est_days: int | None = None
    est_date: str | None = None
    if not already_reached and avg_daily_exp > 0:
        import math
        est_days = math.ceil(exp_remaining / avg_daily_exp)
        est_date = (datetime.now() + timedelta(days=est_days)).strftime("%Y-%m-%d")

    return {
        "lv6_threshold": LV6_EXP_THRESHOLD,
        "current_level": int(acc.level or 0),
        "current_exp": int(acc.current_exp or 0),
        "exp_remaining": exp_remaining,
        "avg_daily_exp": round(avg_daily_exp, 1),
        "est_days_to_lv6": est_days,
        "est_date": est_date,
        "already_reached": already_reached,
    }
