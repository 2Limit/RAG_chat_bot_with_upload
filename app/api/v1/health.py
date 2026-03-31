from fastapi import APIRouter
from app.core.config import settings

router = APIRouter()


@router.get("/health")
async def health_check():
    """서버 상태 확인용 엔드포인트 — 브라우저에서 바로 확인 가능"""
    return {
        "status": "ok",
        "app": settings.app_name,
        "version": settings.app_version,
    }
