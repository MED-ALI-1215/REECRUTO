from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.dependencies import require_auth
from app.core.config import get_settings
from app.db.session import get_db
from app.repositories import interview_repo
from app.repositories.interview_repo import is_session_valid
from app.schemas.interview import AnswerIn, InterviewCreateIn, InterviewResultOut, InterviewSessionOut
from app.services import interview_service, email_service
from app.core.logging import get_logger

logger = get_logger(__name__)
router = APIRouter(prefix="/interviews", tags=["interviews"])


@router.post("", response_model=InterviewSessionOut, status_code=status.HTTP_201_CREATED)
def create_interview(body: InterviewCreateIn, db: Session = Depends(get_db), _: str = Depends(require_auth)):
    session = interview_repo.create_session(
        db,
        candidate_name=body.candidate_name,
        candidate_email=body.candidate_email,
        job_title=body.job_title,
        job_description=body.job_description,
    )
    settings = get_settings()
    interview_link = f"{settings.APP_BASE_URL}?token={session.token}"
    try:
        subject, html = email_service.generate_invite_email(body.candidate_name, body.job_title, interview_link)
        email_service.send_email(body.candidate_email, subject, html)
    except Exception as e:
        logger.error("Failed to send invite email to %s: %s", body.candidate_email, e)
    return session


@router.get("/{token}", response_model=InterviewSessionOut)
def get_session(token: str, db: Session = Depends(get_db)):
    session = interview_repo.get_session(db, token)
    if not session:
        raise HTTPException(status_code=404, detail="Interview session not found.")
    valid, reason = is_session_valid(session)
    if not valid:
        raise HTTPException(status_code=410, detail=reason)
    return session


@router.post("/{token}/questions")
def get_questions(token: str, db: Session = Depends(get_db)):
    session = interview_repo.get_session(db, token)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found.")
    valid, reason = is_session_valid(session)
    if not valid:
        raise HTTPException(status_code=410, detail=reason)
    questions = interview_service.generate_questions(session.job_title, session.job_description)
    return {"questions": questions}


@router.post("/{token}/score")
def score_answer(token: str, body: AnswerIn, db: Session = Depends(get_db)):
    session = interview_repo.get_session(db, token)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found.")
    result = interview_service.score_answer(body.question, body.answer, session.job_title, session.job_description)
    return result


@router.post("/{token}/finish", response_model=InterviewResultOut)
def finish_interview(token: str, body: dict, db: Session = Depends(get_db)):
    session = interview_repo.get_session(db, token)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found.")
    if session.used:
        raise HTTPException(status_code=410, detail="Already submitted.")

    questions = body.get("questions", [])
    answers = body.get("answers", [])
    scores = body.get("scores", [])

    try:
        report = interview_service.generate_final_report(
            session.candidate_name, session.job_title, questions, answers, scores
        )
    except Exception as e:
        logger.error("Final report generation failed: %s", e)
        raise HTTPException(status_code=502, detail="Report generation failed.")

    interview_repo.mark_session_used(db, token)
    result = interview_repo.save_result(
        db, token=token,
        candidate_name=session.candidate_name, candidate_email=session.candidate_email,
        job_title=session.job_title, questions=questions, answers=answers, scores=scores,
        overall_score=report["overall_score"], summary=report.get("summary", ""),
        strengths=report.get("strengths", ""), red_flags=report.get("red_flags", ""),
        recommendation=report.get("recommendation", "Maybe"),
    )
    return result
