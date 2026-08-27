"""数据库异步连接、会话与基类。"""

from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.config import DATA_DIR, settings
from sqlalchemy.orm import DeclarativeBase

engine = create_async_engine(
    settings.DATABASE_URL,
    echo=settings.DEBUG,
    connect_args={"check_same_thread": False},
)

AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,
)


class Base(DeclarativeBase):
    """所有 ORM 模型的声明基类。"""

    pass


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI 依赖：每请求注入一个 AsyncSession。"""
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()


async def _ensure_account_columns() -> None:
    """轻量迁移：为已存在的 accounts 表补充 0.2.0 新增字段（不破坏已有数据）。

    针对 SQLite：用 PRAGMA table_info 检查列是否存在，缺失则 ALTER TABLE 补列。
    """
    from sqlalchemy import text

    async with engine.connect() as conn:
        table_exists = await conn.scalar(
            text(
                "SELECT name FROM sqlite_master "
                "WHERE type='table' AND name='accounts'"
            )
        )
        if not table_exists:
            return

        cols = await conn.execute(text("PRAGMA table_info(accounts)"))
        existing = {row[1] for row in cols.fetchall()}

        if "cookie_status" not in existing:
            await conn.execute(
                text(
                    "ALTER TABLE accounts ADD COLUMN "
                    "cookie_status VARCHAR(16) NOT NULL DEFAULT 'unknown'"
                )
            )
        if "cookie_checked_at" not in existing:
            await conn.execute(
                text("ALTER TABLE accounts ADD COLUMN cookie_checked_at DATETIME")
            )
        await conn.commit()


async def init_db() -> None:
    """开发期建表；生产应使用 Alembic 迁移。"""
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    import app.models  # noqa: F401  确保所有模型注册到 metadata

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    # 兼容旧库：补 0.2.0 新增列
    await _ensure_account_columns()
