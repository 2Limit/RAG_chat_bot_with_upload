from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

from app.core.config import settings
from app.core.database import init_db
from app.api.router import api_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    """앱 시작/종료 시 실행되는 이벤트 핸들러"""
    # 시작 시: DB 테이블 자동 생성
    from pathlib import Path
    from app.core.auth import validate_auth_config
    validate_auth_config()
    Path(settings.raw_path).mkdir(parents=True, exist_ok=True, mode=0o700)
    await init_db()
    print(f"✅ {settings.app_name} v{settings.app_version} 시작")
    print(f"📖 API 문서: http://localhost:8000/docs")
    yield
    # 종료 시: 필요한 정리 작업
    print("🛑 서버 종료")


app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description="RAG 기반 문서 QA 챗봇 API",
    lifespan=lifespan,
)

from app.core.upload_guard import UploadGuard
app.add_middleware(UploadGuard)

# Same-origin UI only. Do not enable wildcard credentialed CORS.

# 전역 예외 핸들러 — 모든 500 에러를 JSON으로 반환
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error"},
    )


@app.middleware("http")
async def security_headers(request, call_next):
    response = await call_next(request)
    response.headers["Cache-Control"] = "no-store"
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "no-referrer"
    return response

# API 라우터 등록
app.include_router(api_router)

# 프론트엔드 정적 파일 서빙
app.mount("/", StaticFiles(directory="frontend", html=True), name="frontend")
