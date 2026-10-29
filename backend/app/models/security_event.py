from datetime import UTC, datetime

from sqlalchemy import DateTime, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.session import Base


class SecurityEvent(Base):
    """
    One row per suspected prompt-injection attempt (in a CV or an interview answer).
    The input is neutralised automatically; this table is what the recruiter reviews.
    """

    __tablename__ = "security_events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC)
    )
    source: Mapped[str] = mapped_column(String(32))  # "cv" | "interview_answer"
    detector: Mapped[str] = mapped_column(String(16))  # "rules" | "llm" | "rules+llm"
    reasons: Mapped[str] = mapped_column(Text)  # JSON list of human-readable reasons
    excerpt: Mapped[str] = mapped_column(Text)  # suspicious snippet, truncated
    candidate_id: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    candidate_name: Mapped[str | None] = mapped_column(String(256), nullable=True)
    session_token: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    question_index: Mapped[int | None] = mapped_column(Integer, nullable=True)
