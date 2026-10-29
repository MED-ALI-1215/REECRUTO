from datetime import UTC, datetime, timedelta

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


def _cost(prompt_tokens: int, completion_tokens: int) -> float:
    from app.core.config import get_settings

    settings = get_settings()
    return round(
        prompt_tokens / 1e6 * settings.GROQ_PRICE_INPUT_PER_M
        + completion_tokens / 1e6 * settings.GROQ_PRICE_OUTPUT_PER_M,
        6,
    )


def get_stats(db: Session) -> list[dict]:
    """
    Per-service summary of AI calls (all time).
    Exposed via GET /api/admin/ai-stats.
    """
    return get_usage(db)["by_service"]


def get_usage(db: Session, days: int | None = None) -> dict:
    """
    Token usage and estimated cost, overall, per service and per day.
    `days=None` (or 0) means all time. Exposed via GET /api/admin/usage.
    """
    from sqlalchemy import Integer, func

    since = datetime.now(UTC) - timedelta(days=days) if days else None

    def scoped(query):
        return query.filter(AICall.created_at >= since) if since else query

    failures = func.sum((AICall.success.is_(False)).cast(Integer))
    by_service_rows = scoped(
        db.query(
            AICall.service,
            func.count(AICall.id),
            func.coalesce(func.sum(AICall.prompt_tokens), 0),
            func.coalesce(func.sum(AICall.completion_tokens), 0),
            func.avg(AICall.latency_ms),
            failures,
        )
    ).group_by(AICall.service)

    by_service = []
    for service, calls, prompt, completion, latency, failed in by_service_rows.all():
        prompt, completion = int(prompt), int(completion)
        cost = _cost(prompt, completion)
        by_service.append(
            {
                "service": service,
                "total_calls": calls,
                "prompt_tokens": prompt,
                "completion_tokens": completion,
                "total_tokens": prompt + completion,
                "avg_tokens_per_call": round((prompt + completion) / calls) if calls else 0,
                "estimated_cost_usd": cost,
                "avg_cost_per_call_usd": round(cost / calls, 6) if calls else 0.0,
                "avg_latency_ms": round(latency or 0, 1),
                "failures": int(failed or 0),
            }
        )
    by_service.sort(key=lambda s: s["total_tokens"], reverse=True)

    day = func.date(AICall.created_at)
    by_day = [
        {
            "date": str(d),
            "calls": calls,
            "prompt_tokens": int(prompt),
            "completion_tokens": int(completion),
            "estimated_cost_usd": _cost(int(prompt), int(completion)),
        }
        for d, calls, prompt, completion in scoped(
            db.query(
                day,
                func.count(AICall.id),
                func.coalesce(func.sum(AICall.prompt_tokens), 0),
                func.coalesce(func.sum(AICall.completion_tokens), 0),
            )
        )
        .group_by(day)
        .order_by(day)
        .all()
    ]

    prompt_total = sum(s["prompt_tokens"] for s in by_service)
    completion_total = sum(s["completion_tokens"] for s in by_service)
    calls_total = sum(s["total_calls"] for s in by_service)
    return {
        "days": days or None,
        "totals": {
            "calls": calls_total,
            "failures": sum(s["failures"] for s in by_service),
            "prompt_tokens": prompt_total,
            "completion_tokens": completion_total,
            "total_tokens": prompt_total + completion_total,
            "estimated_cost_usd": _cost(prompt_total, completion_total),
        },
        "by_service": by_service,
        "by_day": by_day,
    }
