from datetime import datetime, timezone
from sqlalchemy import Integer, String, Boolean, DateTime, JSON, ForeignKey, func
from sqlalchemy.orm import Mapped, mapped_column
from app.database import Base


def _utcnow() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


class Question(Base):
    __tablename__ = "questions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    title: Mapped[str] = mapped_column(String, nullable=False)
    description: Mapped[str] = mapped_column(String, nullable=False)
    difficulty: Mapped[str] = mapped_column(String, nullable=False)  # easy|medium|hard
    constraints: Mapped[str | None] = mapped_column(String, nullable=True)
    sample_input: Mapped[str | None] = mapped_column(String, nullable=True)
    sample_output: Mapped[str | None] = mapped_column(String, nullable=True)
    test_cases: Mapped[list | None] = mapped_column(JSON, nullable=True)
    is_published: Mapped[bool] = mapped_column(Boolean, default=False)
    created_by: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("users.id"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=_utcnow
    )
