from datetime import datetime
from pydantic import BaseModel


class CandidateOut(BaseModel):
    id: str
    name: str
    email: str | None = None
    file_name: str | None = None
    uploaded_at: datetime
    match_score: float | None = None
    structured_info: str | None = None  # returned for CV upload list

    model_config = {"from_attributes": True}


class CandidateListOut(BaseModel):
    total: int
    candidates: list[CandidateOut]
