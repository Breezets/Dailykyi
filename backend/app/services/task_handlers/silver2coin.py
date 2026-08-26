"""银瓜子兑换硬币任务。"""

from __future__ import annotations

from typing import Any

from loguru import logger

from app.exceptions import BiliAPIException, TaskExecuteException
from app.services.task_handlers.base import BaseTaskHandler, TaskResult


class Silver2CoinHandler(BaseTaskHandler):
    """银瓜子兑硬币处理器：当银瓜子 >= 700 时执行兑换。"""

    SILVER_THRESHOLD: int = 700

    async def execute(self, config: dict[str, Any]) -> TaskResult:
        if self.client is None:
            await self.init_client()
        assert self.client is not None

        # 获取用户信息（含钱包）
        try:
            info = await self.client.get_user_info()
        except BiliAPIException as exc:
            raise TaskExecuteException(f"获取用户信息失败: {exc}") from exc

        wallet = info.get("wallet") or {}
        silver: int = int(wallet.get("silver", 0) or 0)

        if silver < self.SILVER_THRESHOLD:
            return TaskResult(
                success=True,
                message=f"银瓜子不足 ({silver}/{self.SILVER_THRESHOLD})，跳过兑换",
                exp_gained=0,
                detail={"silver": silver, "threshold": self.SILVER_THRESHOLD},
            )

        try:
            data = await self.client.silver2coin(self.client.csrf)
        except BiliAPIException as exc:
            logger.warning(f"银瓜子兑换失败 uid={self.account.uid}: {exc}")
            return TaskResult(
                success=False,
                message=f"银瓜子兑换失败: {exc}",
                exp_gained=0,
            )

        return TaskResult(
            success=True,
            message="银瓜子兑换硬币完成",
            exp_gained=0,
            detail=data or {},
        )
