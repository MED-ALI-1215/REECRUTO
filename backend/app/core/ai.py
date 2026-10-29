"""
Shared Groq helper.

Every AI call in the app goes through `chat_completion`, which handles timing,
structured logging, persisting the call to the `ai_calls` table and wrapping
errors in GroqAPIError (so tenacity retries kick in upstream).
"""

from __future__ import annotations

import json
import re
import threading
import time
from typing import Any

from app.core.config import get_settings
from app.core.exceptions import GroqAPIError, GroqParseError
from app.core.logging import get_logger, log_ai_call

logger = get_logger(__name__)

_client_lock = threading.Lock()
_client_cache: tuple[Any, str, Any] | None = None  # (Groq class, api key, client)


def get_groq_client():
    """
    Return a shared Groq client (one HTTP connection pool for the whole process)
    instead of building a new client on every request.

    The cache is keyed on the Groq class and API key, so tests that patch
    `groq.Groq` still get their mock.
    """
    global _client_cache
    import groq

    key = groq.Groq, get_settings().GROQ_API_KEY
    with _client_lock:
        if _client_cache is None or _client_cache[:2] != key:
            _client_cache = (*key, groq.Groq(api_key=key[1]))
        return _client_cache[2]


def _as_int(value: Any) -> int:
    try:
        return int(value or 0)
    except (TypeError, ValueError):
        return 0


def _persist(db, **fields) -> None:
    if db is None:
        return
    try:
        from app.repositories.ai_call_repo import record_ai_call

        record_ai_call(db, model=get_settings().GROQ_MODEL, **fields)
    except Exception as e:  # logging must never break the request
        logger.warning("Could not persist AI call record: %s", e)


def chat_completion(
    *,
    service: str,
    prompt_version: str,
    system: str,
    user: str,
    temperature: float,
    max_tokens: int,
    db=None,
    client=None,
    json_mode: bool = False,
) -> str:
    """Run one chat completion and return the stripped text content."""
    settings = get_settings()
    client = client or get_groq_client()
    extra: dict[str, Any] = {"response_format": {"type": "json_object"}} if json_mode else {}

    t0 = time.monotonic()
    try:
        resp = client.chat.completions.create(
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            model=settings.GROQ_MODEL,
            temperature=temperature,
            max_tokens=max_tokens,
            timeout=30,
            **extra,
        )
    except Exception as e:
        latency = (time.monotonic() - t0) * 1000
        log_ai_call(
            logger,
            service=service,
            model=settings.GROQ_MODEL,
            prompt_tokens=0,
            latency_ms=latency,
            success=False,
            error=str(e),
        )
        _persist(
            db,
            service=service,
            prompt_version=prompt_version,
            prompt_tokens=0,
            completion_tokens=0,
            latency_ms=latency,
            success=False,
            error_message=str(e),
        )
        raise GroqAPIError(f"{service} failed: {e}") from e

    latency = (time.monotonic() - t0) * 1000
    usage = getattr(resp, "usage", None)
    prompt_tokens = _as_int(getattr(usage, "prompt_tokens", 0))
    completion_tokens = _as_int(getattr(usage, "completion_tokens", 0))
    log_ai_call(
        logger,
        service=service,
        model=settings.GROQ_MODEL,
        prompt_tokens=prompt_tokens,
        latency_ms=latency,
        success=True,
    )
    _persist(
        db,
        service=service,
        prompt_version=prompt_version,
        prompt_tokens=prompt_tokens,
        completion_tokens=completion_tokens,
        latency_ms=latency,
        success=True,
    )
    return (resp.choices[0].message.content or "").strip()


def parse_json_object(raw: str) -> dict:
    """Extract the first JSON object from an LLM response."""
    raw = (raw or "").strip()
    try:
        value = json.loads(raw)
        if isinstance(value, dict):
            return value
    except json.JSONDecodeError:
        pass
    match = re.search(r"\{.*\}", raw, re.DOTALL)
    if not match:
        raise GroqParseError(f"No JSON found in AI response: {raw[:200]}")
    try:
        return json.loads(match.group())
    except json.JSONDecodeError as e:
        raise GroqParseError(f"Invalid JSON in AI response: {e}") from e


def clamp_score(value: Any) -> float:
    """Coerce an AI-provided score into the 0–100 range."""
    try:
        return max(0.0, min(100.0, float(value)))
    except (TypeError, ValueError):
        return 0.0
