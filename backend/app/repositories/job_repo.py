import json
from datetime import UTC, datetime

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.candidate import Candidate
from app.models.job import Job, JobMatch


def _now() -> datetime:
    return datetime.now(UTC)


# ── Jobs ──────────────────────────────────────────────────────────────────────


def create_job(
    db: Session, *, title: str, description: str, required: list, nice: list, soft: list
) -> Job:
    job = Job(
        title=title,
        description=description,
        required_skills_json=json.dumps(required),
        nice_skills_json=json.dumps(nice),
        soft_skills_json=json.dumps(soft),
        created_at=_now(),
        updated_at=_now(),
    )
    db.add(job)
    db.commit()
    db.refresh(job)
    return job


def get_job(db: Session, job_id: int) -> Job | None:
    return db.get(Job, job_id)


def job_skills(job: Job) -> dict[str, list[str]]:
    return {
        "required": json.loads(job.required_skills_json or "[]"),
        "nice": json.loads(job.nice_skills_json or "[]"),
        "soft": json.loads(job.soft_skills_json or "[]"),
    }


def update_job(
    db: Session,
    job: Job,
    *,
    title: str | None = None,
    description: str | None = None,
    skills: dict[str, list[str]] | None = None,
) -> Job:
    """Update a job. Changing anything that affects scoring clears its matches."""
    if title is not None:
        job.title = title
    if description is not None:
        job.description = description
    if skills is not None:
        job.required_skills_json = json.dumps(skills["required"])
        job.nice_skills_json = json.dumps(skills["nice"])
        job.soft_skills_json = json.dumps(skills["soft"])
        db.query(JobMatch).filter(JobMatch.job_id == job.id).delete()
    job.updated_at = _now()
    db.commit()
    db.refresh(job)
    return job


def delete_job(db: Session, job: Job) -> None:
    db.delete(job)  # matches are removed by the ORM cascade
    db.commit()


def list_jobs_with_stats(db: Session, scoring_version: str) -> list[dict]:
    """Jobs for the grid, with match count, best score and pending (unscored) CVs."""
    total_candidates = count_candidates(db)
    handled = dict(
        db.execute(
            select(JobMatch.job_id, func.count(JobMatch.id))
            .where(JobMatch.scoring_version == scoring_version)
            .group_by(JobMatch.job_id)
        ).all()
    )
    stats = {
        job_id: (count, best)
        for job_id, count, best in db.execute(
            select(JobMatch.job_id, func.count(JobMatch.id), func.max(JobMatch.score))
            .where(JobMatch.scoring_version == scoring_version, JobMatch.retrieved.is_(True))
            .group_by(JobMatch.job_id)
        )
    }
    jobs = db.scalars(select(Job).order_by(Job.created_at.desc())).all()
    out = []
    for job in jobs:
        count, best = stats.get(job.id, (0, None))
        out.append(
            {
                "job": job,
                "candidates_count": count,
                "best_score": best,
                "pending_count": max(0, total_candidates - handled.get(job.id, 0)),
            }
        )
    return out


# ── Matches ───────────────────────────────────────────────────────────────────


def list_matches(db: Session, job_id: int) -> list[tuple[JobMatch, Candidate]]:
    rows = db.execute(
        select(JobMatch, Candidate)
        .join(Candidate, Candidate.id == JobMatch.candidate_id)
        .where(JobMatch.job_id == job_id, JobMatch.retrieved.is_(True))
        .order_by(JobMatch.score.desc())
    ).all()
    return [(m, c) for m, c in rows]


def candidates_to_score(
    db: Session, job_id: int, scoring_version: str, rescore_all: bool = False
) -> list[Candidate]:
    """
    Candidates that have no up-to-date match for this job: newly uploaded CVs,
    or CVs scored with an older version of the formula.
    """
    if rescore_all:
        return list(db.scalars(select(Candidate)).all())
    up_to_date = select(JobMatch.candidate_id).where(
        JobMatch.job_id == job_id, JobMatch.scoring_version == scoring_version
    )
    return list(db.scalars(select(Candidate).where(Candidate.id.not_in(up_to_date))).all())


def count_candidates(db: Session) -> int:
    return db.scalar(select(func.count()).select_from(Candidate)) or 0


def count_filtered_out(db: Session, job_id: int, scoring_version: str) -> int:
    """CVs that ChromaDB did not pre-select for this job (stage 1 of retrieve -> rank)."""
    return (
        db.scalar(
            select(func.count(JobMatch.id)).where(
                JobMatch.job_id == job_id,
                JobMatch.scoring_version == scoring_version,
                JobMatch.retrieved.is_(False),
            )
        )
        or 0
    )


def count_pending(db: Session, job_id: int, scoring_version: str) -> int:
    up_to_date = select(JobMatch.candidate_id).where(
        JobMatch.job_id == job_id, JobMatch.scoring_version == scoring_version
    )
    return (
        db.scalar(
            select(func.count()).select_from(Candidate).where(Candidate.id.not_in(up_to_date))
        )
        or 0
    )


def upsert_match(db: Session, *, job_id: int, candidate_id: str, **fields) -> JobMatch:
    match = db.scalar(
        select(JobMatch).where(JobMatch.job_id == job_id, JobMatch.candidate_id == candidate_id)
    )
    if match is None:
        match = JobMatch(job_id=job_id, candidate_id=candidate_id)
        db.add(match)
    for key, value in fields.items():
        setattr(match, key, value)
    match.matched_at = _now()
    return match


def delete_matches_for_candidate(db: Session, candidate_id: str) -> None:
    # SQLite doesn't enforce ON DELETE CASCADE by default, so do it explicitly.
    db.query(JobMatch).filter(JobMatch.candidate_id == candidate_id).delete()
