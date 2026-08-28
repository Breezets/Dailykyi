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


async def compute_today_exp_split(db: AsyncSession, acc: Account) -> dict[str, int]:
    """0.2.1 新增：分离今日经验为「平台获得」与「其他设备获得」。

    返回：
      {
        "total": 今日总经验,
        "platform": 平台执行任务获得,
        "other": 其他设备 / 其他方式获得 = max(0, total - platform),
        "baseline_exp": 计算起点（24h 前快照 exp；无则用今日 0 点前最后一条；再无则 0）,
        "current_exp": 当前经验,
        "has_baseline_snapshot": 是否有可用的 24h 基线快照
      }

    关键修复（v0.2.1 实测 Bug）：
      1. 满级（LV6）B 站 current_exp 恒为 28800，快照对比看不出变化——改用 TaskLog.detail.delta
         （即 last_exp_info.before_exp / after_exp 的真实差值，B 站服务端在满级时
         before_exp=28800, after_exp=28800 也会 delta=0，但 TaskLog.exp_gained=actual*10 是对的，
         所以这里优先用 detail.delta，其次 TaskLog.exp_gained，最后才是快照对比）
      2. 首日无 24h 基线时，用"今日 0 点前最后一条快照"作 baseline_exp，不再写死 0
         导致 platform 暴增
    """
    now = datetime.now()
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)

    # ========== 1) baseline_exp：今日 0 点之前的最后一条快照（比 24h 窗口更稳定）==========
    pre_day_result = await db.execute(
        select(ExpSnapshot)
        .where(
            ExpSnapshot.account_uid == acc.uid,
            ExpSnapshot.recorded_at < today_start,
        )
        .order_by(ExpSnapshot.recorded_at.desc(), ExpSnapshot.id.desc())
        .limit(1)
    )
    pre_day_snap = pre_day_result.scalar_one_or_none()

    # 兼容旧逻辑：24h±30min 内的快照有则算"有基线"（用于 UI 提示首日）
    window_start = now - timedelta(hours=24, minutes=30)
    window_end = now - timedelta(hours=23, minutes=30)
    base_result = await db.execute(
        select(ExpSnapshot)
        .where(
            ExpSnapshot.account_uid == acc.uid,
            ExpSnapshot.recorded_at >= window_start,
            ExpSnapshot.recorded_at <= window_end,
        )
        .order_by(ExpSnapshot.recorded_at.desc())
        .limit(1)
    )
    baseline_snap_24h = base_result.scalar_one_or_none()
    has_baseline = baseline_snap_24h is not None

    # baseline_exp：优先 24h 窗口快照（更准），其次 0 点前最后一条，再无则 0
    if baseline_snap_24h is not None:
        baseline_exp = int(baseline_snap_24h.exp or 0)
    elif pre_day_snap is not None:
        baseline_exp = int(pre_day_snap.exp or 0)
    else:
        baseline_exp = 0

    current_exp = int(acc.current_exp or 0)
    total = max(0, current_exp - baseline_exp)

    # ========== 2) platform：今日平台任务获得经验 ==========
    # 方案 A（优先）：遍历今日 0 点后所有 success TaskLog，
    #   1. detail.delta 有数值（refresh_exp_snapshot 写入，最准）
    #   2. 否则用 TaskLog.exp_gained（子类推算值，满级时仍能拿到 actual*10）
    log_rows_result = await db.execute(
        select(TaskLog)
        .where(
            TaskLog.account_uid == acc.uid,
            TaskLog.created_at >= today_start,
            TaskLog.status == "success",
        )
        .order_by(TaskLog.created_at.asc(), TaskLog.id.asc())
    )
    log_rows = list(log_rows_result.scalars().all())

    platform_from_logs = 0
    for tl in log_rows:
        d = tl.detail
        delta_from_detail: int | None = None
        if isinstance(d, dict):
            raw = d.get("delta")
            if raw is None:
                # 兼容：detail 里 after_exp - before_exp
                a = d.get("after_exp")
                b = d.get("before_exp")
                if a is not None and b is not None:
                    try:
                        delta_from_detail = int(a) - int(b)
                        if delta_from_detail < 0:
                            delta_from_detail = None
                    except (TypeError, ValueError):
                        delta_from_detail = None
            else:
                try:
                    delta_from_detail = int(raw)
                    if delta_from_detail < 0:
                        delta_from_detail = None
                except (TypeError, ValueError):
                    delta_from_detail = None
        if delta_from_detail is not None and delta_from_detail > 0:
            platform_from_logs += delta_from_detail
        elif int(tl.exp_gained or 0) > 0:
            platform_from_logs += int(tl.exp_gained or 0)

    # 方案 B（fallback）：用今日快照对比（老版本数据无 TaskLog.detail 时）
    platform_from_snaps = 0
    try:
        day_snaps_result = await db.execute(
            select(ExpSnapshot)
            .where(
                ExpSnapshot.account_uid == acc.uid,
                ExpSnapshot.recorded_at >= today_start,
            )
            .order_by(ExpSnapshot.recorded_at.asc(), ExpSnapshot.id.asc())
        )
        day_snaps = list(day_snaps_result.scalars().all())
        last_seen_exp = int(pre_day_snap.exp) if pre_day_snap is not None else 0
        for s in day_snaps:
            s_exp = int(s.exp or 0)
            if s.source == "task":
                delta_s = max(0, s_exp - last_seen_exp)
                platform_from_snaps += delta_s
            last_seen_exp = s_exp
    except Exception as e:  # noqa: BLE001
        import logging as _log
        _log.getLogger(__name__).debug(
            f"compute_today_exp_split 快照算法跳过: {e}"
        )

    # 取两者较大值（满级后快照 delta=0，所以 logs 方案能拿到 actual*10）
    platform = max(platform_from_logs, platform_from_snaps)

    # ========== 3) total 二次修正：满级 / 无基线场景 ==========
    # 满级特殊：B 站 current_exp 被封顶（28800），此时用"获得经验累加"代替快照差值
    # 判定：current_exp 达到 LV6 阈值，且 baseline_exp == current_exp，但 platform>0
    if (
        current_exp >= LV6_EXP_THRESHOLD
        and baseline_exp >= LV6_EXP_THRESHOLD - 1
        and total <= 0
        and platform > 0
    ):
        # 满级后 B 站服务端 current_exp 不再变化，total 退化为日志实际获得量
        # 这样平台/其他拆分仍能反映真实所得
        total = platform

    # 首日无任何基线：total 至少等于 platform（平台执行任务的经验一定包含在总经验里）
    if baseline_exp == 0 and platform > total:
        total = platform

    other = max(0, total - platform)

    return {
        "total": total,
        "platform": platform,
        "other": other,
        "baseline_exp": baseline_exp,
        "current_exp": current_exp,
        "has_baseline_snapshot": has_baseline,
    }


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
