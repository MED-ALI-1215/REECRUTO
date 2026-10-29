"""
Interview service — LLM calls for interviews (question generation, answer scoring,
final report) and the template-based personal question.

Untrusted text (the candidate's answers) is always wrapped in <candidate_answer>
tags and the model reports injection attempts ("injection_detected").
"""

import re

from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

from app.core.ai import chat_completion, clamp_score, get_groq_client, parse_json_object
from app.core.exceptions import GroqAPIError
from app.core.logging import get_logger
from app.core.prompts import load_prompt
from app.services.injection_guard import scan, wrap_untrusted

logger = get_logger(__name__)

_retry = retry(
    retry=retry_if_exception_type(GroqAPIError),
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=2, max=10),
    reraise=True,
)

GENERIC_PERSONAL_QUESTION = (
    "Describe a personal or academic project you are proud of: what problem it solved, "
    "your role, the main technical challenge and what you would do differently today."
)


def _groq_client():
    # Kept as a separate function so tests can patch it.
    return get_groq_client()


# Kept for backwards compatibility with older imports.
_parse_json_response = parse_json_object


def _as_bool(value) -> bool:
    if isinstance(value, str):
        return value.strip().lower() in ("true", "yes", "1")
    return bool(value)


@_retry
def generate_questions(job_title: str, job_description: str, n: int = 5, db=None) -> list[str]:
    prompt = load_prompt(
        "question_generation_v1.txt", n=n, job_title=job_title, job_description=job_description
    )
    raw = chat_completion(
        service="question_generation",
        prompt_version="question_generation_v1",
        system="You are an expert technical interviewer. Return only the numbered list.",
        user=prompt,
        temperature=0.7,
        max_tokens=2000,
        db=db,
        client=_groq_client(),
    )
    questions = [
        re.sub(r"^\d+[\.\)]\s*", "", line.strip()).strip()
        for line in raw.splitlines()
        if re.match(r"^\d+[\.\)]", line.strip())
    ]
    logger.info("Generated %d questions for '%s'", len(questions), job_title)
    return questions[:n] or [raw]


def personal_question(profile: dict | None) -> str:
    """
    One question about the candidate's own work, built from a template (no LLM):
    the CV is untrusted, so its text never reaches a prompt as instructions.
    """
    if profile:
        for project in profile.get("projects", []):
            name = (project.get("name") or "").strip()[:80]
            if name and not scan(name).flagged:
                techs = ", ".join(t[:30] for t in project.get("technologies", [])[:4])
                tech_part = f" ({techs})" if techs else ""
                return (
                    f"Your CV mentions the project “{name}”{tech_part}. Describe it: the problem "
                    "it solved, your role, the hardest technical challenge and what you would "
                    "do differently today."
                )
        for job in profile.get("experience", []):
            title = (job.get("title") or "").strip()[:80]
            company = (job.get("company") or "").strip()[:80]
            if title and not scan(f"{title} {company}").flagged:
                where = f" at {company}" if company else ""
                return (
                    f"Tell us about your role as {title}{where}: a concrete problem you solved, "
                    "how you approached it and the result."
                )
    return GENERIC_PERSONAL_QUESTION


@_retry
def score_answer(question: str, answer: str, job_title: str, job_description: str, db=None) -> dict:
    """
    Returns {score, feedback, keywords, injection_detected, injection_reason}.
    """
    if not answer or not answer.strip():
        return {
            "score": 0,
            "feedback": "No answer provided.",
            "keywords": [],
            "injection_detected": False,
            "injection_reason": "",
        }

    prompt = load_prompt(
        "answer_scoring_v2.txt",
        job_title=job_title,
        job_description_excerpt=job_description[:500],
        question=question,
        answer_block=wrap_untrusted(answer, "candidate_answer"),
    )
    raw = chat_completion(
        service="answer_scoring",
        prompt_version="answer_scoring_v2",
        system=load_prompt("answer_scoring_v2_system.txt"),
        user=prompt,
        temperature=0.2,
        max_tokens=1500,
        db=db,
        client=_groq_client(),
        json_mode=True,
    )
    result = parse_json_object(raw)
    keywords = result.get("keywords") or []
    return {
        "score": clamp_score(result.get("score")),
        "feedback": str(result.get("feedback", "")),
        "keywords": [str(k) for k in keywords] if isinstance(keywords, list) else [],
        "injection_detected": _as_bool(result.get("injection_detected", False)),
        "injection_reason": str(result.get("injection_reason") or ""),
    }


@_retry
def generate_final_report(
    candidate_name: str,
    job_title: str,
    questions: list,
    answers: list,
    scores: list,
    db=None,
    flagged: list[bool] | None = None,
) -> dict:
    """
    Narrative report (summary, strengths, red flags, recommendation).
    The overall score is the average of the per-question scores, computed here —
    never taken from the model, so answers cannot talk their way to a better grade.
    """
    flagged = flagged or [False] * len(questions)
    per_question = [clamp_score(s.get("score", 0)) for s in scores]
    average = round(sum(per_question) / len(per_question), 1) if per_question else 0.0

    lines = []
    for i, (q, a, s, f) in enumerate(zip(questions, answers, scores, flagged, strict=False)):
        shown = "[withheld]" if f else (a or "[no answer]")
        lines.append(f"Q{i + 1}: {q}\nA: {shown}\nScore: {s.get('score', 0)}/100")
    prompt = load_prompt(
        "final_report_v2.txt",
        job_title=job_title,
        candidate_name=candidate_name,
        average_score=average,
        transcript_block=wrap_untrusted("\n\n".join(lines), "interview_transcript"),
    )
    raw = chat_completion(
        service="final_report",
        prompt_version="final_report_v2",
        system="You are a senior hiring manager. Respond only with valid JSON.",
        user=prompt,
        temperature=0.3,
        max_tokens=2000,
        db=db,
        client=_groq_client(),
        json_mode=True,
    )
    result = parse_json_object(raw)
    result["overall_score"] = average
    logger.info(
        "Final report: candidate=%s score=%s recommendation=%s",
        candidate_name,
        average,
        result.get("recommendation"),
    )
    return result
