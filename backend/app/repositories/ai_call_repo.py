from datetime import UTC, datetime

from sqlalchemy import Integer, func
from sqlalchemy.orm import Session

from app.core.logging import get_logger
from app.models.ai_call import AICall

logger = get_logger(__name__)


def record_ai_call(
    db: Session,
    *,
    service: str,
    model: str,
    prompt_version: str,
    prompt_tokens: int,
    completion_tokens: int,
    latency_ms: float,
    success: bool,
    error_message: str | None = None,
) -> AICall:
    call = AICall(
        created_at=datetime.now(UTC),
        service=service,
        model=model,
        prompt_version=prompt_version,
        prompt_tokens=prompt_tokens,
        completion_tokens=completion_tokens,
        latency_ms=latency_ms,
        success=success,
        error_message=error_message,
    )
    try:
        db.add(call)
        db.commit()
        db.refresh(call)
    except Exception as e:
        # Never let observability break the main flow
        db.rollback()
        logger.warning("Failed to record AI call to DB: %s", e)
    return call


def get_stats(db: Session) -> dict:
    """
    Quick summary of AI call usage.
    Exposed via GET /api/admin/ai-stats.
    """
    rows = (
        db.query(
            AICall.service,
            func.count(AICall.id).label("total_calls"),
            func.sum(AICall.prompt_tokens).label("total_tokens"),
            func.avg(AICall.latency_ms).label("avg_latency_ms"),
            func.sum((AICall.success == False).cast(Integer)).label("failures"),  # noqa
        )
        .group_by(AICall.service)
        .all()
    )
    return [
        {
            "service": r.service,
            "total_calls": r.total_calls,
            "total_tokens": r.total_tokens or 0,
            "avg_latency_ms": round(r.avg_latency_ms or 0, 1),
            "failures": r.failures or 0,
        }
        for r in rows
    ]
