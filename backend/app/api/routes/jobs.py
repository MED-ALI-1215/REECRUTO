import json

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.api.dependencies import require_auth
from app.core.exceptions import AppError
from app.db.session import get_db
from app.models.job import Job
from app.repositories import job_repo
from app.schemas.job import (
    JobCreateIn,
    JobDetailOut,
    JobMatchOut,
    JobMatchRunOut,
    JobSkills,
    JobSummaryOut,
    JobUpdateIn,
)
from app.services import job_service
from app.services.scoring_service import SCORING_VERSION, STRONG_THRESHOLD

router = APIRouter(prefix="/jobs", tags=["jobs"])


class JobNotFoundError(AppError):
    status_code = 404
    detail = "Job not found."


def _get_job_or_404(db: Session, job_id: int) -> Job:
    job = job_repo.get_job(db, job_id)
    if job is None:
        raise JobNotFoundError()
    return job


def _detail(db: Session, job: Job) -> JobDetailOut:
    matches = []
    for match, candidate in job_repo.list_matches(db, job.id):
        breakdown = json.loads(match.breakdown_json or "[]")
        technical = [b for b in breakdown if b["category"] != "soft"]
        matches.append(
            JobMatchOut(
                candidate_id=candidate.id,
                name=candidate.name,
                email=candidate.email,
                file_name=candidate.file_name,
                score=match.score,
                required_score=match.required_score,
                nice_score=match.nice_score,
                soft_score=match.soft_score,
                matched_skills=[b["skill"] for b in technical if b["score"] >= STRONG_THRESHOLD],
                partial_skills=[b["skill"] for b in technical if 0 < b["score"] < STRONG_THRESHOLD],
                missing_skills=[b["skill"] for b in technical if b["score"] == 0],
                breakdown=breakdown,
                reasoning=match.reasoning,
                legacy_profile=match.legacy_profile,
                matched_at=match.matched_at,
            )
        )
    return JobDetailOut(
        id=job.id,
        title=job.title,
        description=job.description,
        skills=JobSkills(**job_repo.job_skills(job)),
        matches=matches,
        pending_count=job_repo.count_pending(db, job.id, SCORING_VERSION),
        filtered_out_count=job_repo.count_filtered_out(db, job.id, SCORING_VERSION),
        created_at=job.created_at,
        updated_at=job.updated_at,
    )


@router.get("", response_model=list[JobSummaryOut])
def list_jobs(db: Session = Depends(get_db), _: str = Depends(require_auth)):
    out = []
    for row in job_repo.list_jobs_with_stats(db, SCORING_VERSION):
        job = row["job"]
        out.append(
            JobSummaryOut(
                id=job.id,
                title=job.title,
                description_preview=job.description[:220],
                required_skills=job_repo.job_skills(job)["required"],
                candidates_count=row["candidates_count"],
                best_score=row["best_score"],
                pending_count=row["pending_count"],
                created_at=job.created_at,
            )
        )
    return out


@router.post("", response_model=JobDetailOut, status_code=status.HTTP_201_CREATED)
def create_job(body: JobCreateIn, db: Session = Depends(get_db), _: str = Depends(require_auth)):
    """Save a job description, extract its skills (1 AI call) and score every CV."""
    job = job_service.create_job(db, title=body.title.strip(), description=body.description)
    return _detail(db, job)


@router.get("/{job_id}", response_model=JobDetailOut)
def get_job(job_id: int, db: Session = Depends(get_db), _: str = Depends(require_auth)):
    return _detail(db, _get_job_or_404(db, job_id))


@router.patch("/{job_id}", response_model=JobDetailOut)
def update_job(
    job_id: int,
    body: JobUpdateIn,
    db: Session = Depends(get_db),
    _: str = Depends(require_auth),
):
    job = _get_job_or_404(db, job_id)
    job = job_service.update_job(
        db,
        job,
        title=body.title.strip() if body.title else None,
        description=body.description,
        skills=body.skills.model_dump() if body.skills else None,
    )
    return _detail(db, job)


@router.post("/{job_id}/match", response_model=JobMatchRunOut)
def run_match(
    job_id: int,
    rescore_all: bool = Query(False, description="Rescore every CV, not only new ones"),
    db: Session = Depends(get_db),
    _: str = Depends(require_auth),
):
    """Score the CVs uploaded since the last search: ChromaDB retrieve, then rank (no AI call)."""
    job = _get_job_or_404(db, job_id)
    counts = job_service.run_matching(db, job, rescore_all=rescore_all)
    return JobMatchRunOut(**counts, job=_detail(db, job))


@router.delete("/{job_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_job(job_id: int, db: Session = Depends(get_db), _: str = Depends(require_auth)):
    job_repo.delete_job(db, _get_job_or_404(db, job_id))
