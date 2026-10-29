"""
Interview service — question generation and answer scoring via Groq.
"""

import json
import re
import time

from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

from app.core.config import get_settings
from app.core.exceptions import GroqAPIError, GroqParseError
from app.core.logging import get_logger, log_ai_call
from app.core.prompts import load_prompt

logger = get_logger(__name__)


def _groq_client():
    from groq import Groq

    return Groq(api_key=get_settings().GROQ_API_KEY)


def _parse_json_response(raw: str) -> dict:
    match = re.search(r"\{.*\}", raw, re.DOTALL)
    if not match:
        raise GroqParseError(f"No JSON found in AI response: {raw[:200]}")
    try:
        return json.loads(match.group())
    except json.JSONDecodeError as e:
        raise GroqParseError(f"Invalid JSON in AI response: {e}") from e


def _persist(
    db,
    *,
    service: str,
    prompt_version: str,
    prompt_tokens: int,
    completion_tokens: int,
    latency_ms: float,
    success: bool,
    error_message: str | None = None,
):
    if db is None:
        return
    try:
        from app.repositories.ai_call_repo import record_ai_call

        record_ai_call(
            db,
            service=service,
            model=get_settings().GROQ_MODEL,
            prompt_version=prompt_version,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            latency_ms=latency_ms,
            success=success,
            error_message=error_message,
        )
    except Exception as e:
        logger.warning("Could not persist AI call record: %s", e)


@retry(
    retry=retry_if_exception_type(GroqAPIError),
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=2, max=10),
    reraise=True,
)
def generate_questions(job_title: str, job_description: str, n: int = 5, db=None) -> list[str]:
    settings = get_settings()
    prompt = load_prompt(
        "question_generation_v1.txt", n=n, job_title=job_title, job_description=job_description
    )
    t0 = time.monotonic()
    try:
        resp = _groq_client().chat.completions.create(
            messages=[
                {
                    "role": "system",
                    "content": "You are an expert technical interviewer. Return only the numbered list.",
                },
                {"role": "user", "content": prompt},
            ],
            model=settings.GROQ_MODEL,
            temperature=0.7,
            max_tokens=800,
            timeout=30,
        )
        latency = (time.monotonic() - t0) * 1000
        log_ai_call(
            logger,
            service="question_generation",
            model=settings.GROQ_MODEL,
            prompt_tokens=resp.usage.prompt_tokens,
            latency_ms=latency,
            success=True,
        )
        _persist(
            db,
            service="question_generation",
            prompt_version="question_generation_v1",
            prompt_tokens=resp.usage.prompt_tokens,
            completion_tokens=resp.usage.completion_tokens,
            latency_ms=latency,
            success=True,
        )

        raw = resp.choices[0].message.content.strip()
        questions = [
            re.sub(r"^\d+[\.\)]\s*", "", line).strip()
            for line in raw.splitlines()
            if re.match(r"^\d+[\.\)]", line.strip())
        ]
        logger.info("Generated %d questions for '%s'", len(questions), job_title)
        return questions or [raw]

    except GroqAPIError:
        raise
    except Exception as e:
        latency = (time.monotonic() - t0) * 1000
        log_ai_call(
            logger,
            service="question_generation",
            model=settings.GROQ_MODEL,
            prompt_tokens=0,
            latency_ms=latency,
            success=False,
            error=str(e),
        )
        _persist(
            db,
            service="question_generation",
            prompt_version="question_generation_v1",
            prompt_tokens=0,
            completion_tokens=0,
            latency_ms=latency,
            success=False,
            error_message=str(e),
        )
        raise GroqAPIError(f"Question generation failed: {e}") from e


@retry(
    retry=retry_if_exception_type(GroqAPIError),
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=2, max=10),
    reraise=True,
)
def score_answer(question: str, answer: str, job_title: str, job_description: str, db=None) -> dict:
    if not answer or not answer.strip():
        return {"score": 0, "feedback": "No answer provided.", "keywords": []}

    settings = get_settings()
    prompt = load_prompt(
        "answer_scoring_v1.txt",
        job_title=job_title,
        job_description_excerpt=job_description[:500],
        question=question,
        answer=answer,
    )
    t0 = time.monotonic()
    try:
        resp = _groq_client().chat.completions.create(
            messages=[
                {
                    "role": "system",
                    "content": "You are a technical interviewer. Respond only with valid JSON.",
                },
                {"role": "user", "content": prompt},
            ],
            model=settings.GROQ_MODEL,
            temperature=0.3,
            max_tokens=400,
            timeout=30,
        )
        latency = (time.monotonic() - t0) * 1000
        log_ai_call(
            logger,
            service="answer_scoring",
            model=settings.GROQ_MODEL,
            prompt_tokens=resp.usage.prompt_tokens,
            latency_ms=latency,
            success=True,
        )
        _persist(
            db,
            service="answer_scoring",
            prompt_version="answer_scoring_v1",
            prompt_tokens=resp.usage.prompt_tokens,
            completion_tokens=resp.usage.completion_tokens,
            latency_ms=latency,
            success=True,
        )
        return _parse_json_response(resp.choices[0].message.content.strip())

    except (GroqParseError, GroqAPIError):
        raise
    except Exception as e:
        latency = (time.monotonic() - t0) * 1000
        log_ai_call(
            logger,
            service="answer_scoring",
            model=settings.GROQ_MODEL,
            prompt_tokens=0,
            latency_ms=latency,
            success=False,
            error=str(e),
        )
        _persist(
            db,
            service="answer_scoring",
            prompt_version="answer_scoring_v1",
            prompt_tokens=0,
            completion_tokens=0,
            latency_ms=latency,
            success=False,
            error_message=str(e),
        )
        raise GroqAPIError(f"Answer scoring failed: {e}") from e


@retry(
    retry=retry_if_exception_type(GroqAPIError),
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=2, max=10),
    reraise=True,
)
def generate_final_report(
    candidate_name: str, job_title: str, questions: list, answers: list, scores: list, db=None
) -> dict:
    settings = get_settings()
    qa_summary = "\n".join(
        f"Q{i+1}: {q}\nA: {a}\nScore: {s.get('score', 0)}/100"
        for i, (q, a, s) in enumerate(zip(questions, answers, scores, strict=False))
    )
    prompt = load_prompt(
        "final_report_v1.txt",
        job_title=job_title,
        candidate_name=candidate_name,
        qa_summary=qa_summary,
    )
    t0 = time.monotonic()
    try:
        resp = _groq_client().chat.completions.create(
            messages=[
                {
                    "role": "system",
                    "content": "You are a senior hiring manager. Respond only with valid JSON.",
                },
                {"role": "user", "content": prompt},
            ],
            model=settings.GROQ_MODEL,
            temperature=0.3,
            max_tokens=600,
            timeout=30,
        )
        latency = (time.monotonic() - t0) * 1000
        log_ai_call(
            logger,
            service="final_report",
            model=settings.GROQ_MODEL,
            prompt_tokens=resp.usage.prompt_tokens,
            latency_ms=latency,
            success=True,
        )
        _persist(
            db,
            service="final_report",
            prompt_version="final_report_v1",
            prompt_tokens=resp.usage.prompt_tokens,
            completion_tokens=resp.usage.completion_tokens,
            latency_ms=latency,
            success=True,
        )

        result = _parse_json_response(resp.choices[0].message.content.strip())
        logger.info(
            "Final report: candidate=%s score=%s recommendation=%s",
            candidate_name,
            result.get("overall_score"),
            result.get("recommendation"),
        )
        return result

    except (GroqParseError, GroqAPIError):
        raise
    except Exception as e:
        latency = (time.monotonic() - t0) * 1000
        log_ai_call(
            logger,
            service="final_report",
            model=settings.GROQ_MODEL,
            prompt_tokens=0,
            latency_ms=latency,
            success=False,
            error=str(e),
        )
        _persist(
            db,
            service="final_report",
            prompt_version="final_report_v1",
            prompt_tokens=0,
            completion_tokens=0,
            latency_ms=latency,
            success=False,
            error_message=str(e),
        )
        raise GroqAPIError(f"Final report generation failed: {e}") from e
