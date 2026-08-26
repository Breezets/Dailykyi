"""仪表盘路由：聚合账号、当日统计、最近日志、即将执行任务。"""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.account import Account
from app.models.task_log import TaskLog
from app.schemas.task import (
    DashboardAccount,
    DashboardLog,
    DashboardResponse,
    DashboardStats,
    DashboardUpcoming,
)
from app.services.scheduler import scheduler

router = APIRouter()


def _start_of_day() -> datetime:
    """今天 00:00:00。"""
    now = datetime.now()
    return now.replace(hour=0, minute=0, second=0, microsecond=0)


@router.get("", response_model=DashboardResponse)
async def get_dashboard(
    db: AsyncSession = Depends(get_db),
) -> DashboardResponse:
    """聚合仪表盘数据。"""
    today_start = _start_of_day()

    # 1. 账号列表
    acc_result = await db.execute(select(Account))
    accounts_orm = list(acc_result.scalars().all())

    accounts: list[DashboardAccount] = []
    for acc in accounts_orm:
        # 当日 exp 汇总
        log_result = await db.execute(
            select(TaskLog).where(
                TaskLog.account_uid == acc.uid,
                TaskLog.created_at >= today_start,
            )
        )
        today_logs = list(log_result.scalars().all())
        today_exp = sum(int(l.exp_gained or 0) for l in today_logs)

        accounts.append(
            DashboardAccount(
                uid=acc.uid,
                username=acc.username,
                avatar_url=acc.avatar_url,
                level=acc.level,
                current_exp=acc.current_exp,
                next_level_exp=acc.next_level_exp,
                coins=acc.coins,
                today_exp_gained=today_exp,
            )
        )

    # 2. 当日统计
    all_today_result = await db.execute(
        select(TaskLog).where(TaskLog.created_at >= today_start)
    )
    all_today_logs = list(all_today_result.scalars().all())
    today_stats = DashboardStats(
        total_tasks=len(all_today_logs),
        success_count=sum(1 for l in all_today_logs if l.status == "success"),
        failed_count=sum(1 for l in all_today_logs if l.status == "failed"),
        skipped_count=sum(1 for l in all_today_logs if l.status == "skipped"),
    )

    # 3. 最近 10 条日志（带账号名）
    recent_result = await db.execute(
        select(TaskLog).order_by(TaskLog.created_at.desc()).limit(10)
    )
    recent_logs_orm = list(recent_result.scalars().all())
    # 构造 uid -> username 映射
    uid_to_name: dict[int, str] = {a.uid: a.username or "" for a in accounts_orm}
    recent_logs: list[DashboardLog] = [
        DashboardLog(
            id=l.id,
            account_uid=l.account_uid,
            account_name=uid_to_name.get(l.account_uid, ""),
            task_type=l.task_type,
            status=l.status,
            message=l.message,
            exp_gained=l.exp_gained,
            created_at=l.created_at,
        )
        for l in recent_logs_orm
    ]

    # 4. 即将执行任务
    upcoming_raw = scheduler.get_upcoming(limit=10)
    upcoming: list[DashboardUpcoming] = [
        DashboardUpcoming(
            job_id=item["job_id"],
            account_uid=item["account_uid"],
            task_type=item["task_type"],
            next_run_time=item.get("next_run_time"),
        )
        for item in upcoming_raw
    ]

    return DashboardResponse(
        accounts=accounts,
        today_stats=today_stats,
        recent_logs=recent_logs,
        upcoming=upcoming,
    )
