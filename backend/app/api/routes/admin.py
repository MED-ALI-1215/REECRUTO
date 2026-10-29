import json

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.api.dependencies import require_auth
from app.db.session import get_db
from app.repositories import security_repo
from app.repositories.ai_call_repo import get_stats, get_usage

router = APIRouter(prefix="/admin", tags=["admin"])


@router.get("/ai-stats")
def ai_stats(db: Session = Depends(get_db), _: str = Depends(require_auth)):
    """
    Returns per-service AI call statistics:
    total calls, total tokens consumed, avg latency, failure count.
    """
    return get_stats(db)


@router.get("/usage")
def usage(
    days: int = Query(30, ge=0, le=3650, description="Period in days, 0 = all time"),
    db: Session = Depends(get_db),
    _: str = Depends(require_auth),
):
    """LLM token usage and estimated cost: totals, per service and per day."""
    return get_usage(db, days or None)


@router.get("/security-events")
def security_events(
    limit: int = 200, db: Session = Depends(get_db), _: str = Depends(require_auth)
):
    """Suspected prompt-injection attempts (CVs and interview answers), newest first."""
    return [
        {
            "id": e.id,
            "created_at": e.created_at,
            "source": e.source,
            "detector": e.detector,
            "reasons": json.loads(e.reasons or "[]"),
            "excerpt": e.excerpt,
            "candidate_id": e.candidate_id,
            "candidate_name": e.candidate_name,
            "session_token": (e.session_token or "")[:8] or None,
            "question_index": e.question_index,
        }
        for e in security_repo.list_events(db, limit=min(limit, 1000))
    ]
