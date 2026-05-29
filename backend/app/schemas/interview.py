from datetime import datetime

from pydantic import BaseModel


class InterviewCreateIn(BaseModel):
    candidate_name: str
    candidate_email: str
    job_title: str
    job_description: str


class InterviewSessionOut(BaseModel):
    token: str
    candidate_name: str
    candidate_email: str
    job_title: str
    used: bool
    expires_at: datetime

    model_config = {"from_attributes": True}


class AnswerIn(BaseModel):
    question: str
    answer: str


class InterviewResultOut(BaseModel):
    id: int
    candidate_name: str
    candidate_email: str
    job_title: str
    overall_score: float
    recommendation: str | None
    summary: str | None
    strengths: str | None
    red_flags: str | None
    completed_at: datetime

    model_config = {"from_attributes": True}


class JobMatchIn(BaseModel):
    job_description: str
    n_results: int = 5
