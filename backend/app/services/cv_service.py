"""
CV parsing and AI extraction service.
No Streamlit, no HTTP — plain Python in, plain Python out.
"""

import io
import json
import re
import uuid

from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

from app.core.ai import chat_completion, parse_json_object
from app.core.exceptions import (
    CVExtractionError,
    GroqAPIError,
    GroqParseError,
    UnsupportedFileTypeError,
)
from app.core.logging import get_logger
from app.core.prompts import load_prompt
from app.services.injection_guard import GuardResult, detector_name, merge, scan, wrap_untrusted

logger = get_logger(__name__)

PROMPT_VERSION = "cv_extraction_v3"
# Very long CVs blow the context window and cost tokens for little gain
MAX_CV_CHARS = 20_000


# ── Text extractors ───────────────────────────────────────────────────────────


SUPPORTED_FORMATS = "PDF (with selectable text), DOCX or TXT"
# Below this many letters/digits, a PDF is treated as a scan / image-only document
MIN_TEXT_CHARS = 50


def _extract_pdf(data: bytes) -> str:
    import PyPDF2

    try:
        reader = PyPDF2.PdfReader(io.BytesIO(data))
        text = "\n".join(page.extract_text() or "" for page in reader.pages)
    except Exception as e:
        raise CVExtractionError(
            f"This PDF could not be read (it may be corrupted or password-protected). "
            f"Please upload a {SUPPORTED_FORMATS} file."
        ) from e
    if sum(c.isalnum() for c in text) < MIN_TEXT_CHARS:
        raise CVExtractionError(
            "This PDF contains no selectable text — it is probably a scan or an image. "
            f"Image-based CVs are not supported: please upload a {SUPPORTED_FORMATS} file."
        )
    return text


def _extract_docx(data: bytes) -> str:
    import docx

    try:
        doc = docx.Document(io.BytesIO(data))
    except Exception as e:
        raise CVExtractionError(
            f"This DOCX file could not be read. Please upload a {SUPPORTED_FORMATS} file."
        ) from e
    text = "\n".join(p.text for p in doc.paragraphs)
    if not text.strip():
        raise CVExtractionError("This DOCX file is empty.")
    return text


def _extract_txt(data: bytes) -> str:
    text = data.decode("utf-8", errors="replace")
    if not text.strip():
        raise CVExtractionError("This text file is empty.")
    return text


_EXTRACTORS = {
    "pdf": _extract_pdf,
    "docx": _extract_docx,
    "txt": _extract_txt,
}


def extract_text(filename: str, data: bytes) -> str:
    ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
    fn = _EXTRACTORS.get(ext)
    if fn is None:
        raise UnsupportedFileTypeError(
            f"File type .{ext} is not allowed. Please upload a {SUPPORTED_FORMATS} file."
        )
    logger.info("Extracting text from %s (%d bytes)", filename, len(data))
    return fn(data)


# ── AI extraction ─────────────────────────────────────────────────────────────


@retry(
    retry=retry_if_exception_type(GroqAPIError),
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=2, max=10),
    reraise=True,
)
def extract_cv_info_with_ai(cv_text: str, db=None) -> str:
    """
    Use Groq to extract a structured JSON profile from raw CV text.
    Returns the profile as pretty-printed JSON (stored in candidate.structured_info).
    db is optional — if provided, the AI call is persisted to the ai_calls table.
    """
    raw = chat_completion(
        service="cv_extraction",
        prompt_version=PROMPT_VERSION,
        system=load_prompt(f"{PROMPT_VERSION}_system.txt"),
        user=load_prompt(
            f"{PROMPT_VERSION}.txt", cv_block=wrap_untrusted(cv_text[:MAX_CV_CHARS], "cv")
        ),
        temperature=0.1,
        max_tokens=6000,  # gpt-oss models spend part of the budget on reasoning
        db=db,
        json_mode=True,
    )
    try:
        return json.dumps(parse_json_object(raw), ensure_ascii=False, indent=2)
    except GroqParseError as e:
        # Retry once more through tenacity: the model sometimes truncates its JSON
        raise GroqAPIError(f"CV extraction returned invalid JSON: {e}") from e


# ── Helpers ───────────────────────────────────────────────────────────────────


def extract_email_from_text(text: str) -> str | None:
    pattern = r"[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}"
    matches = re.findall(pattern, text or "")
    return matches[0] if matches else None


def extract_name_from_structured(structured_info: str) -> str | None:
    from app.services.extraction_service import load_profile

    profile = load_profile(structured_info)
    if profile is not None:
        return profile["full_name"] or None
    for line in (structured_info or "").splitlines():
        m = re.match(
            r"(?:\d+\.\s*)?(?:full\s*name|name)\s*[:\-]\s*(.+)", line.strip(), re.IGNORECASE
        )
        if m:
            name = m.group(1).strip().strip("*").strip()
            if name and name.lower() not in ("n/a", "unknown", "not provided", ""):
                return name
    return None


def extract_email_from_structured(structured_info: str) -> str | None:
    from app.services.extraction_service import load_profile

    profile = load_profile(structured_info)
    if profile is not None and profile["email"]:
        return extract_email_from_text(profile["email"])
    for line in (structured_info or "").splitlines():
        m = re.match(r"(?:\d+\.\s*)?e[-\s]?mail\s*[:\-]\s*(.+)", line.strip(), re.IGNORECASE)
        if m:
            email = extract_email_from_text(m.group(1).strip())
            if email:
                return email
    return extract_email_from_text(structured_info)


def generate_candidate_id() -> str:
    return uuid.uuid4().hex


def check_cv_injection(cv_text: str, structured_info: str) -> tuple[GuardResult, str]:
    """
    Combine the rule-based scan of the raw CV text (which includes hidden/white text)
    with the LLM's own report from the extraction. Returns (result, detector name).
    """
    rules = scan(cv_text)
    try:
        data = json.loads(structured_info)
    except (json.JSONDecodeError, TypeError):
        data = {}
    llm_flag = str(data.get("injection_detected", "")).strip().lower() in ("true", "1", "yes")
    merged = merge(rules, llm_flag, str(data.get("injection_reason") or ""), cv_text)
    return merged, detector_name(rules, llm_flag)
