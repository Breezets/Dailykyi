"""FastAPI 应用入口：日志、CORS、请求日志中间件、路由装配。"""

import sys
import time
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from loguru import logger

from app.config import LOG_DIR, settings
from app.database import init_db
from app.exceptions import register_exception_handlers
from app.routers import accounts, auth, dashboard, exp, health, logs, system, tasks
from app.services.scheduler import init_scheduler, shutdown_scheduler


def setup_logging() -> None:
    """Loguru 配置：控制台 + 文件（按天轮转，保留 7 天）。"""
    logger.remove()
    logger.add(
        sys.stderr,
        level=settings.LOG_LEVEL,
        format=(
            "<green>{time:YYYY-MM-DD HH:mm:ss}</green> | "
            "<level>{level: <8}</level> | "
            "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - "
            "<level>{message}</level>"
        ),
    )
    logger.add(
        LOG_DIR / "backend.log",
        level=settings.LOG_LEVEL,
        rotation="1 day",
        retention="7 days",
        encoding="utf-8",
        format=(
            "{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | "
            "{name}:{function}:{line} - {message}"
        ),
    )


@asynccontextmanager
async def lifespan(_app: FastAPI):
    """应用生命周期：配置日志、建表、调度、就绪。"""
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    setup_logging()
    logger.info(f"{settings.APP_NAME} v{settings.APP_VERSION} 启动中...")
    await init_db()
    await init_scheduler()
    logger.info(f"{settings.APP_NAME} 启动完成")
    yield
    logger.info(f"{settings.APP_NAME} 正在关闭")
    await shutdown_scheduler()


app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    debug=settings.DEBUG,
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def request_logging(request: Request, call_next):
    """记录每个请求的方法、路径、状态码与耗时。"""
    start = time.perf_counter()
    response = await call_next(request)
    duration_ms = (time.perf_counter() - start) * 1000
    logger.info(
        f"{request.method} {request.url.path} "
        f"-> {response.status_code} ({duration_ms:.1f}ms)"
    )
    return response


register_exception_handlers(app)

app.include_router(health.router, prefix="/api/v1", tags=["health"])
app.include_router(auth.router, prefix="/api/v1/auth", tags=["auth"])
app.include_router(tasks.router, prefix="/api/v1/tasks", tags=["tasks"])
app.include_router(dashboard.router, prefix="/api/v1/dashboard", tags=["dashboard"])
app.include_router(accounts.router, prefix="/api/v1/accounts", tags=["accounts"])
app.include_router(logs.router, prefix="/api/v1/logs", tags=["logs"])
app.include_router(exp.router, prefix="/api/v1/exp", tags=["exp"])
app.include_router(system.router, prefix="/api/v1/system", tags=["system"])


@app.get("/")
async def root():
    return {"app": settings.APP_NAME, "version": settings.APP_VERSION}
