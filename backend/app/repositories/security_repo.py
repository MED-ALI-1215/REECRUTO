import json

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.logging import get_logger
from app.models.security_event import SecurityEvent

logger = get_logger(__name__)

MAX_EXCERPT = 500


def record_event(
    db: Session,
    *,
    source: str,
    detector: str,
    reasons: list[str],
    excerpt: str,
    candidate_id: str | None = None,
    candidate_name: str | None = None,
    session_token: str | None = None,
    question_index: int | None = None,
) -> SecurityEvent:
    event = SecurityEvent(
        source=source,
        detector=detector,
        reasons=json.dumps(reasons),
        excerpt=(excerpt or "")[:MAX_EXCERPT],
        candidate_id=candidate_id,
        candidate_name=candidate_name,
        session_token=session_token,
        question_index=question_index,
    )
    db.add(event)
    db.commit()
    db.refresh(event)
    logger.warning(
        "SECURITY prompt-injection suspected source=%s detector=%s candidate=%s session=%s "
        "reasons=%s",
        source,
        detector,
        candidate_id or candidate_name,
        (session_token or "")[:8],
        reasons,
    )
    return event


def list_events(db: Session, limit: int = 200) -> list[SecurityEvent]:
    return list(
        db.scalars(
            select(SecurityEvent).order_by(SecurityEvent.created_at.desc()).limit(limit)
        ).all()
    )


def reasons_by_candidate(db: Session, candidate_ids: list[str]) -> dict[str, list[str]]:
    return _group(db, SecurityEvent.candidate_id, candidate_ids, source="cv")


def reasons_by_session(db: Session, tokens: list[str]) -> dict[str, list[str]]:
    return _group(db, SecurityEvent.session_token, tokens)


def _group(db: Session, column, keys: list, source: str | None = None) -> dict[str, list[str]]:
    if not keys:
        return {}
    query = select(column, SecurityEvent.reasons).where(column.in_(keys))
    if source:
        query = query.where(SecurityEvent.source == source)
    out: dict[str, list[str]] = {}
    for key, reasons in db.execute(query):
        bucket = out.setdefault(key, [])
        for reason in json.loads(reasons or "[]"):
            if reason not in bucket:
                bucket.append(reason)
    return out
