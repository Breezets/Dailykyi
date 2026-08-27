"""通知推送服务：Server酱。"""

from __future__ import annotations

from datetime import datetime
from typing import Any

import httpx
from loguru import logger
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.account import Account
from app.models.system_config import SystemConfig
from app.models.task_log import TaskLog


# SystemConfig 中通知相关的独立 key 列表
NOTIFY_KEYS = [
    "server_chan_key",
    "notify_on_failure",
    "notify_on_success",
    "notify_daily_summary",
    "notify_cookie_warning",
    "notify_risk_alert",
    "dnd_enabled",
    "dnd_start",
    "dnd_end",
]


class NotifyService:
    """根据 SystemConfig 中的独立 key 读取通知配置并推送。"""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    # ============== 基础工具 ==============

    async def _load_config(self) -> dict[str, Any]:
        """从 SystemConfig 把所有通知相关 key 加载成一个 dict。
        值不存在时返回默认，保证下游不用判空。"""
        result = await self.db.execute(
            select(SystemConfig).where(SystemConfig.key.in_(NOTIFY_KEYS))
        )
        rows = list(result.scalars().all())
        raw: dict[str, Any] = {r.key: r.value for r in rows}

        return {
            "server_chan_key": str(raw.get("server_chan_key", "") or "").strip(),
            "notify_on_failure": bool(raw.get("notify_on_failure", True)),   # 默认失败开启
            "notify_on_success": bool(raw.get("notify_on_success", False)),
            "notify_daily_summary": bool(raw.get("notify_daily_summary", False)),
            "notify_cookie_warning": bool(raw.get("notify_cookie_warning", False)),
            "notify_risk_alert": bool(raw.get("notify_risk_alert", True)),   # 默认风控告警开
            "dnd_enabled": bool(raw.get("dnd_enabled", False)),
            "dnd_start": str(raw.get("dnd_start", "23:00") or "23:00"),
            "dnd_end": str(raw.get("dnd_end", "08:00") or "08:00"),
        }

    async def send_server_chan(self, key: str, title: str, body: str) -> bool:
        """Server 酱推送：POST https://sctapi.ftqq.com/{key}.send。

        form-data 格式：title / desp（支持 Markdown）。
        详细日志：HTTP status / response code / message / data 摘要。
        """
        url = f"https://sctapi.ftqq.com/{key}.send"
        try:
            async with httpx.AsyncClient(timeout=12) as client:
                resp = await client.post(url, data={"title": title, "desp": body})
                # 打印日志（敏感 key 脱敏只保留前后各 4 位）
                masked = key if len(key) <= 12 else f"{key[:4]}***{key[-4:]}"
                if resp.status_code == 200:
                    try:
                        data = resp.json()
                    except ValueError:
                        logger.warning(
                            f"[Server酱] 响应非 JSON: key={masked} body={resp.text[:200]}"
                        )
                        return False
                    code = data.get("code")
                    message = data.get("message")
                    if code == 0:
                        pushid = (data.get("data") or {}).get("pushid", "?")
                        logger.info(
                            f"[Server酱] 推送成功: key={masked} pushid={pushid} title={title!r}"
                        )
                        return True
                    logger.warning(
                        f"[Server酱] 推送失败: key={masked} code={code} msg={message}"
                    )
                    return False
                logger.warning(
                    f"[Server酱] HTTP {resp.status_code}: key={masked} body={resp.text[:200]}"
                )
                return False
        except httpx.TimeoutException as exc:
            logger.warning(f"[Server酱] 超时: {exc}")
            return False
        except httpx.HTTPError as exc:
            logger.warning(f"[Server酱] 网络错误: {exc}")
            return False
        except Exception as exc:  # noqa: BLE001
            logger.warning(f"[Server酱] 未知异常: {exc}", exc_info=True)
            return False

    # ============== 统一发送入口 ==============

    async def send(
        self,
        account_uid: int,
        message_type: str,
        body: str,
        is_urgent: bool = False,
    ) -> None:
        """发送通知。
        - server_chan_key 为空则打印警告并返回
        - 非 urgent 且 dnd_enabled 时检查免打扰时段
        """
        cfg = await self._load_config()
        server_chan_key = cfg["server_chan_key"]

        if not server_chan_key:
            logger.warning(
                f"[Notify] 未配置 Server酱 Key，跳过发送: uid={account_uid} "
                f"type={message_type}。请前往「系统设置 → 通知设置」填写 key 并保存。"
            )
            return

        # 免打扰（urgent 消息跳过）
        if not is_urgent and cfg["dnd_enabled"]:
            now = datetime.now()
            current_str = now.strftime("%H:%M")
            if _in_dnd_window(current_str, cfg["dnd_start"], cfg["dnd_end"]):
                logger.info(
                    f"[Notify] 免打扰时段({cfg['dnd_start']}-{cfg['dnd_end']}), "
                    f"跳过: uid={account_uid} type={message_type}"
                )
                return

        ok = await self.send_server_chan(server_chan_key, "Dailykyi", body)
        if not ok:
            logger.warning(
                f"[Notify] 发送最终未成功: uid={account_uid} type={message_type}"
            )

    # ============== 场景封装 ==============

    async def send_task_result(
        self,
        account: Account,
        task_type: str,
        success: bool,
        message: str,
        exp_gained: int = 0,
    ) -> None:
        """根据 notify_on_success / notify_on_failure 开关决定是否发送。"""
        cfg = await self._load_config()

        if success:
            if not cfg["notify_on_success"]:
                logger.debug(
                    f"[Notify] 成功通知未开启，跳过: uid={account.uid} type={task_type}"
                )
                return
        else:
            if not cfg["notify_on_failure"]:
                logger.debug(
                    f"[Notify] 失败通知已关闭，跳过: uid={account.uid} type={task_type}"
                )
                return

        status_icon = "✅" if success else "❌"
        status_text = "成功" if success else "失败"
        username = account.username or f"UID:{account.uid}"
        task_names = {
            "coin": "投币",
            "watch": "观看",
            "share": "分享",
            "live_sign": "直播签到",
            "silver2coin": "银瓜子换币",
        }
        task_display = task_names.get(task_type, task_type)

        lines = [
            f"## {status_icon} {task_display}任务{status_text}",
            "",
            f"- **账号**: {username} (`{account.uid}`)",
            f"- **任务类型**: {task_display}",
            f"- **结果**: {message}",
        ]
        if success and exp_gained > 0:
            lines.append(f"- **获得经验**: +{exp_gained}")
        if account.coins is not None and account.coins >= 0:
            lines.append(f"- **当前硬币**: {account.coins}")

        body = "\n".join(lines)
        await self.send(account.uid, f"task_{task_type}", body)

    async def send_daily_summary(
        self,
        account: Account,
        logs: list[TaskLog],
    ) -> None:
        """如果 notify_daily_summary 为 true，发送每日汇总。"""
        cfg = await self._load_config()
        if not cfg["notify_daily_summary"]:
            return

        total = len(logs)
        success_count = sum(1 for l in logs if l.status == "success")
        failed_count = sum(1 for l in logs if l.status == "failed")
        skipped_count = sum(1 for l in logs if l.status == "skipped")
        total_exp = sum(l.exp_gained for l in logs)

        task_stats: dict[str, dict[str, int]] = {}
        for l in logs:
            if l.task_type not in task_stats:
                task_stats[l.task_type] = {"success": 0, "failed": 0, "skipped": 0, "exp": 0}
            if l.status in task_stats[l.task_type]:
                task_stats[l.task_type][l.status] += 1
            task_stats[l.task_type]["exp"] += l.exp_gained

        username = account.username or f"UID:{account.uid}"
        today = datetime.now().strftime("%Y-%m-%d")
        task_names = {
            "coin": "投币",
            "watch": "观看",
            "share": "分享",
            "live_sign": "直播签到",
            "silver2coin": "银瓜子换币",
        }

        lines = [
            f"## 📊 每日汇总 {today}",
            "",
            f"**账号**: {username} (`{account.uid}`)",
            f"**等级**: Lv{account.level} | **经验**: {account.current_exp}/{account.next_level_exp}",
            f"**硬币**: {account.coins}",
            "",
            "### 任务统计",
            f"- 总执行: {total} 次",
            f"- ✅ 成功: {success_count}",
            f"- ❌ 失败: {failed_count}",
            f"- ⏭️ 跳过: {skipped_count}",
            f"- **今日获得经验**: +{total_exp}",
        ]

        if task_stats:
            lines.append("")
            lines.append("### 各任务详情")
            for task_type, stats in task_stats.items():
                name = task_names.get(task_type, task_type)
                lines.append(
                    f"- {name}: ✅{stats['success']} ❌{stats['failed']} "
                    f"⏭️{stats['skipped']} +{stats['exp']}exp"
                )

        body = "\n".join(lines)
        await self.send(account.uid, "daily_summary", body)

    async def send_cookie_warning(
        self,
        account: Account,
        days_left: int,
    ) -> None:
        """Cookie 过期预警：urgent，不受免打扰限制。"""
        cfg = await self._load_config()
        if not cfg["notify_cookie_warning"]:
            return

        username = account.username or f"UID:{account.uid}"
        body = f"【{username}】Cookie 将在 {days_left} 天后过期，建议重新扫码登录"
        await self.send(account.uid, "cookie_warning", body, is_urgent=True)

    async def send_cookie_expired(
        self,
        account: Account,
    ) -> None:
        """Cookie 已失效告警：urgent，不受免打扰限制（0.2.0）。"""
        cfg = await self._load_config()
        if not cfg["notify_cookie_warning"]:
            return

        username = account.username or f"UID:{account.uid}"
        body = (
            f"【{username}】Cookie 已失效，任务将无法执行，"
            f"请尽快到面板重新扫码登录"
        )
        await self.send(account.uid, "cookie_expired", body, is_urgent=True)

    async def send_risk_alert(
        self,
        account: Account,
        task_type: str,
        fail_count: int,
    ) -> None:
        """风控/连续失败告警：urgent，不受免打扰限制。
        默认开启（notify_risk_alert 没关就发）。"""
        cfg = await self._load_config()
        if not cfg["notify_risk_alert"]:
            return

        task_names = {
            "coin": "投币",
            "watch": "观看",
            "share": "分享",
            "live_sign": "直播签到",
            "silver2coin": "银瓜子换币",
        }
        task_display = task_names.get(task_type, task_type)
        username = account.username or f"UID:{account.uid}"
        body = (
            f"【{username}】{task_display} 任务连续失败 {fail_count} 次，"
            f"已自动暂停，请检查账号状态"
        )
        await self.send(account.uid, "risk_alert", body, is_urgent=True)


# ============== 辅助函数 ==============


def _in_dnd_window(current: str, start: str, end: str) -> bool:
    """判断当前时间是否在免打扰时段内（支持跨午夜，如 23:00-08:00）。"""
    try:
        current_min = _time_to_minutes(current)
        start_min = _time_to_minutes(start)
        end_min = _time_to_minutes(end)

        if start_min <= end_min:
            return start_min <= current_min < end_min
        return current_min >= start_min or current_min < end_min
    except (ValueError, TypeError):
        return False


def _time_to_minutes(time_str: str) -> int:
    """HH:MM → 分钟数。"""
    parts = str(time_str).strip().split(":")
    if len(parts) != 2:
        raise ValueError(f"无效时间格式: {time_str}")
    return int(parts[0]) * 60 + int(parts[1])
