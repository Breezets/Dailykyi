"""账号 Cookie 有效性检测服务（0.2.0）。

定时遍历所有账号：
- 用带风控指纹的 nav 验证 cookie 是否有效
- 更新 Account.cookie_status / cookie_checked_at
- 失效或临期时通过 NotifyService 推送告警
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from loguru import logger
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.deps import decrypt_cookie
from app.exceptions import BiliAPIException
from app.models.account import Account
from app.services.bili_api import BiliClient
from app.services.notify import NotifyService


def _safe_int(val: Any) -> int:
    """安全转 int，处理满级账号 next_exp='--' 等非数字值。"""
    try:
        return int(val)
    except (ValueError, TypeError):
        return 0


async def check_account_cookie(db: AsyncSession, account: Account) -> str:
    """检测单个账号 cookie 有效性，返回新状态（ok / expired）。

    同时顺带刷新账号缓存字段（昵称/等级/经验/硬币）。
    """
    cookies = decrypt_cookie(account.cookie_encrypted or "")
    if not cookies:
        return "expired"

    client = BiliClient(cookies=cookies)
    try:
        info = await client.get_user_info()
    except (BiliAPIException, Exception) as exc:  # noqa: BLE001
        logger.warning(f"cookie 检测失败 uid={account.uid}: {exc}")
        return "expired"
    finally:
        await client.close()

    # nav 返回 isLogin=False 视为 cookie 失效
    if info.get("isLogin") is False:
        return "expired"

    # 刷新缓存字段
    account.username = info.get("uname") or account.username
    account.avatar_url = info.get("face") or account.avatar_url
    account.coins = _safe_int(info.get("money", 0))
    level_info = info.get("level_info") or {}
    account.level = _safe_int(level_info.get("current_level", 0))
    account.current_exp = _safe_int(level_info.get("current_exp", 0))
    account.next_level_exp = _safe_int(level_info.get("next_exp", 0))
    return "ok"


async def check_all_accounts(db: AsyncSession) -> dict[str, Any]:
    """检测所有账号的 cookie 有效性并推送告警。

    返回统计：{"checked", "ok", "expired", "warned_expiring"}
    """
    result = await db.execute(select(Account))
    accounts = list(result.scalars().all())

    stats = {"checked": 0, "ok": 0, "expired": 0, "warned_expiring": 0}
    notify = NotifyService(db)

    for acc in accounts:
        if not acc.cookie_encrypted:
            # 没有 cookie 的账号（占位/异常）标记 expired
            acc.cookie_status = "expired"
            acc.cookie_checked_at = datetime.now()
            continue

        old_status = acc.cookie_status
        new_status = await check_account_cookie(db, acc)
        acc.cookie_status = new_status
        acc.cookie_checked_at = datetime.now()
        stats["checked"] += 1

        if new_status == "ok":
            stats["ok"] += 1
            # 仅状态从非 ok 变为 ok 时不告警；临期预警独立判断
            if acc.cookie_expires_at is not None:
                remaining = (acc.cookie_expires_at - datetime.now()).days
                if 0 <= remaining <= 3:
                    try:
                        await notify.send_cookie_warning(acc, remaining)
                        stats["warned_expiring"] += 1
                    except Exception as exc:  # noqa: BLE001
                        logger.warning(f"Cookie 临期预警发送失败 uid={acc.uid}: {exc}")
        else:
            stats["expired"] += 1
            # 状态从 ok/unknown 变 expired 才告警（避免每次检测重复轰炸）
            if old_status != "expired":
                try:
                    await notify.send_cookie_expired(acc)
                except Exception as exc:  # noqa: BLE001
                    logger.warning(f"Cookie 失效告警发送失败 uid={acc.uid}: {exc}")

    await db.commit()
    logger.info(
        f"Cookie 检测完成: checked={stats['checked']} "
        f"ok={stats['ok']} expired={stats['expired']}"
    )
    return stats
