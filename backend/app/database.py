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


async def init_db() -> None:
    """开发期建表；生产应使用 Alembic 迁移。"""
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    import app.models  # noqa: F401  确保所有模型注册到 metadata

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
