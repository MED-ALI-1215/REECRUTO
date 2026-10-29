"""
Interview flow — the server is the single source of truth.

  start   : questions are frozen on the session — the job's shared questions
            (generated once per job) + one personal question from the candidate's CV
  answer  : one answer per question; scored, checked for prompt injection, stored
  finish  : the browser sends nothing; the result is built from the stored answers and
            the overall score is the average of the per-question scores
"""

import json

from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.exceptions import InterviewStateError, InvalidQuestionError
from app.core.logging import get_logger
from app.models.candidate import Candidate
from app.models.interview import InterviewResult, InterviewSession
from app.models.job import Job
from app.repositories import interview_repo, security_repo
from app.services import interview_service
from app.services.extraction_service import load_profile
from app.services.injection_guard import detector_name, merge, scan, should_neutralise

logger = get_logger(__name__)

NEUTRALISED_FEEDBACK = "This answer could not be evaluated."


# ── Questions ─────────────────────────────────────────────────────────────────


def ensure_job_questions(db: Session, job: Job) -> list[str]:
    """The job's interview questions, generated once and shared by every candidate."""
    if job.interview_questions_json:
        return json.loads(job.interview_questions_json)
    questions = interview_service.generate_questions(
        job.title, job.description, n=get_settings().INTERVIEW_QUESTION_COUNT, db=db
    )
    job.interview_questions_json = json.dumps(questions)
    db.commit()
    logger.info("Job %s: generated %d shared interview questions", job.id, len(questions))
    return questions


def ensure_session_questions(db: Session, session: InterviewSession) -> list[dict]:
    """Freeze the questions on the session the first time the candidate starts."""
    existing = interview_repo.get_questions(session)
    if existing:
        return existing

    job = db.get(Job, session.job_id) if session.job_id else None
    if job is not None:
        base = ensure_job_questions(db, job)
    else:  # invite sent without a saved job
        base = interview_service.generate_questions(
            session.job_title,
            session.job_description,
            n=get_settings().INTERVIEW_QUESTION_COUNT,
            db=db,
        )

    candidate = db.get(Candidate, session.candidate_id) if session.candidate_id else None
    profile = load_profile(candidate.structured_info) if candidate else None

    questions = [{"text": q, "kind": "job"} for q in base]
    questions.append({"text": interview_service.personal_question(profile), "kind": "personal"})
    interview_repo.set_questions(db, session, questions)
    return questions


# ── Answers ───────────────────────────────────────────────────────────────────


def answer_question(db: Session, session: InterviewSession, index: int, answer: str) -> dict:
    questions = interview_repo.get_questions(session)
    if not questions:
        raise InterviewStateError("Start the interview before answering.")
    if not 0 <= index < len(questions):
        raise InvalidQuestionError()
    progress = interview_repo.get_progress(session)
    if progress[index] is not None:
        raise InterviewStateError("This question has already been answered.")

    rules = scan(answer)
    result = interview_service.score_answer(
        questions[index]["text"], answer, session.job_title, session.job_description, db=db
    )
    llm_flag = result["injection_detected"]
    flagged = rules.flagged or llm_flag
    neutralised = should_neutralise(rules, llm_flag)

    if flagged:
        merged = merge(rules, llm_flag, result["injection_reason"], answer)
        security_repo.record_event(
            db,
            source="interview_answer",
            detector=detector_name(rules, llm_flag),
            reasons=merged.reasons,
            excerpt=merged.excerpt,
            candidate_id=session.candidate_id,
            candidate_name=session.candidate_name,
            session_token=session.token,
            question_index=index,
        )

    entry = {
        "answer": answer,
        "score": 0 if neutralised else result["score"],
        "feedback": NEUTRALISED_FEEDBACK if neutralised else result["feedback"],
        "keywords": [] if neutralised else result["keywords"],
        "flagged": flagged,
        "neutralised": neutralised,
    }
    interview_repo.record_answer(db, session, index, entry)
    # Never tell the candidate that a detector fired: it would help them iterate.
    return {"score": entry["score"], "feedback": entry["feedback"], "keywords": entry["keywords"]}


# ── Finish ────────────────────────────────────────────────────────────────────


def finish(db: Session, session: InterviewSession) -> InterviewResult:
    questions = interview_repo.get_questions(session)
    if not questions:
        raise InterviewStateError("The interview has not started.")
    progress = interview_repo.get_progress(session)
    if all(p is None for p in progress):
        raise InterviewStateError("Answer at least one question before finishing.")

    texts = [q["text"] for q in questions]
    answers = [p["answer"] if p else "" for p in progress]
    scores = [
        (
            {"score": p["score"], "feedback": p["feedback"], "keywords": p["keywords"]}
            if p
            else {"score": 0, "feedback": "No answer provided.", "keywords": []}
        )
        for p in progress
    ]
    flagged = [bool(p and p.get("flagged")) for p in progress]

    report = interview_service.generate_final_report(
        session.candidate_name, session.job_title, texts, answers, scores, db=db, flagged=flagged
    )

    red_flags = report.get("red_flags") or ""
    if any(flagged):
        numbers = ", ".join(str(i + 1) for i, f in enumerate(flagged) if f)
        warning = (
            f"Possible prompt-injection attempt in answer(s) {numbers} — review before deciding."
        )
        red_flags = (
            warning if red_flags.strip().lower() in ("", "none") else f"{warning} {red_flags}"
        )

    interview_repo.mark_session_used(db, session.token)
    return interview_repo.save_result(
        db,
        token=session.token,
        candidate_name=session.candidate_name,
        candidate_email=session.candidate_email,
        job_title=session.job_title,
        questions=texts,
        answers=answers,
        scores=scores,
        overall_score=report["overall_score"],
        summary=report.get("summary", ""),
        strengths=report.get("strengths", ""),
        red_flags=red_flags,
        recommendation=report.get("recommendation", "Maybe"),
    )
