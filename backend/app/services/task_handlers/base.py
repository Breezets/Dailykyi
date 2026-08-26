"""任务处理器基类：抽象接口与通用客户端初始化、预检逻辑。"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from loguru import logger
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.exceptions import BiliAPIException
from app.models.account import Account
from app.services.bili_api import BiliClient


class TaskResult(BaseModel):
    """任务执行结果。"""

    success: bool
    message: str
    detail: dict[str, Any] = Field(default_factory=dict)
    exp_gained: int = 0


class BaseTaskHandler(ABC):
    """任务处理器抽象基类。"""

    task_type: str = ""

    def __init__(self, account: Account, db: AsyncSession) -> None:
        self.account: Account = account
        self.db: AsyncSession = db
        self.client: BiliClient | None = None

    async def init_client(self) -> BiliClient:
        """从 account.cookie_encrypted 解密后创建 BiliClient。"""
        from app.deps import decrypt_cookie

        cookies: str = decrypt_cookie(self.account.cookie_encrypted or "")
        self.client = BiliClient(cookies=cookies)
        return self.client

    async def pre_check(self) -> bool:
        """调用 nav 接口验证 cookie 有效性，并刷新账号缓存字段。"""
        if self.client is None:
            await self.init_client()
        assert self.client is not None

        try:
            info = await self.client.get_user_info()
        except BiliAPIException as exc:
            logger.warning(f"pre_check 失败 uid={self.account.uid}: {exc}")
            return False

        # 更新账号缓存字段
        self.account.username = info.get("uname") or self.account.username
        self.account.avatar_url = info.get("face") or self.account.avatar_url

        def _safe_int(val: Any) -> int:
            """安全转 int，处理满级账号 next_exp='--' 等非数字值。"""
            try:
                return int(val)
            except (ValueError, TypeError):
                return 0

        self.account.coins = _safe_int(info.get("money", 0))

        level_info = info.get("level_info") or {}
        self.account.level = _safe_int(level_info.get("current_level", 0))
        self.account.current_exp = _safe_int(level_info.get("current_exp", 0))
        self.account.next_level_exp = _safe_int(level_info.get("next_exp", 0))

        await self.db.commit()
        logger.debug(
            f"pre_check ok uid={self.account.uid} "
            f"name={self.account.username} level={self.account.level}"
        )
        return True

    @abstractmethod
    async def execute(self, config: dict[str, Any]) -> TaskResult:
        """执行任务，子类必须实现。"""
        raise NotImplementedError
