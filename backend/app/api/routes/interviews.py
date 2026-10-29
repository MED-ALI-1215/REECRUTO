from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.dependencies import require_auth
from app.core.config import get_settings
from app.core.exceptions import AppError
from app.core.logging import get_logger
from app.db.session import get_db
from app.models.interview import InterviewSession
from app.models.job import Job
from app.repositories import interview_repo
from app.repositories.interview_repo import is_session_valid
from app.schemas.interview import (
    AnswerIn,
    AnswerOut,
    InterviewCreateIn,
    InterviewResultOut,
    InterviewSessionOut,
    QuestionsOut,
)
from app.services import email_service, interview_flow

logger = get_logger(__name__)
router = APIRouter(prefix="/interviews", tags=["interviews"])


def _valid_session_or_error(db: Session, token: str) -> InterviewSession:
    session = interview_repo.get_session(db, token)
    if not session:
        raise HTTPException(status_code=404, detail="Interview session not found.")
    valid, reason = is_session_valid(session)
    if not valid:
        raise HTTPException(status_code=410, detail=reason)
    return session


@router.post("", response_model=InterviewSessionOut, status_code=status.HTTP_201_CREATED)
def create_interview(
    body: InterviewCreateIn, db: Session = Depends(get_db), _: str = Depends(require_auth)
):
    job = db.get(Job, body.job_id) if body.job_id else None
    if body.job_id and job is None:
        raise HTTPException(status_code=404, detail="Job not found.")
    job_title = body.job_title or (job.title if job else "")
    job_description = body.job_description or (job.description if job else "")
    if not job_title or not job_description:
        raise HTTPException(status_code=422, detail="Job title and description are required.")

    # Generate the job's shared questions now so every candidate gets the same ones.
    # If the AI is unavailable, they are generated when the first candidate starts.
    if job is not None:
        try:
            interview_flow.ensure_job_questions(db, job)
        except AppError as e:
            logger.warning("Could not pre-generate questions for job %s: %s", job.id, e)

    session = interview_repo.create_session(
        db,
        candidate_name=body.candidate_name,
        candidate_email=body.candidate_email,
        job_title=job_title,
        job_description=job_description,
        job_id=job.id if job else None,
        candidate_id=body.candidate_id,
    )
    interview_link = f"{get_settings().APP_BASE_URL}?token={session.token}"
    try:
        subject, html = email_service.generate_invite_email(
            body.candidate_name, job_title, interview_link
        )
        email_service.send_email(body.candidate_email, subject, html)
    except Exception as e:
        logger.error("Failed to send invite email to %s: %s", body.candidate_email, e)
    return session


@router.get("/{token}", response_model=InterviewSessionOut)
def get_session(token: str, db: Session = Depends(get_db)):
    return _valid_session_or_error(db, token)


@router.post("/{token}/questions", response_model=QuestionsOut)
def get_questions(token: str, db: Session = Depends(get_db)):
    """Questions are frozen on the first call; later calls return the same ones."""
    session = _valid_session_or_error(db, token)
    questions = interview_flow.ensure_session_questions(db, session)
    progress = [
        {"score": p["score"], "feedback": p["feedback"], "keywords": p["keywords"]} if p else None
        for p in interview_repo.get_progress(session)
    ]
    return QuestionsOut(
        questions=[q["text"] for q in questions],
        kinds=[q["kind"] for q in questions],
        progress=progress,
    )


@router.post("/{token}/score", response_model=AnswerOut)
def score_answer(token: str, body: AnswerIn, db: Session = Depends(get_db)):
    """Score one answer (once per question). The score is stored on the server."""
    session = _valid_session_or_error(db, token)
    max_chars = get_settings().MAX_ANSWER_CHARS
    if len(body.answer) > max_chars:
        raise HTTPException(
            status_code=422, detail=f"Answers are limited to {max_chars} characters."
        )
    return interview_flow.answer_question(db, session, body.question_index, body.answer)


@router.post("/{token}/finish", response_model=InterviewResultOut)
def finish_interview(token: str, db: Session = Depends(get_db)):
    """Build the result from the answers stored on the server (the request body is ignored)."""
    session = _valid_session_or_error(db, token)
    return interview_flow.finish(db, session)
