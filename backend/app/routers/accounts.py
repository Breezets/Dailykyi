"""账号管理路由。前缀 /api/v1/accounts"""

from datetime import datetime
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from loguru import logger
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.deps import decrypt_cookie, get_current_user
from app.exceptions import BiliAPIError
from app.models.account import Account
from app.models.task_log import TaskLog
from app.services.bili_api import BiliClient
from app.services.exp_service import compute_today_exp_gain

router = APIRouter()


@router.get("")
async def list_accounts(db: AsyncSession = Depends(get_db)):
    """返回所有账号列表，含今日经验（基于 ExpSnapshot 快照对比）。"""
    result = await db.execute(select(Account))
    accounts = list(result.scalars().all())

    items = []
    for acc in accounts:
        # 当日经验增量（基于 24h 前快照对比，无快照时 fallback 到 TaskLog 汇总）
        today_exp = await compute_today_exp_gain(db, acc)

        items.append(
            {
                "uid": acc.uid,
                "username": acc.username,
                "avatar_url": acc.avatar_url,
                "level": acc.level,
                "current_exp": acc.current_exp,
                "next_level_exp": acc.next_level_exp,
                "coins": acc.coins,
                # 0.2.0：未绑定 cookie → missing；否则展示定时检测的真实状态
                "cookie_status": (
                    "missing" if not acc.cookie_encrypted else acc.cookie_status
                ),
                "cookie_checked_at": (
                    acc.cookie_checked_at.isoformat() if acc.cookie_checked_at else None
                ),
                "is_active": acc.is_active,
                "today_exp_gained": today_exp,
            }
        )
    return items


@router.post("/check-cookies")
async def check_cookies(db: AsyncSession = Depends(get_db)):
    """立即检测所有账号 cookie 有效性（0.2.0）。"""
    from app.services.cookie_checker import check_all_accounts

    try:
        stats = await check_all_accounts(db)
        return {"message": "检测完成", **stats}
    except Exception as exc:  # noqa: BLE001
        logger.exception("手动 cookie 检测异常")
        raise HTTPException(status_code=500, detail=f"检测失败: {exc}")


@router.delete("/{uid}")
async def delete_account(uid: int, db: AsyncSession = Depends(get_db)):
    """删除账号及关联数据。"""
    result = await db.execute(select(Account).where(Account.uid == uid))
    account = result.scalar_one_or_none()
    if account is None:
        raise HTTPException(status_code=404, detail="账号不存在")
    await db.delete(account)
    await db.commit()
    return {"message": "删除成功"}


@router.post("/{uid}/refresh")
async def refresh_cookie(uid: int, db: AsyncSession = Depends(get_db)):
    """刷新 Cookie：用已有 cookie 调用 nav 接口更新账号信息。"""
    result = await db.execute(select(Account).where(Account.uid == uid))
    account = result.scalar_one_or_none()
    if account is None:
        raise HTTPException(status_code=404, detail="账号不存在")

    cookie_str = decrypt_cookie(account.cookie_encrypted or "")
    if not cookie_str:
        raise HTTPException(status_code=400, detail="无有效 Cookie")

    client = BiliClient(cookies=cookie_str)
    try:
        nav = await client.get_nav_info()
        account.username = nav.get("uname") or account.username
        account.avatar_url = nav.get("face") or account.avatar_url
        level_info = nav.get("level_info") or {}

        def _safe_int(val: Any) -> int:
            try:
                return int(val)
            except (ValueError, TypeError):
                return 0

        account.level = _safe_int(level_info.get("current_level", 0))
        account.current_exp = _safe_int(level_info.get("current_exp", 0))
        account.next_level_exp = _safe_int(level_info.get("next_exp", 0))
        account.coins = _safe_int(nav.get("money", 0))
        account.last_login_at = datetime.now()
        await db.commit()
        return {"message": "刷新成功"}
    except BiliAPIError as exc:
        raise HTTPException(status_code=502, detail=exc.message)
    finally:
        await client.close()
