"""任务执行日志模型。"""

from datetime import datetime
from typing import Any

from sqlalchemy import JSON, BigInteger, DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


def _localnow() -> datetime:
    """本地时区当前时间（用户在 Asia/Hong_Kong UTC+8）。

    SQLite 的 func.now() 返回 UTC 时间导致日志显示晚 8 小时，
    Python 层显式传本地时间可绕过此问题。
    """
    return datetime.now()


class TaskLog(Base):
    """单次任务执行记录。"""

    __tablename__ = "task_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    account_uid: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("accounts.uid", ondelete="CASCADE"), index=True, nullable=False
    )
    task_type: Mapped[str] = mapped_column(String(32), index=True, nullable=False)
    status: Mapped[str] = mapped_column(
        String(16), default="pending", nullable=False,
        comment="pending/running/success/failed/skipped",
    )
    message: Mapped[str | None] = mapped_column(Text, nullable=True)
    detail: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True, comment="JSON 详情")

    exp_gained: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    started_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=_localnow, server_default=func.now(), nullable=False, index=True
    )

    account = relationship("Account", back_populates="task_logs")

    def __repr__(self) -> str:  # pragma: no cover
        return f"<TaskLog id={self.id} type={self.task_type!r} status={self.status!r}>"
