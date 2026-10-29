"""
Job service — saved job descriptions and evidence-based matching.

  create_job   : one Groq call to extract the job's skills, then score every CV
  run_matching : retrieve (ChromaDB) then rank (evidence) the CVs without an up-to-date
                 match for the job — no LLM call
"""

import json

from sqlalchemy.orm import Session
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

from app.core.ai import chat_completion, parse_json_object
from app.core.config import get_settings
from app.core.exceptions import GroqAPIError, GroqParseError
from app.core.logging import get_logger
from app.core.prompts import load_prompt
from app.models.job import Job
from app.repositories import job_repo
from app.services import semantic_service
from app.services.extraction_service import load_profile
from app.services.scoring_service import SCORING_VERSION, compute_match, profile_skill_names
from app.services.skills import normalize_list

logger = get_logger(__name__)

PROMPT_VERSION = "job_extraction_v1"
MAX_REQUIRED_SKILLS = 20


def clean_skills(required, nice, soft) -> dict[str, list[str]]:
    """Normalise names and make sure a skill appears in one list only."""
    req = normalize_list(required)[:MAX_REQUIRED_SKILLS]
    nice_ = [s for s in normalize_list(nice) if s not in req]
    soft_ = [s for s in normalize_list(soft) if s not in req and s not in nice_]
    return {"required": req, "nice": nice_, "soft": soft_}


@retry(
    retry=retry_if_exception_type(GroqAPIError),
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=2, max=10),
    reraise=True,
)
def extract_job_skills(title: str, description: str, db=None) -> tuple[str, dict[str, list[str]]]:
    """Return (title, skills) extracted from a job description by the LLM."""
    raw = chat_completion(
        service="job_extraction",
        prompt_version=PROMPT_VERSION,
        system=load_prompt(f"{PROMPT_VERSION}_system.txt"),
        user=load_prompt(
            f"{PROMPT_VERSION}.txt", job_title=title or "", job_description=description[:8000]
        ),
        temperature=0.1,
        max_tokens=3000,
        db=db,
        json_mode=True,
    )
    try:
        data = parse_json_object(raw)
    except GroqParseError as e:
        raise GroqAPIError(f"Job extraction returned invalid JSON: {e}") from e

    skills = clean_skills(
        data.get("required_skills"), data.get("nice_to_have_skills"), data.get("soft_skills")
    )
    extracted_title = str(data.get("title") or "").strip()
    return (title or extracted_title or "Untitled job"), skills


def run_matching(db: Session, job: Job, rescore_all: bool = False) -> dict[str, int]:
    """
    Two-stage matching for the CVs that lack an up-to-date match (no LLM call):

      1. retrieve — with many CVs, ChromaDB keeps the MATCH_RETRIEVE_TOP_K closest ones
      2. rank     — evidence-based scoring, with semantic skill matching from ChromaDB

    Returns {"scored": ..., "filtered_out": ...}.
    """
    settings = get_settings()
    skills = job_repo.job_skills(job)
    candidates = job_repo.candidates_to_score(db, job.id, SCORING_VERSION, rescore_all)

    # Stage 1 — retrieve
    kept_ids, _ = semantic_service.retrieve_candidates(
        semantic_service.job_query_text(job.title, skills),
        [c.id for c in candidates],
        total_cvs=job_repo.count_candidates(db),
    )
    kept = set(kept_ids)
    profiles = {c.id: load_profile(c.structured_info) for c in candidates if c.id in kept}

    # Semantic skill matching: grow the skill vocabulary, then look up synonyms once per run
    vocabulary: set[str] = set()
    for profile in profiles.values():
        vocabulary |= profile_skill_names(profile)
    semantic_service.index_skills(vocabulary)
    similar = semantic_service.similar_skills(skills["required"] + skills["nice"])

    # Stage 2 — rank
    filtered_out = 0
    for candidate in candidates:
        if candidate.id not in kept:
            filtered_out += 1
            job_repo.upsert_match(
                db,
                job_id=job.id,
                candidate_id=candidate.id,
                score=0.0,
                required_score=None,
                nice_score=None,
                soft_score=None,
                breakdown_json="[]",
                reasoning="Not pre-selected by the semantic search (outside the top K).",
                legacy_profile=False,
                retrieved=False,
                scoring_version=SCORING_VERSION,
            )
            continue
        result = compute_match(
            skills, profiles[candidate.id], similar, settings.SEMANTIC_MATCH_FACTOR
        )
        job_repo.upsert_match(
            db,
            job_id=job.id,
            candidate_id=candidate.id,
            score=result.final_score,
            required_score=result.required_score,
            nice_score=result.nice_score,
            soft_score=result.soft_score,
            breakdown_json=json.dumps(result.breakdown()),
            reasoning=result.reasoning,
            legacy_profile=result.legacy_profile,
            retrieved=True,
            scoring_version=SCORING_VERSION,
        )
    db.commit()
    scored = len(candidates) - filtered_out
    logger.info(
        "Job %s: scored %d CVs, %d not pre-selected (rescore_all=%s)",
        job.id,
        scored,
        filtered_out,
        rescore_all,
    )
    return {"scored": scored, "filtered_out": filtered_out}


def create_job(db: Session, *, title: str, description: str) -> Job:
    final_title, skills = extract_job_skills(title, description, db=db)
    job = job_repo.create_job(
        db,
        title=final_title,
        description=description,
        required=skills["required"],
        nice=skills["nice"],
        soft=skills["soft"],
    )
    run_matching(db, job)
    return job


def update_job(
    db: Session,
    job: Job,
    *,
    title: str | None = None,
    description: str | None = None,
    skills: dict | None = None,
) -> Job:
    """
    Edit a job. A new description re-extracts the skills (unless skills are given);
    any skill change clears the matches and rescores every CV.
    """
    new_skills = None
    if skills is not None:
        new_skills = clean_skills(skills.get("required"), skills.get("nice"), skills.get("soft"))
    elif description is not None and description != job.description:
        _, new_skills = extract_job_skills(title or job.title, description, db=db)

    job = job_repo.update_job(db, job, title=title, description=description, skills=new_skills)
    if new_skills is not None:
        run_matching(db, job, rescore_all=True)
    return job
