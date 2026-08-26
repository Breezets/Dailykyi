"""系统设置路由：GET/PUT 配置 + Debug 推送测试。"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from loguru import logger
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.account import Account
from app.models.system_config import SystemConfig
from app.services.notify import NotifyService

router = APIRouter()


@router.get("/config")
async def get_system_config(db: AsyncSession = Depends(get_db)) -> dict[str, Any]:
    """返回完整的系统配置。"""
    result = await db.execute(select(SystemConfig))
    rows = list(result.scalars().all())
    config: dict[str, Any] = {}
    for row in rows:
        config[row.key] = row.value
    return config


@router.put("/config")
async def update_system_config(
    body: dict[str, Any],
    db: AsyncSession = Depends(get_db),
) -> dict[str, str]:
    """保存配置：body 为 JSON，直接覆盖 SystemConfig 对应 key 的 value。"""
    for key, value in body.items():
        result = await db.execute(
            select(SystemConfig).where(SystemConfig.key == key)
        )
        row = result.scalar_one_or_none()
        if row is None:
            row = SystemConfig(key=key, value=value)
            db.add(row)
        else:
            row.value = value
        logger.info(f"系统配置更新: {key} = {value!r}")
    await db.commit()
    return {"status": "ok"}


@router.post("/notify/test-failure")
async def test_failure_notification(
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """真实失败通知测试：模拟一个账号任务失败，走完整 NotifyService.send_task_result 分支。

    返回：
    - sent: bool（是否真的调用了 send_server_chan，不代表一定送达手机端，送达要看 Server酱 响应）
    - server_chan_key_configured: bool
    - notify_on_failure: bool
    - log: str（说明信息；若 sent=False 会解释为什么没发）
    - account: dict（被用来模拟的账号，可能是默认 Mock 账号，没有真实账号时用）
    """
    # 取一个真实账号（有则用真实账号体，没有则用 mock 账号）
    acc_result = await db.execute(select(Account).limit(1))
    real_acc = acc_result.scalar_one_or_none()
    if real_acc is not None:
        mock_account = Account(
            uid=real_acc.uid,
            username=real_acc.username or f"UID:{real_acc.uid}",
            level=real_acc.level,
            current_exp=real_acc.current_exp,
            next_level_exp=real_acc.next_level_exp,
            coins=real_acc.coins if real_acc.coins is not None else 0,
        )
    else:
        mock_account = Account(
            uid=123456789,
            username="测试账号",
            level=4,
            current_exp=3000,
            next_level_exp=4500,
            coins=100,
        )

    notify = NotifyService(db)
    cfg = await notify._load_config()

    logs: list[str] = []
    key_ok = bool(cfg["server_chan_key"])
    failure_switch_on = bool(cfg["notify_on_failure"])

    if not key_ok:
        logs.append("未检测到 Server酱 Key，系统跳过发送。请先在「通知设置」里填写 Key 并保存。")
    if not failure_switch_on and key_ok:
        logs.append("「任务失败时推送」开关已关闭，本测试不会推送到手机。请先打开该开关并保存。")

    sent = False
    message = (
        "【测试】投币任务连续 3 次返回 B站 -403 风控校验失败，已自动跳过。"
        " 这是一条系统设置页发起的失败推送测试 — 如果你的手机收到此消息，"
        "说明 Server酱 配置正确，任务失败时你将收到真实告警。"
    )
    try:
        await notify.send_task_result(
            account=mock_account,
            task_type="coin",
            success=False,
            message=message,
            exp_gained=0,
        )
        # 如果 Server酱 key + 开关都正常，send_server_chan 内部会返回 True
        if key_ok and failure_switch_on:
            sent = True
    except Exception as exc:  # noqa: BLE001
        logger.error(f"[Notify] 测试失败通知异常: {exc}")
        logs.append(f"发送过程出现异常: {exc!s}")

    return {
        "sent": sent,
        "server_chan_key_configured": key_ok,
        "notify_on_failure": failure_switch_on,
        "log": " ".join(logs) if logs else "调用结束，请到手机 Server酱 绑定端查看是否收到。",
        "account": {
            "uid": mock_account.uid,
            "username": mock_account.username,
            "used_real": real_acc is not None,
        },
    }
