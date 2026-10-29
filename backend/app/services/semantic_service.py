"""
ChromaDB-powered semantic layer used by the matcher.

1. Retrieve (recall): pre-select the CVs closest to a job before the detailed,
   evidence-based scoring — only when there are many CVs (MATCH_PREFILTER_MIN_CVS).
2. Semantic skill matching: find skill names that mean the same thing
   ("Torch" ~ "PyTorch", "LLM orchestration" ~ "LangGraph") beyond the alias list.

Everything here degrades gracefully: if ChromaDB fails, the matcher falls back
to scoring every CV with exact skill matching.
"""

from collections.abc import Iterable

from app.core.config import get_settings
from app.core.logging import get_logger
from app.db.vector import get_candidates_collection, get_skills_collection

logger = get_logger(__name__)


# ── 1. Retrieve ───────────────────────────────────────────────────────────────


def job_query_text(title: str, skills: dict[str, list[str]]) -> str:
    """Mirror the shape of the CV documents stored in ChromaDB (skills-first)."""
    parts = [title]
    if skills.get("required"):
        parts.append("Skills: " + ", ".join(skills["required"]))
    if skills.get("nice"):
        parts.append("Also: " + ", ".join(skills["nice"]))
    return "\n".join(parts)


def retrieve_candidates(
    query: str, candidate_ids: list[str], total_cvs: int
) -> tuple[list[str], bool]:
    """
    Return (ids to score, prefilter_applied).

    Below MATCH_PREFILTER_MIN_CVS every candidate is scored. Above it, ChromaDB
    keeps the MATCH_RETRIEVE_TOP_K closest ones among `candidate_ids`.
    """
    settings = get_settings()
    if not candidate_ids or total_cvs < settings.MATCH_PREFILTER_MIN_CVS:
        return candidate_ids, False
    top_k = min(settings.MATCH_RETRIEVE_TOP_K, len(candidate_ids))
    try:
        result = get_candidates_collection().query(
            query_texts=[query],
            n_results=top_k,
            where={"candidate_id": {"$in": candidate_ids}},
        )
        ids = result.get("ids", [[]])[0] if result else []
    except Exception as e:
        logger.warning("ChromaDB retrieval failed (%s) — scoring every CV instead", e)
        return candidate_ids, False
    logger.info("Retrieve: kept %d of %d CVs (top_k=%d)", len(ids), len(candidate_ids), top_k)
    return list(ids), True


# ── 2. Semantic skill matching ────────────────────────────────────────────────


def index_skills(names: Iterable[str]) -> None:
    """Add normalised skill names to the vocabulary (ids = names, so upsert is idempotent)."""
    if not get_settings().SEMANTIC_SKILLS_ENABLED:
        return
    unique = sorted({n for n in names if n})
    if not unique:
        return
    try:
        collection = get_skills_collection()
        existing = set(collection.get(ids=unique).get("ids", []))
        new = [n for n in unique if n not in existing]
        if new:
            collection.add(ids=new, documents=new)
            logger.info("Skill vocabulary: added %d skills", len(new))
    except Exception as e:
        logger.warning("Could not index skills in ChromaDB: %s", e)


def similar_skills(skills: list[str], k: int = 5) -> dict[str, list[tuple[str, float]]]:
    """
    For each job skill, the CV skill names whose meaning is close enough
    (cosine similarity >= SKILL_SIMILARITY_THRESHOLD), best first.
    """
    settings = get_settings()
    if not settings.SEMANTIC_SKILLS_ENABLED or not skills:
        return {}
    try:
        collection = get_skills_collection()
        count = collection.count()
        if count == 0:
            return {}
        result = collection.query(query_texts=skills, n_results=min(k + 1, count))
    except Exception as e:
        logger.warning("Semantic skill lookup failed: %s", e)
        return {}

    out: dict[str, list[tuple[str, float]]] = {}
    for skill, ids, distances in zip(skills, result["ids"], result["distances"], strict=False):
        matches = [
            (other, round(1 - dist, 3))
            for other, dist in zip(ids, distances, strict=False)
            if other != skill and 1 - dist >= settings.SKILL_SIMILARITY_THRESHOLD
        ]
        if matches:
            out[skill] = matches
    return out
