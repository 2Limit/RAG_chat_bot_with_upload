from datetime import datetime
from sqlalchemy import String, Integer, DateTime
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class Document(Base):
    """업로드된 문서 메타데이터"""
    __tablename__ = "documents"
    __table_args__ = {"sqlite_autoincrement": True}  # Never recycle storage IDs

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    owner_id: Mapped[str] = mapped_column(String(64), index=True)
    filename: Mapped[str] = mapped_column(String(255))
    file_path: Mapped[str] = mapped_column(String(512))
    chunk_count: Mapped[int] = mapped_column(Integer, default=0)
    status: Mapped[str] = mapped_column(String(32), default="pending")
    # status: pending | processing | completed | failed
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
