"""0.2.1 新增：经验快照查询路由（经验日志页独立 API）。

提供：
  - GET /snapshots         分页查询 ExpSnapshot，支持：账号、来源（task/passive/manual）、日期、
                           limit/offset，返回带前后条快照 delta，便于 UI 展示「获得 X，当前 Y」
  - GET /snapshots/summary 近 7 天汇总（total gain、按 source 分桶），用于顶部统计卡
  - GET /snapshots/export  可选：CSV 导出（暂不实现）
"""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy import select, func, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.account import Account
from app.models.exp_snapshot import ExpSnapshot
from app.models.task_log import TaskLog

router = APIRouter()


SOURCE_LABEL: dict[str, str] = {
    "task": "平台任务",
    "passive": "自动同步",
    "manual": "手动校验",
}


# ---------- 响应模型 ----------

class ExpSnapshotItem(BaseModel):
    id: int
    account_uid: int
    account_name: str | None = None
    exp: int
    level: int
    coins: int
    source: str
    source_label: str
    origin: str        # "Dailykyi" 平台任务产生 / "站外" 手机APP/网页等外部行为
    origin_label: str  # 中文显示：Dailykyi 自动任务 / 站外其他来源
    recorded_at: str
    delta: int          # 与上一条快照相比净增减（>=0 显示 +X，<0 显示 X）
    prev_exp: int       # 上一条快照经验（用于计算"获得X 当前Y"）


class ExpSnapshotListResponse(BaseModel):
    items: list[ExpSnapshotItem]
    total: int


class DailySourceBucket(BaseModel):
    date: str            # YYYY-MM-DD
    total_gain: int      # 当日净增
    task: int            # source=task 的 delta 之和
    passive: int         # source=passive
    manual: int          # source=manual
    end_exp: int         # 当日最后一次快照经验
    start_exp: int       # 当日首次快照经验


class ExpSummaryResponse(BaseModel):
    last_7_days: list[DailySourceBucket]
    accounts_covered: list[int]


# ---------- 工具 ----------

async def _uid_to_name(db: AsyncSession) -> dict[int, str]:
    res = await db.execute(select(Account.uid, Account.username))
    return {int(u): (n or f"UID:{u}") for u, n in res.all()}


# ---------- 路由 ----------

@router.get("/snapshots", response_model=ExpSnapshotListResponse)
async def list_exp_snapshots(
    account_uid: int | None = Query(default=None, description="按账号过滤"),
    source: str | None = Query(default=None, description="task / passive / manual，多选英文逗号分隔"),
    date: str | None = Query(default=None, description="YYYY-MM-DD，仅当天"),
    from_date: str | None = Query(default=None, description="起始 YYYY-MM-DD，含当天"),
    to_date: str | None = Query(default=None, description="结束 YYYY-MM-DD，含当天"),
    limit: int = Query(default=50, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    db: AsyncSession = Depends(get_db),
) -> ExpSnapshotListResponse:
    """分页查询经验快照，返回时计算每条相对"上一条快照"的 delta。

    说明：delta 基于同一账号在 ExpSnapshot 里的时间顺序计算，
    因此能直观看到每次 source 事件带来的经验变化，且区分
    平台任务 / 自动同步 / 手动校验 三种来源——正好满足"经验日志"
    独立页面的需求，避免和执行日志混杂。
    """
    # 1) WHERE 条件
    where: list[Any] = []
    if account_uid is not None:
        where.append(ExpSnapshot.account_uid == int(account_uid))
    if source:
        src_list = [s.strip() for s in source.split(",") if s.strip()]
        if src_list:
            where.append(ExpSnapshot.source.in_(src_list))
    if date:
        d = datetime.strptime(date, "%Y-%m-%d")
        where.append(ExpSnapshot.recorded_at >= d)
        where.append(ExpSnapshot.recorded_at < d + timedelta(days=1))
    else:
        if from_date:
            where.append(ExpSnapshot.recorded_at >= datetime.strptime(from_date, "%Y-%m-%d"))
        if to_date:
            where.append(ExpSnapshot.recorded_at < datetime.strptime(to_date, "%Y-%m-%d") + timedelta(days=1))

    where_expr = and_(*where) if where else True  # type: ignore[assignment]

    # 2) COUNT 总行（用于分页）
    count_stmt = select(func.count(ExpSnapshot.id)).where(where_expr)
    total_res = await db.execute(count_stmt)
    total: int = int(total_res.scalar() or 0)

    # 3) 分页数据（时间倒序，UI 上最新在前）
    page_stmt = (
        select(ExpSnapshot)
        .where(where_expr)
        .order_by(ExpSnapshot.recorded_at.desc(), ExpSnapshot.id.desc())
        .limit(limit)
        .offset(offset)
    )
    page_res = await db.execute(page_stmt)
    page = list(page_res.scalars().all())

    # 4) 补 delta：同账号按时间升序求相邻差，再回倒序返回
    #    简单做法：取该账号"当前这批页最早一条快照"之前的一条快照作基线，
    #    再按时间升序累加 delta
    uid_name = await _uid_to_name(db)

    items: list[ExpSnapshotItem] = []
    if page:
        # 对每个涉及的账号，找到各自的 prev baseline
        uids_in_page = {int(p.account_uid) for p in page}
        # page 里每页账号最老一条（recorded_at 最小），它的前一条就是 baseline
        per_uid_oldest_in_page: dict[int, datetime] = {}
        per_uid_oldest_id: dict[int, int] = {}
        for p in page:
            uid = int(p.account_uid)
            cur_at = p.recorded_at
            cur_id = int(p.id)
            if uid not in per_uid_oldest_in_page:
                per_uid_oldest_in_page[uid] = cur_at
                per_uid_oldest_id[uid] = cur_id
            else:
                if cur_at < per_uid_oldest_in_page[uid] or (
                    cur_at == per_uid_oldest_in_page[uid] and cur_id < per_uid_oldest_id[uid]
                ):
                    per_uid_oldest_in_page[uid] = cur_at
                    per_uid_oldest_id[uid] = cur_id

        # 查每个账号在 oldest 之前的最后一条快照 exp，作为该页起点 prev
        per_uid_baseline: dict[int, int] = {}
        for uid in uids_in_page:
            oldest_at = per_uid_oldest_in_page[uid]
            oldest_id = per_uid_oldest_id[uid]
            base_res = await db.execute(
                select(ExpSnapshot)
                .where(
                    ExpSnapshot.account_uid == uid,
                    (ExpSnapshot.recorded_at < oldest_at)
                    | (
                        (ExpSnapshot.recorded_at == oldest_at)
                        & (ExpSnapshot.id < oldest_id)
                    ),
                )
                .order_by(ExpSnapshot.recorded_at.desc(), ExpSnapshot.id.desc())
                .limit(1)
            )
            b = base_res.scalar_one_or_none()
            per_uid_baseline[uid] = int(b.exp or 0) if b is not None else 0

        # 把 page 升序排一下算 delta，再保持倒序返回
        page_asc = sorted(page, key=lambda x: (x.recorded_at, x.id))
        # 存每个 uid 最新一条（按升序"上一条"），作为下一条的 prev
        prev_map: dict[int, int] = dict(per_uid_baseline)
        calc_map: dict[int, dict[int, tuple[int, int]]] = {uid: {} for uid in uids_in_page}
        for s in page_asc:
            uid = int(s.account_uid)
            cur_exp = int(s.exp or 0)
            prev_exp = prev_map.get(uid, 0)
            delta = cur_exp - prev_exp
            calc_map[uid][int(s.id)] = (delta, prev_exp)
            prev_map[uid] = cur_exp

        # 5) 补 origin：是否 Dailykyi 平台任务产生的经验变化。
        #    判断规则：
        #      - source == "task" → 直接 Dailykyi
        #      - 其他 source（passive/manual）但同账号 ±60s 内存在成功 TaskLog，
        #        且 exp_gained ≈ 该快照 delta → Dailykyi（快照可能晚于任务被写入）
        #      - 其他情况 → 站外（手机APP/网页/手动在B站点操作等）
        origin_map: dict[int, tuple[str, str]] = {}
        # 取页面所有快照的 recorded_at 窗口，批量查 TaskLog
        page_times: list[datetime] = [p.recorded_at for p in page]
        page_uids = {int(p.account_uid) for p in page}
        win_low = min(page_times) - timedelta(seconds=60)
        win_high = max(page_times) + timedelta(seconds=60)
        logs_res = await db.execute(
            select(TaskLog).where(
                TaskLog.account_uid.in_(list(page_uids)),
                TaskLog.created_at >= win_low,
                TaskLog.created_at <= win_high,
                TaskLog.status == "success",
            )
        )
        logs = list(logs_res.scalars().all())
        logs_by_uid: dict[int, list[TaskLog]] = {u: [] for u in page_uids}
        for l in logs:
            logs_by_uid.setdefault(int(l.account_uid), []).append(l)
        for lst in logs_by_uid.values():
            lst.sort(key=lambda x: x.created_at)

        for s in page:
            sid = int(s.id)
            if s.source == "task":
                origin_map[sid] = ("Dailykyi", "Dailykyi 自动任务")
                continue
            uid = int(s.account_uid)
            snap_delta = max(0, calc_map.get(uid, {}).get(sid, (0, 0))[0])
            matched = False
            for log in logs_by_uid.get(uid, []):
                if abs((log.created_at - s.recorded_at).total_seconds()) > 60:
                    continue
                log_gained = int(getattr(log, "exp_gained", 0) or 0)
                # 接近判断：允许经验上限封顶情况的差异
                if log_gained > 0 and snap_delta > 0 and abs(log_gained - snap_delta) <= max(2, log_gained // 2):
                    matched = True
                    break
                if log_gained > 0 and snap_delta == 0:
                    # 满级封顶快照 delta=0，但任务实际仍有 exp_gained：判为 Dailykyi
                    matched = True
                    break
                if isinstance(log.detail, dict) and log.detail.get("delta"):
                    try:
                        d = int(log.detail["delta"])
                        if d > 0 and snap_delta > 0 and abs(d - snap_delta) <= 2:
                            matched = True
                            break
                        if d > 0 and snap_delta == 0:
                            matched = True
                            break
                    except (TypeError, ValueError):
                        pass
            if matched:
                origin_map[sid] = ("Dailykyi", "Dailykyi 自动任务")
            else:
                origin_map[sid] = ("站外", "站外来源（APP/网页/手动操作等）")

    for s in page:
        uid = int(s.account_uid)
        delta, prev_exp = calc_map[uid][int(s.id)]
        origin, origin_label = origin_map.get(int(s.id), ("站外", "站外来源（APP/网页/手动操作等）"))
        items.append(
            ExpSnapshotItem(
                id=int(s.id),
                account_uid=uid,
                account_name=uid_name.get(uid),
                exp=int(s.exp or 0),
                level=int(s.level or 0),
                coins=int(s.coins or 0),
                source=s.source or "task",
                source_label=SOURCE_LABEL.get(s.source or "task", s.source or "task"),
                origin=origin,
                origin_label=origin_label,
                recorded_at=s.recorded_at.isoformat(timespec="seconds"),
                delta=delta,
                prev_exp=prev_exp,
            )
        )

    return ExpSnapshotListResponse(items=items, total=total)


@router.get("/snapshots/summary", response_model=ExpSummaryResponse)
async def get_exp_summary(
    days: int = Query(default=7, ge=1, le=30),
    db: AsyncSession = Depends(get_db),
) -> ExpSummaryResponse:
    """返回最近 N 天经验汇总桶：每日 total_gain / 平台 / 自动 / 手动 拆分。

    顶部统计卡使用，"经验日志"页打开即拉一次。
    """
    today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
    start = today - timedelta(days=days - 1)

    # 拿范围内所有快照（按账号×时间升序）
    stmt = (
        select(ExpSnapshot)
        .where(
            ExpSnapshot.recorded_at >= start - timedelta(days=1),
            # 多拉前一天的最后一条，保证首日 start_exp 能算
            ExpSnapshot.recorded_at < today + timedelta(days=1),
        )
        .order_by(
            ExpSnapshot.account_uid.asc(),
            ExpSnapshot.recorded_at.asc(),
            ExpSnapshot.id.asc(),
        )
    )
    rows = list((await db.execute(stmt)).scalars().all())

    # 按日期分桶：{date: {uid -> (start_exp, end_exp, task, passive, manual)}}
    bucket: dict[str, dict[int, dict[str, int]]] = {}
    dates_list: list[str] = [(start + timedelta(days=i)).strftime("%Y-%m-%d") for i in range(days)]
    for d in dates_list:
        bucket[d] = {}

    # 把每条快照归属到当天，并计算该条对该账号该日的 delta（=cur - last_seen）
    last_per_uid: dict[int, int] = {}
    for s in rows:
        uid = int(s.account_uid)
        cur_exp = int(s.exp or 0)
        prev = last_per_uid.get(uid, -1)
        if prev < 0:
            delta = 0
        else:
            delta = max(0, cur_exp - prev)
        last_per_uid[uid] = cur_exp

        day = s.recorded_at.strftime("%Y-%m-%d")
        if day not in bucket:
            continue  # 前一天的只用于计算基准，不进桶
        entry = bucket[day].setdefault(
            uid, {"start_exp": cur_exp, "end_exp": cur_exp, "task": 0, "passive": 0, "manual": 0}
        )
        # start_exp 只在当天该账号首次出现时写
        if entry["end_exp"] == cur_exp and entry["task"] == entry["passive"] == entry["manual"] == 0:
            if entry["start_exp"] == cur_exp:
                # 保持初值即可
                pass
        entry["end_exp"] = cur_exp
        src = s.source or "task"
        if src in ("task", "passive", "manual") and delta >= 0:
            # 注意：delta 是该条快照相对上一条的经验变化，全部分配给该条的 source 桶
            entry[src] = entry.get(src, 0) + delta
        # start_exp 修正：如果 prev!=-1 且今天第一次看到该账号，start_exp=prev+之前
        # 简化：如果当天有更早快照在 bucket 里已经写过 start_exp，就不动它
        # 否则 prev>=0 时，start_exp=prev
        if prev >= 0:
            # 如果是当天该账号第一条记录，start_exp 应等于 prev
            # 判断方法：end_exp 刚被写为 cur_exp，但 start_exp 也是 cur_exp，
            # 且该账号今天尚无任何 delta，说明这是今天第一条 -> 改 start_exp = prev
            if (
                entry["end_exp"] == cur_exp
                and entry["start_exp"] == cur_exp
                and entry["task"] + entry["passive"] + entry["manual"] - delta == 0
            ):
                entry["start_exp"] = prev

    last_7_days: list[DailySourceBucket] = []
    accounts_seen: set[int] = set()
    for day in dates_list:
        day_bucket = bucket[day]
        t = p = m = total_gain = 0
        start_exp_day = end_exp_day = 0
        if day_bucket:
            first_uid = next(iter(day_bucket.keys()))
            start_exp_day = day_bucket[first_uid]["start_exp"]
            end_exp_day = day_bucket[first_uid]["end_exp"]
            # 多账号简单相加（整体视图），start/end 取单账号逻辑保留
            start_exp_day = 0
            end_exp_day = 0
            for uid, e in day_bucket.items():
                accounts_seen.add(uid)
                t += e["task"]
                p += e["passive"]
                m += e["manual"]
                total_gain += max(0, e["end_exp"] - e["start_exp"])
            total_gain = max(total_gain, t + p + m)
        last_7_days.append(
            DailySourceBucket(
                date=day,
                total_gain=total_gain,
                task=t,
                passive=p,
                manual=m,
                start_exp=start_exp_day,
                end_exp=end_exp_day,
            )
        )

    return ExpSummaryResponse(
        last_7_days=last_7_days,
        accounts_covered=sorted(accounts_seen),
    )
