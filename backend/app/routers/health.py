"""健康检查路由。"""

from fastapi import APIRouter

from app.config import settings

router = APIRouter()


@router.get("/health")
async def health():
    """Liveness 探针。"""
    return {"status": "ok", "version": settings.APP_VERSION}
