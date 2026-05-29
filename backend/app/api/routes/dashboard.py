from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.dependencies import require_auth
from app.core.exceptions import CandidateNotFoundError
from app.core.logging import get_logger
from app.db.session import get_db
from app.repositories import interview_repo
from app.schemas.interview import InterviewResultOut
from app.services.email_service import (
    generate_acceptance_email,
    generate_rejection_email,
    send_email,
)

logger = get_logger(__name__)
router = APIRouter(prefix="/dashboard", tags=["dashboard"])


@router.get("/results", response_model=list[InterviewResultOut])
def list_results(db: Session = Depends(get_db), _: str = Depends(require_auth)):
    return interview_repo.list_results(db)


@router.post("/results/{result_id}/accept")
def accept_candidate(result_id: int, db: Session = Depends(get_db), _: str = Depends(require_auth)):
    result = interview_repo.get_result(db, result_id)
    if not result:
        raise CandidateNotFoundError(f"No interview result with id={result_id}")
    subject, html = generate_acceptance_email(result.candidate_name, result.job_title)
    send_email(result.candidate_email, subject, html)
    return {"status": "accepted", "email_sent_to": result.candidate_email}


@router.post("/results/{result_id}/reject")
def reject_candidate(result_id: int, db: Session = Depends(get_db), _: str = Depends(require_auth)):
    result = interview_repo.get_result(db, result_id)
    if not result:
        raise CandidateNotFoundError(f"No interview result with id={result_id}")
    subject, html = generate_rejection_email(result.candidate_name, result.job_title)
    send_email(result.candidate_email, subject, html)
    return {"status": "rejected", "email_sent_to": result.candidate_email}
