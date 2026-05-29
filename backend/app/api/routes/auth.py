from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel

from app.core.security import create_access_token
from app.core.config import get_settings

router = APIRouter(prefix="/auth", tags=["auth"])

# ── Temporary hardcoded credentials — replace with DB users in Phase 2 ────────
_RECRUITER_USERNAME = "admin"
_RECRUITER_PASSWORD = "admin"   # override in .env via env var later


class LoginIn(BaseModel):
    username: str
    password: str


class TokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"


@router.post("/login", response_model=TokenOut)
def login(body: LoginIn):
    if body.username != _RECRUITER_USERNAME or body.password != _RECRUITER_PASSWORD:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials",
        )
    token = create_access_token(subject=body.username)
    return TokenOut(access_token=token)
