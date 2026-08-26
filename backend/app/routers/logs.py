"""日志路由。前缀 /api/v1/logs"""

import asyncio
import json
from datetime import datetime, timedelta
from typing import Any

from fastapi import APIRouter, Depends, Query
from fastapi.responses import StreamingResponse
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import AsyncSessionLocal, get_db
from app.models.account import Account
from app.models.task_log import TaskLog

router = APIRouter()


@router.get("/{log_id}")
async def get_log_by_id(
    log_id: int,
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """按 ID 查询单条日志（用于立即测试轮询结果）。"""
    from fastapi import HTTPException, status

    result = await db.execute(select(TaskLog).where(TaskLog.id == log_id))
    log = result.scalar_one_or_none()
    if log is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="日志不存在")
    return {
        "id": log.id,
        "account_uid": log.account_uid,
        "task_type": log.task_type,
        "status": log.status,
        "message": log.message,
        "exp_gained": log.exp_gained or 0,
        "detail": log.detail or {},
        "started_at": log.started_at.isoformat() if log.started_at else None,
        "completed_at": log.completed_at.isoformat() if log.completed_at else None,
        "created_at": log.created_at.isoformat() if log.created_at else None,
    }


@router.get("")
async def list_logs(
    uid: int | None = Query(None),
    task_type: str | None = Query(None),
    status: str | None = Query(None),
    date: str | None = Query(None),
    limit: int = Query(10, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """查询日志列表，返回 {total, logs}。"""
    query = select(TaskLog)
    count_query = select(func.count(TaskLog.id))

    if uid:
        query = query.where(TaskLog.account_uid == uid)
        count_query = count_query.where(TaskLog.account_uid == uid)
    if task_type:
        query = query.where(TaskLog.task_type == task_type)
        count_query = count_query.where(TaskLog.task_type == task_type)
    if status:
        query = query.where(TaskLog.status == status)
        count_query = count_query.where(TaskLog.status == status)
    if date:
        try:
            day = datetime.strptime(date, "%Y-%m-%d")
            next_day = day + timedelta(days=1)
            query = query.where(TaskLog.created_at >= day, TaskLog.created_at < next_day)
            count_query = count_query.where(
                TaskLog.created_at >= day, TaskLog.created_at < next_day
            )
        except ValueError:
            pass

    total_result = await db.execute(count_query)
    total = total_result.scalar() or 0

    query = query.order_by(TaskLog.created_at.desc()).offset(offset).limit(limit)
    result = await db.execute(query)
    logs = list(result.scalars().all())

    # 账号名映射
    uid_set = {l.account_uid for l in logs}
    if uid_set:
        acc_result = await db.execute(select(Account).where(Account.uid.in_(uid_set)))
        uid_to_name = {a.uid: a.username or "" for a in acc_result.scalars().all()}
    else:
        uid_to_name = {}

    return {
        "total": total,
        "logs": [
            {
                "id": l.id,
                "account_uid": l.account_uid,
                "account_name": uid_to_name.get(l.account_uid, ""),
                "task_type": l.task_type,
                "status": l.status,
                "message": l.message,
                "detail": l.detail,
                "exp_gained": l.exp_gained,
                "created_at": l.created_at.isoformat() if l.created_at else "",
            }
            for l in logs
        ],
    }


@router.get("/stream")
async def log_stream() -> StreamingResponse:
    """SSE 日志流：每 3 秒推送新增 TaskLog。"""

    async def event_generator():
        last_id = 0
        while True:
            async with AsyncSessionLocal() as db:
                result = await db.execute(
                    select(TaskLog)
                    .where(TaskLog.id > last_id)
                    .order_by(TaskLog.id)
                    .limit(50)
                )
                logs = list(result.scalars().all())
                for log in logs:
                    last_id = max(last_id, log.id)
                    acc_result = await db.execute(
                        select(Account).where(Account.uid == log.account_uid)
                    )
                    acc = acc_result.scalar_one_or_none()
                    data = {
                        "id": log.id,
                        "account_uid": log.account_uid,
                        "account_name": acc.username if acc else "",
                        "task_type": log.task_type,
                        "status": log.status,
                        "message": log.message,
                        "detail": log.detail,
                        "exp_gained": log.exp_gained,
                        "created_at": log.created_at.isoformat() if log.created_at else "",
                    }
                    yield f"data: {json.dumps(data)}\n\n"
            await asyncio.sleep(3)

    return StreamingResponse(event_generator(), media_type="text/event-stream")
