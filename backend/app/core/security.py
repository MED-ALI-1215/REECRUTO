import secrets
from datetime import datetime, timedelta, timezone
from typing import Optional

from jose import JWTError, jwt

from app.core.config import get_settings

ALGORITHM = "HS256"


def create_access_token(subject: str, expires_delta: Optional[timedelta] = None) -> str:
    settings = get_settings()
    expire = datetime.now(timezone.utc) + (
        expires_delta or timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    )
    return jwt.encode(
        {"sub": subject, "exp": expire},
        settings.SECRET_KEY,
        algorithm=ALGORITHM,
    )


def decode_access_token(token: str) -> Optional[str]:
    """Return the subject (username) or None if invalid/expired."""
    try:
        payload = jwt.decode(token, get_settings().SECRET_KEY, algorithms=[ALGORITHM])
        return payload.get("sub")
    except JWTError:
        return None


def generate_interview_token() -> str:
    """Cryptographically secure one-time token for candidate interview links."""
    return secrets.token_urlsafe(32)
