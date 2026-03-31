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

# CORS 설정 (프론트엔드에서 API 호출 허용)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 개발 중에는 모두 허용, 배포 시 도메인 지정
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 전역 예외 핸들러 — 모든 500 에러를 JSON으로 반환
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    return JSONResponse(
        status_code=500,
        content={"detail": f"서버 오류: {type(exc).__name__}: {str(exc)}"},
    )


# API 라우터 등록
app.include_router(api_router)

# 프론트엔드 정적 파일 서빙
app.mount("/", StaticFiles(directory="frontend", html=True), name="frontend")
