from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.dependencies import require_auth
from app.db.session import get_db
from app.repositories.ai_call_repo import get_stats

router = APIRouter(prefix="/admin", tags=["admin"])


@router.get("/ai-stats")
def ai_stats(db: Session = Depends(get_db), _: str = Depends(require_auth)):
    """
    Returns per-service AI call statistics:
    total calls, total tokens consumed, avg latency, failure count.
    """
    return get_stats(db)
