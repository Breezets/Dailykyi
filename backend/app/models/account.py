"""账号模型：B 站账号信息（扫码登录后落库）。"""

from datetime import datetime

from sqlalchemy import BigInteger, Boolean, DateTime, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Account(Base):
    """B 站账号：保存 uid、等级、硬币缓存与加密后的 cookies。"""

    __tablename__ = "accounts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    uid: Mapped[int] = mapped_column(BigInteger, unique=True, index=True, nullable=False, comment="B 站 UID")

    username: Mapped[str | None] = mapped_column(String(128), nullable=True, comment="B 站昵称")
    avatar_url: Mapped[str | None] = mapped_column(String(512), nullable=True)

    # 等级 / 经验 / 硬币（缓存字段，登录或任务时刷新）
    level: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    current_exp: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    next_level_exp: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    coins: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    # 加密后的 cookies
    cookie_encrypted: Mapped[str | None] = mapped_column(Text, nullable=True, comment="Fernet 加密")
    cookie_expires_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    # 状态
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    last_login_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now(), nullable=False
    )

    # 关系
    task_configs = relationship(
        "TaskConfig", back_populates="account", cascade="all, delete-orphan"
    )
    task_logs = relationship(
        "TaskLog", back_populates="account", cascade="all, delete-orphan"
    )
    coin_records = relationship(
        "CoinRecord", back_populates="account", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:  # pragma: no cover
        return f"<Account uid={self.uid} username={self.username!r}>"
