import json
from datetime import UTC, datetime, timedelta

from sqlalchemy.orm import Session

from app.core.logging import get_logger
from app.core.security import generate_interview_token
from app.models.interview import InterviewResult, InterviewSession

logger = get_logger(__name__)

SESSION_TTL_DAYS = 7


def _now() -> datetime:
    return datetime.now(UTC)


def _as_utc(dt: datetime) -> datetime:
    """Ensure a datetime is timezone-aware (SQLite returns naive datetimes)."""
    if dt.tzinfo is None:
        return dt.replace(tzinfo=UTC)
    return dt


def create_session(
    db: Session, *, candidate_name: str, candidate_email: str, job_title: str, job_description: str
) -> InterviewSession:
    token = generate_interview_token()
    session = InterviewSession(
        token=token,
        candidate_name=candidate_name,
        candidate_email=candidate_email,
        job_title=job_title,
        job_description=job_description,
        used=False,
        expires_at=_now() + timedelta(days=SESSION_TTL_DAYS),
    )
    db.add(session)
    db.commit()
    db.refresh(session)
    logger.info("Created interview session token=%s for %s", token[:8] + "...", candidate_email)
    return session


def get_session(db: Session, token: str) -> InterviewSession | None:
    return db.get(InterviewSession, token)


def mark_session_used(db: Session, token: str) -> None:
    session = db.get(InterviewSession, token)
    if session:
        session.used = True
        db.commit()


def save_result(
    db: Session,
    *,
    token: str,
    candidate_name: str,
    candidate_email: str,
    job_title: str,
    questions: list,
    answers: list,
    scores: list,
    overall_score: float,
    summary: str,
    strengths: str,
    red_flags: str,
    recommendation: str,
) -> InterviewResult:
    result = InterviewResult(
        token=token,
        candidate_name=candidate_name,
        candidate_email=candidate_email,
        job_title=job_title,
        questions_json=json.dumps(questions),
        answers_json=json.dumps(answers),
        scores_json=json.dumps(scores),
        overall_score=overall_score,
        summary=summary,
        strengths=strengths,
        red_flags=red_flags,
        recommendation=recommendation,
        completed_at=_now(),
    )
    db.add(result)
    db.commit()
    db.refresh(result)
    return result


def list_results(db: Session) -> list[InterviewResult]:
    return db.query(InterviewResult).order_by(InterviewResult.completed_at.desc()).all()


def get_result(db: Session, result_id: int) -> InterviewResult | None:
    return db.get(InterviewResult, result_id)


def is_session_valid(session: InterviewSession) -> tuple[bool, str]:
    """Returns (is_valid, reason). Use in route handlers."""
    if session.used:
        return False, "This interview link has already been used."
    if _as_utc(session.expires_at) < _now():
        return False, "This interview link has expired."
    return True, ""
