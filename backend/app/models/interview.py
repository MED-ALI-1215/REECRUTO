from datetime import UTC, datetime

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.session import Base


class InterviewSession(Base):
    """
    Created when recruiter sends an interview invite.
    Holds the one-time token used by the candidate to access their interview.
    """

    __tablename__ = "interview_sessions"

    token: Mapped[str] = mapped_column(String(64), primary_key=True)
    candidate_name: Mapped[str] = mapped_column(String(256))
    candidate_email: Mapped[str] = mapped_column(String(256))
    job_title: Mapped[str] = mapped_column(String(256))
    job_description: Mapped[str] = mapped_column(Text)
    used: Mapped[bool] = mapped_column(Boolean, default=False)

    # Links to the saved job / candidate (null for invites sent without them)
    job_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("jobs.id", ondelete="SET NULL"), nullable=True
    )
    candidate_id: Mapped[str | None] = mapped_column(
        String(64), ForeignKey("candidates.id", ondelete="SET NULL"), nullable=True
    )

    # Server-side interview state — never trusted from the browser.
    # questions_json: [{"text": ..., "kind": "job" | "personal"}], frozen when the interview starts
    # progress_json:  list aligned with questions: null | {answer, score, feedback, keywords, flagged}
    questions_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    progress_json: Mapped[str | None] = mapped_column(Text, nullable=True)

    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
    )

    result: Mapped["InterviewResult | None"] = relationship(
        "InterviewResult", back_populates="session", uselist=False
    )


class InterviewResult(Base):
    """
    Saved once the candidate completes their interview.
    All JSON blobs (questions, answers, scores) stored as Text.
    """

    __tablename__ = "interview_results"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    token: Mapped[str] = mapped_column(
        String(64), ForeignKey("interview_sessions.token"), unique=True
    )
    candidate_name: Mapped[str] = mapped_column(String(256))
    candidate_email: Mapped[str] = mapped_column(String(256))
    job_title: Mapped[str] = mapped_column(String(256))
    questions_json: Mapped[str] = mapped_column(Text)  # JSON list of strings
    answers_json: Mapped[str] = mapped_column(Text)  # JSON list of strings
    scores_json: Mapped[str] = mapped_column(Text)  # JSON list of {score, feedback, keywords}
    overall_score: Mapped[float] = mapped_column(Float)
    summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    strengths: Mapped[str | None] = mapped_column(Text, nullable=True)
    red_flags: Mapped[str | None] = mapped_column(Text, nullable=True)
    recommendation: Mapped[str | None] = mapped_column(String(64), nullable=True)
    completed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
    )

    session: Mapped["InterviewSession"] = relationship("InterviewSession", back_populates="result")
