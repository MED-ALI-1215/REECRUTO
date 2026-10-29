from datetime import UTC, datetime

from sqlalchemy import (
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
    true,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.session import Base


def _now() -> datetime:
    return datetime.now(UTC)


class Job(Base):
    """A saved job description with the skills extracted from it (once, by the LLM)."""

    __tablename__ = "jobs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    title: Mapped[str] = mapped_column(String(256))
    description: Mapped[str] = mapped_column(Text)

    # JSON lists of normalised skill names
    required_skills_json: Mapped[str] = mapped_column(Text, default="[]")
    nice_skills_json: Mapped[str] = mapped_column(Text, default="[]")
    soft_skills_json: Mapped[str] = mapped_column(Text, default="[]")

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)

    matches: Mapped[list["JobMatch"]] = relationship(
        "JobMatch", back_populates="job", cascade="all, delete-orphan"
    )


class JobMatch(Base):
    """The score of one candidate for one job (one row per pair)."""

    __tablename__ = "job_matches"
    __table_args__ = (UniqueConstraint("job_id", "candidate_id", name="uq_job_candidate"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    job_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("jobs.id", ondelete="CASCADE"), index=True
    )
    candidate_id: Mapped[str] = mapped_column(
        String(64), ForeignKey("candidates.id", ondelete="CASCADE"), index=True
    )
    score: Mapped[float] = mapped_column(Float)
    required_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    nice_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    soft_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    breakdown_json: Mapped[str] = mapped_column(Text, default="[]")  # per-skill evidence
    reasoning: Mapped[str | None] = mapped_column(Text, nullable=True)
    legacy_profile: Mapped[bool] = mapped_column(default=False)
    # False = not pre-selected by ChromaDB (stage 1) — kept so it isn't "pending" again
    retrieved: Mapped[bool] = mapped_column(default=True, server_default=true())
    scoring_version: Mapped[str] = mapped_column(String(32))
    matched_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)

    job: Mapped["Job"] = relationship("Job", back_populates="matches")
