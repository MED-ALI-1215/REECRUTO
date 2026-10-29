from datetime import datetime

from pydantic import BaseModel, Field


class InterviewCreateIn(BaseModel):
    candidate_name: str = Field(min_length=1, max_length=256)
    candidate_email: str = Field(min_length=3, max_length=256)
    # Linking the saved job shares its interview questions; title/description then default to it
    job_id: int | None = None
    candidate_id: str | None = None  # enables the personal question built from the CV
    job_title: str = Field(default="", max_length=256)
    job_description: str = Field(default="", max_length=20_000)


class InterviewSessionOut(BaseModel):
    token: str
    candidate_name: str
    candidate_email: str
    job_title: str
    used: bool
    expires_at: datetime

    model_config = {"from_attributes": True}


class AnswerIn(BaseModel):
    question_index: int = Field(ge=0)
    answer: str = Field(max_length=20_000)  # the real limit is MAX_ANSWER_CHARS (setting)


class QuestionsOut(BaseModel):
    questions: list[str]
    kinds: list[str]  # "job" | "personal"
    progress: list[dict | None]  # already-answered questions (to resume after a reload)


class AnswerOut(BaseModel):
    score: float
    feedback: str
    keywords: list[str]


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
    flagged: bool = False  # prompt-injection attempt detected during the interview
    flag_reasons: list[str] = []

    model_config = {"from_attributes": True}
