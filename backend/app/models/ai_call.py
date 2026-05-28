from datetime import datetime, timezone
from sqlalchemy import String, Text, Float, Boolean, DateTime, Integer
from sqlalchemy.orm import Mapped, mapped_column

from app.db.session import Base


class AICall(Base):
    """
    One row per Groq API call.
    Gives visibility into cost (tokens), latency, and failure rate
    without any external observability tool.
    """
    __tablename__ = "ai_calls"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
    )
    service: Mapped[str] = mapped_column(String(64))          # cv_extraction, answer_scoring, etc.
    model: Mapped[str] = mapped_column(String(128))
    prompt_version: Mapped[str] = mapped_column(String(64))   # e.g. "cv_extraction_v1"
    prompt_tokens: Mapped[int] = mapped_column(Integer, default=0)
    completion_tokens: Mapped[int] = mapped_column(Integer, default=0)
    latency_ms: Mapped[float] = mapped_column(Float, default=0.0)
    success: Mapped[bool] = mapped_column(Boolean, default=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)

    def __repr__(self) -> str:
        return (
            f"<AICall id={self.id} service={self.service!r} "
            f"success={self.success} latency_ms={self.latency_ms:.0f}>"
        )
