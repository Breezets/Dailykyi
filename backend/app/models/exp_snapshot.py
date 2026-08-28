"""经验快照模型：每 6 小时记录一次账号经验，用于精确计算每日经验增量。

为什么需要快照？
- 原方案用 TaskLog.exp_gained 之和算"今日经验"：1) 依赖任务执行虚报数值，曾因 bug 误报 +5；
  2) 任务未执行时段不会记录；3) 同一天多次执行会被重复累加。
- 用快照对比：取当前 current_exp 与 24 小时前最近的那条快照的 exp，差值即真实今日增量。
"""

from datetime import datetime

from sqlalchemy import BigInteger, DateTime, ForeignKey, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class ExpSnapshot(Base):
    """账号经验定期快照。

    来源（source）：
      - task：任务执行后主动写（refresh_exp_snapshot）
      - passive：6 小时定时被动快照（_exp_snapshot_job，会调 B 站 nav 刷新）
      - manual：用户在首页点击「校验经验」主动触发
    """

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
    source: Mapped[str] = mapped_column(
        String(16), default="task", server_default="task",
        nullable=False, index=True,
        comment="task(任务执行)/passive(6h定时)/manual(手动校验)",
    )
    recorded_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.now, server_default=func.now(), nullable=False, index=True
    )

    account = relationship("Account", backref="exp_snapshots")

    def __repr__(self) -> str:  # pragma: no cover
        return f"<ExpSnapshot uid={self.account_uid} exp={self.exp} at={self.recorded_at}>"
