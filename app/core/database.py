from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from app.core.config import settings

# 비동기 DB 엔진 생성
engine = create_async_engine(
    settings.database_url,
    echo=settings.debug,  # debug=True 이면 SQL 쿼리 로그 출력
)

# 세션 팩토리 (요청마다 세션을 하나씩 만들어서 사용)
AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


# 모든 ORM 모델이 상속받는 Base 클래스
class Base(DeclarativeBase):
    pass


async def init_db() -> None:
    """앱 시작 시 테이블 자동 생성"""
    # 모델을 import해야 Base.metadata에 등록됨
    from app.models import chat, document  # noqa: F401

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def get_db():
    """FastAPI 의존성 주입용 DB 세션 제공"""
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()
