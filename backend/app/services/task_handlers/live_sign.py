"""直播签到任务。"""

from __future__ import annotations

from typing import Any

from loguru import logger

from app.exceptions import BiliAPIException, TaskExecuteException
from app.services.task_handlers.base import BaseTaskHandler, TaskResult


class LiveSignHandler(BaseTaskHandler):
    """直播签到任务处理器。"""

    task_type: str = "live_sign"

    async def execute(self, config: dict[str, Any]) -> TaskResult:
        if self.client is None:
            await self.init_client()
        assert self.client is not None

        try:
            data = await self.client.live_sign()
        except BiliAPIException as exc:
            logger.warning(f"直播签到失败 uid={self.account.uid}: {exc}")
            return TaskResult(
                success=False,
                message=f"直播签到失败: {exc}",
                exp_gained=0,
            )

        return TaskResult(
            success=True,
            message="直播签到完成",
            exp_gained=0,
            detail=data or {},
        )
