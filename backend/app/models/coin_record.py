"""投币记录模型：每次投币的明细。"""

from datetime import datetime

from sqlalchemy import BigInteger, DateTime, ForeignKey, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class CoinRecord(Base):
    """投币历史：account × bvid。"""

    __tablename__ = "coin_records"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    account_uid: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("accounts.uid", ondelete="CASCADE"), index=True, nullable=False
    )
    bvid: Mapped[str] = mapped_column(String(32), index=True, nullable=False)
    title: Mapped[str | None] = mapped_column(String(255), nullable=True)
    owner_uid: Mapped[int] = mapped_column(BigInteger, nullable=False, comment="UP 主 UID")
    owner_name: Mapped[str | None] = mapped_column(String(128), nullable=True)

    coin_count: Mapped[int] = mapped_column(Integer, default=1, nullable=False)

    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), nullable=False
    )

    account = relationship("Account", back_populates="coin_records")

    def __repr__(self) -> str:  # pragma: no cover
        return f"<CoinRecord id={self.id} bvid={self.bvid!r} coins={self.coin_count}>"
