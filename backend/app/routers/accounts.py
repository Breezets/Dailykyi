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
from app.services.exp_service import compute_today_exp_gain, compute_today_exp_split

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


@router.post("/{uid}/refresh-exp")
async def refresh_exp_manual(uid: int, db: AsyncSession = Depends(get_db)):
    """0.2.1 新增：手动校验经验。

    1. 解密 Cookie → 调 B 站 nav 接口刷新 current_exp / coins / level 缓存
    2. 写一条 source='manual' 的 ExpSnapshot
    3. 返回最新的账号信息 + 今日经验拆分（总/平台/其他）

    用户在其他设备完成任务后（如手机 APP 分享/登录），可点此按钮立即同步。
    """
    result = await db.execute(select(Account).where(Account.uid == uid))
    account = result.scalar_one_or_none()
    if account is None:
        raise HTTPException(status_code=404, detail="账号不存在")

    cookie_str = decrypt_cookie(account.cookie_encrypted or "")
    if not cookie_str:
        raise HTTPException(status_code=400, detail="无有效 Cookie")

    # 先查最近一条快照（用于计算 delta）
    from app.models.exp_snapshot import ExpSnapshot
    last_result = await db.execute(
        select(ExpSnapshot)
        .where(ExpSnapshot.account_uid == uid)
        .order_by(ExpSnapshot.recorded_at.desc(), ExpSnapshot.id.desc())
        .limit(1)
    )
    last_snap = last_result.scalar_one_or_none()
    last_exp = int(last_snap.exp) if last_snap else 0

    client = BiliClient(cookies=cookie_str)
    try:
        nav = await client.get_user_info()
    except Exception as exc:  # noqa: BLE001
        await client.close()
        raise HTTPException(status_code=502, detail=f"B 站接口失败: {exc}")

    def _safe_int(val: Any) -> int:
        try:
            return int(val)
        except (ValueError, TypeError):
            return 0

    account.username = nav.get("uname") or account.username
    account.avatar_url = nav.get("face") or account.avatar_url
    account.level = _safe_int((nav.get("level_info") or {}).get("current_level", 0))
    account.current_exp = _safe_int((nav.get("level_info") or {}).get("current_exp", 0))
    account.next_level_exp = _safe_int((nav.get("level_info") or {}).get("next_exp", 0))
    account.coins = _safe_int(nav.get("money", 0))
    account.last_login_at = datetime.now()
    await client.close()

    new_exp = int(account.current_exp or 0)
    delta = max(0, new_exp - last_exp)

    # 写 source=manual 快照
    snap = ExpSnapshot(
        account_uid=uid,
        exp=new_exp,
        level=int(account.level or 0),
        coins=int(account.coins or 0),
        source="manual",
        recorded_at=datetime.now(),
    )
    db.add(snap)
    await db.commit()

    # 返回最新经验拆分
    exp_split = await compute_today_exp_split(db, account)
    logger.info(
        f"手动校验经验 uid={uid} last={last_exp} new={new_exp} delta={delta}"
    )

    return {
        "message": "校验完成",
        "uid": uid,
        "before_exp": last_exp,
        "after_exp": new_exp,
        "delta": delta,
        "level": account.level,
        "coins": account.coins,
        "today_exp_split": exp_split,
    }
