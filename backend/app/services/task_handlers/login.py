"""登录任务：验证 cookie 有效性并刷新账号缓存。"""

from __future__ import annotations

from typing import Any

from app.services.task_handlers.base import BaseTaskHandler, TaskResult


class LoginHandler(BaseTaskHandler):
    """登录任务处理器：仅做 pre_check，验证 cookie 有效。"""

    task_type: str = "login"

    async def execute(self, config: dict[str, Any]) -> TaskResult:
        ok: bool = await self.pre_check()
        if ok:
            return TaskResult(
                success=True,
                message="登录成功",
                exp_gained=5,
                detail={"uid": self.account.uid, "username": self.account.username},
            )
        return TaskResult(
            success=False,
            message="登录失败：cookie 无效或已过期",
            exp_gained=0,
        )
