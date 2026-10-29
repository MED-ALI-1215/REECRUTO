import secrets

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel

from app.core.config import get_settings
from app.core.security import create_access_token

router = APIRouter(prefix="/auth", tags=["auth"])


class LoginIn(BaseModel):
    username: str
    password: str


class TokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"


def _check_credentials(username: str, password: str) -> bool:
    """Constant-time comparison so response timing doesn't leak the credentials."""
    settings = get_settings()
    user_ok = secrets.compare_digest(username.encode(), settings.RECRUITER_USERNAME.encode())
    pass_ok = secrets.compare_digest(password.encode(), settings.RECRUITER_PASSWORD.encode())
    return user_ok and pass_ok


@router.post("/login", response_model=TokenOut)
def login(body: LoginIn):
    if not _check_credentials(body.username, body.password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials",
        )
    return TokenOut(access_token=create_access_token(subject=body.username))
