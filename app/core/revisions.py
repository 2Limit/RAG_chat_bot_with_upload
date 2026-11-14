"""SQLite transaction fence for deletion versus in-flight generated answers."""
from sqlalchemy import Integer, String, select
from sqlalchemy.dialects.sqlite import insert
from sqlalchemy.orm import Mapped, mapped_column
from app.core.database import Base


class OwnerRevision(Base):
    __tablename__ = "owner_revisions"
    owner_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    revision: Mapped[int] = mapped_column(Integer, default=0)


async def ensure_revision(db, owner_id):
    await db.execute(insert(OwnerRevision).values(owner_id=owner_id, revision=0)
                     .on_conflict_do_nothing(index_elements=["owner_id"]))
    await db.commit()


async def read_revision(db, owner_id):
    return await db.scalar(select(OwnerRevision.revision).where(OwnerRevision.owner_id == owner_id))
