"""任务处理器基类：抽象接口与通用客户端初始化、预检逻辑。"""

from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import datetime
from typing import Any

from loguru import logger
from pydantic import BaseModel, Field
from sqlalchemy import select
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

        self._apply_nav_info(info)
        await self.db.commit()
        logger.debug(
            f"pre_check ok uid={self.account.uid} "
            f"name={self.account.username} level={self.account.level}"
        )
        return True

    def _apply_nav_info(self, info: dict[str, Any]) -> None:
        """把 nav/get_user_info 返回值写入 account 缓存字段。"""
        from app.models.account import Account  # noqa: F401

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

    async def refresh_exp_snapshot(self) -> int:
        """任务执行完成后调用：刷新 account.current_exp 并写一条 ExpSnapshot。

        返回值：与最近一条 ExpSnapshot 的 exp 差值（delta）。
          - delta > 0：本次执行真的获得了经验
          - delta = 0：本次没获得经验（可能别处已完成，B 站服务端去重）
          - delta < 0：异常情况（经验被减少），按 0 处理

        实现逻辑：
          1. 调 nav 接口拿最新 current_exp（绕过任务缓存的过期值）
          2. 查最近一条 ExpSnapshot 的 exp
          3. 写一条新 ExpSnapshot
          4. 计算 delta 返回
        """
        from app.models.exp_snapshot import ExpSnapshot

        if self.client is None:
            await self.init_client()
        assert self.client is not None

        # 1. 调 nav 接口刷新 account.current_exp
        try:
            info = await self.client.get_user_info()
            self._apply_nav_info(info)
        except BiliAPIException as exc:
            logger.warning(
                f"refresh_exp_snapshot 调 nav 失败 uid={self.account.uid}: {exc}"
            )
            return 0

        # 2. 查最近一条快照
        from sqlalchemy import select
        last_snap_result = await self.db.execute(
            select(ExpSnapshot)
            .where(ExpSnapshot.account_uid == self.account.uid)
            .order_by(ExpSnapshot.recorded_at.desc())
            .limit(1)
        )
        last_snap = last_snap_result.scalar_one_or_none()
        last_exp = int(last_snap.exp) if last_snap else 0

        # 3. 写新快照
        new_exp = int(self.account.current_exp or 0)
        snap = ExpSnapshot(
            account_uid=self.account.uid,
            exp=new_exp,
            level=int(self.account.level or 0),
            coins=int(self.account.coins or 0),
            recorded_at=datetime.now(),
        )
        self.db.add(snap)
        await self.db.commit()

        # 4. 计算 delta
        delta = max(0, new_exp - last_exp)
        logger.info(
            f"refresh_exp_snapshot uid={self.account.uid} "
            f"last={last_exp} new={new_exp} delta={delta}"
        )
        return delta

    @abstractmethod
    async def execute(self, config: dict[str, Any]) -> TaskResult:
        """执行任务，子类必须实现。"""
        raise NotImplementedError
