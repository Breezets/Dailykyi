"""经验快照模型：每 6 小时记录一次账号经验，用于精确计算每日经验增量。

为什么需要快照？
- 原方案用 TaskLog.exp_gained 之和算"今日经验"：1) 依赖任务执行虚报数值，曾因 bug 误报 +5；
  2) 任务未执行时段不会记录；3) 同一天多次执行会被重复累加。
- 用快照对比：取当前 current_exp 与 24 小时前最近的那条快照的 exp，差值即真实今日增量。
"""

from datetime import datetime

from sqlalchemy import BigInteger, DateTime, ForeignKey, Integer, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class ExpSnapshot(Base):
    """账号经验定期快照（每 6 小时由 scheduler 写一条）。"""

    __tablename__ = "exp_snapshots"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    account_uid: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("accounts.uid", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    exp: Mapped[int] = mapped_column(Integer, nullable=False, comment="快照时的 current_exp")
    level: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    coins: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    recorded_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.now, server_default=func.now(), nullable=False, index=True
    )

    account = relationship("Account", backref="exp_snapshots")

    def __repr__(self) -> str:  # pragma: no cover
        return f"<ExpSnapshot uid={self.account_uid} exp={self.exp} at={self.recorded_at}>"
