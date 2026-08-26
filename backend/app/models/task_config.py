"""任务配置模型：account × task_type 的开关、参数、调度。"""

from datetime import datetime
from typing import Any

from sqlalchemy import JSON, Boolean, DateTime, ForeignKey, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy import BigInteger

from app.database import Base


class TaskConfig(Base):
    """单账号单任务配置。"""

    __tablename__ = "task_configs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    account_uid: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("accounts.uid", ondelete="CASCADE"), index=True, nullable=False
    )
    task_type: Mapped[str] = mapped_column(
        String(32), index=True, nullable=False,
        comment="watch/coin/share/live_sign/silver2coin",
    )
    enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    config: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)

    schedule_mode: Mapped[str] = mapped_column(
        String(16), default="random", nullable=False, comment="random/fixed/interval"
    )
    schedule_config: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)

    max_retries: Mapped[int] = mapped_column(Integer, default=3, nullable=False)
    cooldown_minutes: Mapped[int] = mapped_column(Integer, default=10, nullable=False)

    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now(), nullable=False
    )

    account = relationship("Account", back_populates="task_configs")

    def __repr__(self) -> str:  # pragma: no cover
        return f"<TaskConfig id={self.id} type={self.task_type!r} enabled={self.enabled}>"
