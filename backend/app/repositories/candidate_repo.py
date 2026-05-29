from datetime import datetime, timezone
from typing import Optional

from sqlalchemy.orm import Session

from app.db.vector import get_candidates_collection
from app.models.candidate import Candidate
from app.core.logging import get_logger

logger = get_logger(__name__)


# ── PostgreSQL operations ─────────────────────────────────────────────────────

def create_candidate(
    db: Session, *, id: str, name: str, email: Optional[str],
    file_name: Optional[str], structured_info: str, cv_text: str,
    skills_text: str = "", experience_text: str = "", certifications_text: str = "",
) -> Candidate:
    candidate = Candidate(
        id=id,
        name=name,
        email=email,
        file_name=file_name,
        structured_info=structured_info,
        cv_text=cv_text,
        skills_text=skills_text,
        experience_text=experience_text,
        certifications_text=certifications_text,
        uploaded_at=datetime.now(timezone.utc),
    )
    db.add(candidate)
    db.commit()
    db.refresh(candidate)
    return candidate


def get_candidate(db: Session, candidate_id: str) -> Optional[Candidate]:
    return db.get(Candidate, candidate_id)


def list_candidates(db: Session) -> list[Candidate]:
    return db.query(Candidate).order_by(Candidate.uploaded_at.desc()).all()


def delete_candidate(db: Session, candidate_id: str) -> bool:
    candidate = db.get(Candidate, candidate_id)
    if not candidate:
        return False
    db.delete(candidate)
    db.commit()
    return True


# ── ChromaDB operations ───────────────────────────────────────────────────────

def add_to_vector_store(candidate_id: str, chroma_document: str) -> None:
    """
    Store the compact semantic document (skills + experience + projects)
    instead of the raw CV text — cleaner signal for vector search.
    """
    collection = get_candidates_collection()
    collection.add(
        ids=[candidate_id],
        documents=[chroma_document],
        metadatas=[{"candidate_id": candidate_id}],
    )
    logger.info("ChromaDB: added candidate %s (%d chars)", candidate_id, len(chroma_document))


def remove_from_vector_store(candidate_id: str) -> None:
    collection = get_candidates_collection()
    try:
        collection.delete(ids=[candidate_id])
        logger.info("ChromaDB: removed candidate %s", candidate_id)
    except Exception as e:
        logger.warning("ChromaDB: could not delete %s — %s", candidate_id, e)


def search_candidates_vector(query: str, n_results: int = 10) -> list[dict]:
    """
    Returns top N candidates by vector similarity.
    We fetch more than the final result count (default 10) so the scoring
    formula has enough candidates to re-rank from.
    """
    collection = get_candidates_collection()
    count = collection.count()
    if count == 0:
        return []

    n = min(n_results, count)
    results = collection.query(query_texts=[query], n_results=n)

    if not results or not results.get("ids") or not results["ids"][0]:
        return []

    out = []
    for cid, distance in zip(results["ids"][0], results["distances"][0]):
        # Convert L2 distance to 0-100 score — lower distance = better match
        match_score = round(max(0.0, min(100.0, 100 - distance * 50)), 1)
        out.append({"candidate_id": cid, "distance": distance, "match_score": match_score})
    return out
