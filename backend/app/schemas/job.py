from datetime import datetime

from pydantic import BaseModel, Field


class JobSkills(BaseModel):
    required: list[str] = []
    nice: list[str] = []
    soft: list[str] = []


class JobCreateIn(BaseModel):
    title: str = Field(default="", max_length=256)
    description: str = Field(min_length=20, max_length=20_000)


class JobUpdateIn(BaseModel):
    title: str | None = Field(default=None, max_length=256)
    description: str | None = Field(default=None, min_length=20, max_length=20_000)
    skills: JobSkills | None = None  # edit the extracted skills by hand


class SkillEvidenceOut(BaseModel):
    skill: str
    category: str
    score: float
    sources: list[dict]


class JobMatchOut(BaseModel):
    candidate_id: str
    name: str
    email: str | None = None
    file_name: str | None = None
    score: float
    required_score: float | None = None
    nice_score: float | None = None
    soft_score: float | None = None
    matched_skills: list[str]
    partial_skills: list[str]
    missing_skills: list[str]
    breakdown: list[SkillEvidenceOut]
    reasoning: str | None = None
    legacy_profile: bool = False
    flagged: bool = False  # the CV tried to instruct the AI (prompt injection)
    matched_at: datetime


class JobSummaryOut(BaseModel):
    id: int
    title: str
    description_preview: str
    required_skills: list[str]
    candidates_count: int
    best_score: float | None = None
    pending_count: int
    created_at: datetime


class JobDetailOut(BaseModel):
    id: int
    title: str
    description: str
    skills: JobSkills
    matches: list[JobMatchOut]
    pending_count: int
    filtered_out_count: int = 0  # CVs not pre-selected by ChromaDB
    interview_questions: list[str] = []  # shared by every candidate invited for this job
    created_at: datetime
    updated_at: datetime


class JobMatchRunOut(BaseModel):
    scored: int
    filtered_out: int = 0
    job: JobDetailOut
