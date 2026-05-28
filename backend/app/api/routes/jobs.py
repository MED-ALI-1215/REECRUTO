from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.api.dependencies import require_auth
from app.db.session import get_db
from app.services import matching_service

router = APIRouter(prefix="/jobs", tags=["jobs"])


class JobMatchIn(BaseModel):
    job_description: str
    n_results: int = 5
    deep: bool = False   # set True only when you want the Groq re-rank pass


class MatchResult(BaseModel):
    id: str
    name: str
    email: str | None = None
    file_name: str | None = None
    match_score: float
    vector_score: float
    skills_score: float
    cert_score: float
    matched_skills: list[str]
    missing_skills: list[str]
    reasoning: str


@router.post("/match", response_model=list[MatchResult])
def match_candidates(
    body: JobMatchIn,
    db: Session = Depends(get_db),
    _: str = Depends(require_auth),
):
    return matching_service.match_candidates(
        db,
        job_description=body.job_description,
        n_results=body.n_results,
        deep=body.deep,
    )
