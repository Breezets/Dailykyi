"""任务路由：配置 CRUD、手动触发、预览。"""

from __future__ import annotations

import asyncio
from datetime import datetime
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from loguru import logger
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.exceptions import BiliAPIException
from app.models.account import Account
from app.models.task_config import TaskConfig
from app.models.task_log import TaskLog
from app.schemas.task import (
    TaskConfigSchema,
    TaskConfigUpdate,
    TaskTriggerResponse,
)
from app.services.bili_api import BiliClient
from app.services.scheduler import scheduler
from app.services.task_handlers import HANDLER_MAP, BaseTaskHandler

router = APIRouter()


@router.get("/{uid}", response_model=list[TaskConfigSchema])
async def list_task_configs(
    uid: int, db: AsyncSession = Depends(get_db)
) -> list[TaskConfig]:
    """列出指定账号的所有任务配置。"""
    result = await db.execute(
        select(TaskConfig).where(TaskConfig.account_uid == uid)
    )
    return list(result.scalars().all())


@router.put("/{uid}/{task_type}", response_model=TaskConfigSchema)
async def upsert_task_config(
    uid: int,
    task_type: str,
    body: TaskConfigUpdate,
    db: AsyncSession = Depends(get_db),
) -> TaskConfig:
    """覆盖式更新或新建任务配置。"""
    if task_type not in HANDLER_MAP:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"未知任务类型: {task_type}",
        )

    result = await db.execute(
        select(TaskConfig).where(
            TaskConfig.account_uid == uid,
            TaskConfig.task_type == task_type,
        )
    )
    cfg = result.scalar_one_or_none()

    if cfg is None:
        cfg = TaskConfig(
            account_uid=uid,
            task_type=task_type,
            enabled=body.enabled if body.enabled is not None else True,
            config=body.config,
            schedule_mode=body.schedule_mode or "random",
            schedule_config=body.schedule_config,
        )
        db.add(cfg)
    else:
        if body.enabled is not None:
            cfg.enabled = body.enabled
        if body.schedule_mode is not None:
            cfg.schedule_mode = body.schedule_mode
        cfg.config = body.config
        cfg.schedule_config = body.schedule_config
        cfg.updated_at = datetime.utcnow()

    await db.commit()
    await db.refresh(cfg)

    # 重新加载调度
    try:
        if cfg.enabled:
            scheduler._register_task(cfg)
    except Exception as exc:  # noqa: BLE001
        logger.warning(f"重新注册任务调度失败: {exc}")

    return cfg


@router.post("/{uid}/{task_type}/trigger", response_model=TaskTriggerResponse)
async def trigger_task(
    uid: int, task_type: str, db: AsyncSession = Depends(get_db)
) -> TaskTriggerResponse:
    """手动触发任务：创建 pending TaskLog 后异步执行。"""
    if task_type not in HANDLER_MAP:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"未知任务类型: {task_type}",
        )

    # 检查账号存在
    acc_result = await db.execute(
        select(Account).where(Account.uid == uid)
    )
    if acc_result.scalar_one_or_none() is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"账号不存在: uid={uid}",
        )

    # 创建 pending TaskLog
    log = TaskLog(
        account_uid=uid,
        task_type=task_type,
        status="pending",
        message="手动触发",
        started_at=datetime.utcnow(),
    )
    db.add(log)
    await db.commit()
    await db.refresh(log)

    # 后台执行
    asyncio.create_task(scheduler.execute_task(uid, task_type))

    return TaskTriggerResponse(task_log_id=log.id, status="running")


@router.get("/{uid}/{task_type}/preview")
async def preview_task(
    uid: int, task_type: str, db: AsyncSession = Depends(get_db)
) -> dict[str, Any]:
    """预览任务：执行选视频逻辑但不真正操作，返回 would_execute 列表。"""
    if task_type not in HANDLER_MAP:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"未知任务类型: {task_type}",
        )

    acc_result = await db.execute(
        select(Account).where(Account.uid == uid)
    )
    account = acc_result.scalar_one_or_none()
    if account is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"账号不存在: uid={uid}",
        )

    handler_cls = HANDLER_MAP[task_type]
    handler: BaseTaskHandler = handler_cls(account, db)

    try:
        await handler.init_client()
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"客户端初始化失败: {exc}",
        )

    would_execute: list[dict[str, Any]] = []
    preview_summary: dict[str, Any] = {"task_type": task_type, "uid": uid}

    try:
        if handler.client is None:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="客户端未初始化",
            )

        if task_type == "coin":
            # 预览候选视频
            cfg_result = await db.execute(
                select(TaskConfig).where(
                    TaskConfig.account_uid == uid,
                    TaskConfig.task_type == "coin",
                )
            )
            cfg = cfg_result.scalar_one_or_none()
            config = cfg.config if cfg else {}
            target_mode: str = str(config.get("target_mode", "recommend"))
            target_uids: list[int] = [
                int(u) for u in (config.get("target_uids") or []) if u
            ]
            if target_mode == "specified" and target_uids:
                for tu in target_uids:
                    try:
                        videos = await handler.client.get_videos_by_uid(tu, ps=5)
                        for v in videos:
                            would_execute.append(
                                {
                                    "bvid": v.get("bvid"),
                                    "title": v.get("title"),
                                    "owner_uid": tu,
                                    "source": "specified",
                                }
                            )
                    except BiliAPIException as exc:
                        logger.warning(f"预览获取 UID={tu} 视频失败: {exc}")
            else:
                try:
                    videos = await handler.client.get_recommend_videos(ps=10)
                    for v in videos:
                        would_execute.append(
                            {
                                "bvid": v.get("bvid"),
                                "title": v.get("title"),
                                "owner_uid": v.get("owner", {}).get("mid", 0)
                                if isinstance(v.get("owner"), dict)
                                else v.get("mid", 0),
                                "source": "recommend",
                            }
                        )
                except BiliAPIException as exc:
                    logger.warning(f"预览获取推荐视频失败: {exc}")
            preview_summary["plan"] = config
        elif task_type in ("watch", "share"):
            try:
                videos = await handler.client.get_recommend_videos(ps=1)
                for v in videos:
                    would_execute.append(
                        {
                            "bvid": v.get("bvid"),
                            "title": v.get("title"),
                            "cid": v.get("cid", 0),
                            "source": "recommend",
                        }
                    )
            except BiliAPIException as exc:
                logger.warning(f"预览获取推荐视频失败: {exc}")
            preview_summary["action"] = task_type
        else:
            preview_summary["action"] = (
                f"将直接调用 {task_type} 接口（无候选视频预览）"
            )
    finally:
        if handler.client is not None:
            try:
                await handler.client.close()
            except Exception:  # noqa: BLE001
                pass

    preview_summary["would_execute"] = would_execute
    preview_summary["count"] = len(would_execute)
    return preview_summary
