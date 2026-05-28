"""
Candidate matching service.

Default pipeline (zero Groq calls):
  1. ChromaDB vector search → top N candidates by embedding similarity
  2. Local scoring formula  → combines vector score + skills overlap + cert bonus
  3. Sort by final score, return top `n_results`

Optional deep analysis (one Groq call, only when deep=True):
  4. Groq re-ranks the top candidates with full job description context
"""
from sqlalchemy.orm import Session

from app.core.logging import get_logger
from app.models.candidate import Candidate
from app.repositories.candidate_repo import search_candidates_vector
from app.services.scoring_service import compute_score

logger = get_logger(__name__)

# Fetch more from ChromaDB than we need so scoring has room to re-order
_VECTOR_FETCH_MULTIPLIER = 3


def match_candidates(
    db: Session,
    job_description: str,
    n_results: int = 5,
    deep: bool = False,
) -> list[dict]:
    """
    Match candidates to a job description.

    deep=False (default): local formula only, no API calls.
    deep=True:  local formula first, then Groq re-ranks the top results.
                Use sparingly — costs tokens.
    """
    fetch_n = min(n_results * _VECTOR_FETCH_MULTIPLIER, 30)
    vector_hits = search_candidates_vector(job_description, n_results=fetch_n)

    if not vector_hits:
        logger.info("No candidates in vector store")
        return []

    # Score each candidate locally
    scored = []
    for hit in vector_hits:
        candidate: Candidate | None = db.get(Candidate, hit["candidate_id"])
        if candidate is None:
            logger.warning("Vector store has ID %s but no DB record — skipping", hit["candidate_id"])
            continue

        breakdown = compute_score(
            vector_score=hit["match_score"],
            job_description=job_description,
            skills_text=candidate.skills_text or "",
            experience_text=candidate.experience_text or "",
            certifications_text=candidate.certifications_text or "",
        )

        scored.append({
            "id": candidate.id,
            "name": candidate.name,
            "email": candidate.email,
            "file_name": candidate.file_name,
            "match_score": breakdown.final_score,
            "vector_score": breakdown.vector_score,
            "skills_score": breakdown.skills_score,
            "cert_score": breakdown.cert_score,
            "matched_skills": breakdown.matched_skills,
            "missing_skills": breakdown.missing_skills,
            "reasoning": breakdown.reasoning,
            "structured_info": candidate.structured_info,
        })

    # Sort by final score, keep top n_results
    scored.sort(key=lambda x: x["match_score"], reverse=True)
    top = scored[:n_results]

    logger.info(
        "Matched %d candidates (from %d vector hits), deep=%s",
        len(top), len(vector_hits), deep
    )

    if deep and top:
        top = _deep_rerank(top, job_description, db)

    return top


def _deep_rerank(candidates: list[dict], job_description: str, db: Session) -> list[dict]:
    """
    Optional Groq re-ranking pass.
    Falls back gracefully to formula scores if anything goes wrong.
    """
    import json
    import re
    import time

    from app.core.config import get_settings
    from app.core.logging import log_ai_call
    from app.core.prompts import load_prompt
    from app.repositories.ai_call_repo import record_ai_call

    settings = get_settings()

    candidates_summary = "\n\n".join(
        f"Candidate ID: {c['id']}\nName: {c['name']}\n"
        f"Formula score: {c['match_score']}\n"
        f"Matched skills: {', '.join(c['matched_skills'][:10])}\n"
        f"Profile:\n{(c['structured_info'] or '')[:600]}"
        for c in candidates
    )

    prompt = load_prompt(
        "match_rerank_v1.txt",
        job_description=job_description[:1000],
        candidates_summary=candidates_summary,
    )

    t0 = time.monotonic()
    try:
        from groq import Groq
        resp = Groq(api_key=settings.GROQ_API_KEY).chat.completions.create(
            messages=[
                {"role": "system", "content": "You are a senior recruiter. Respond only with valid JSON."},
                {"role": "user", "content": prompt},
            ],
            model=settings.GROQ_MODEL,
            temperature=0.2,
            max_tokens=600,
            timeout=30,
        )
        latency = (time.monotonic() - t0) * 1000
        log_ai_call(logger, service="match_rerank", model=settings.GROQ_MODEL,
                    prompt_tokens=resp.usage.prompt_tokens, latency_ms=latency, success=True)
        record_ai_call(
            db, service="match_rerank", model=settings.GROQ_MODEL,
            prompt_version="match_rerank_v1",
            prompt_tokens=resp.usage.prompt_tokens,
            completion_tokens=resp.usage.completion_tokens,
            latency_ms=latency, success=True,
        )

        raw = resp.choices[0].message.content.strip()
        match = re.search(r"\[.*\]", raw, re.DOTALL)
        if not match:
            raise ValueError("No JSON array in response")

        rerank_data = json.loads(match.group())
        score_map = {r["candidate_id"]: r for r in rerank_data}

        for c in candidates:
            rerank = score_map.get(c["id"], {})
            if "score" in rerank:
                # Blend: 60% Groq, 40% formula — don't throw away local signal
                c["match_score"] = round(rerank["score"] * 0.6 + c["match_score"] * 0.4, 1)
                c["reasoning"] = rerank.get("reasoning", c["reasoning"])

        candidates.sort(key=lambda x: x["match_score"], reverse=True)
        return candidates

    except Exception as e:
        latency = (time.monotonic() - t0) * 1000
        log_ai_call(logger, service="match_rerank", model=settings.GROQ_MODEL,
                    prompt_tokens=0, latency_ms=latency, success=False, error=str(e))
        logger.warning("Deep re-rank failed (%s) — using formula scores", e)
        return candidates
