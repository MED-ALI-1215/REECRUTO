"""
CV parsing and AI extraction service.
No Streamlit, no HTTP — plain Python in, plain Python out.
"""

import io
import re
import time
import uuid

from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

from app.core.config import get_settings
from app.core.exceptions import CVExtractionError, GroqAPIError, UnsupportedFileTypeError
from app.core.logging import get_logger, log_ai_call
from app.core.prompts import load_prompt

logger = get_logger(__name__)

PROMPT_VERSION = "cv_extraction_v1"


# ── Text extractors ───────────────────────────────────────────────────────────


def _extract_pdf(data: bytes) -> str:
    import PyPDF2

    reader = PyPDF2.PdfReader(io.BytesIO(data))
    text = "".join(page.extract_text() or "" for page in reader.pages)
    if not text.strip():
        raise CVExtractionError("PDF appears to be empty or image-only (no extractable text).")
    return text


def _extract_docx(data: bytes) -> str:
    import docx

    doc = docx.Document(io.BytesIO(data))
    text = "\n".join(p.text for p in doc.paragraphs)
    if not text.strip():
        raise CVExtractionError("DOCX file appears to be empty.")
    return text


def _extract_image(data: bytes) -> str:
    try:
        import pytesseract
        from PIL import Image
    except ImportError as err:
        raise CVExtractionError("OCR not available — install pytesseract and Pillow.") from err
    text = pytesseract.image_to_string(Image.open(io.BytesIO(data)))
    if not text.strip():
        raise CVExtractionError("No text could be extracted from the image.")
    return text


def _extract_txt(data: bytes) -> str:
    text = data.decode("utf-8", errors="replace")
    if not text.strip():
        raise CVExtractionError("Text file is empty.")
    return text


_EXTRACTORS = {
    "pdf": _extract_pdf,
    "docx": _extract_docx,
    "doc": _extract_docx,
    "txt": _extract_txt,
    "png": _extract_image,
    "jpg": _extract_image,
    "jpeg": _extract_image,
}


def extract_text(filename: str, data: bytes) -> str:
    ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
    fn = _EXTRACTORS.get(ext)
    if fn is None:
        raise UnsupportedFileTypeError(f"Unsupported file type: .{ext}")
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
    Use Groq to extract structured info from raw CV text.
    db is optional — if provided, the AI call is persisted to the ai_calls table.
    """
    from groq import Groq

    settings = get_settings()

    user_prompt = load_prompt(f"{PROMPT_VERSION}.txt", cv_text=cv_text)
    system_prompt = load_prompt(f"{PROMPT_VERSION}_system.txt")

    client = Groq(api_key=settings.GROQ_API_KEY)
    t0 = time.monotonic()
    try:
        response = client.chat.completions.create(
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            model=settings.GROQ_MODEL,
            temperature=0.1,
            max_tokens=2000,
            timeout=30,
        )
        latency = (time.monotonic() - t0) * 1000
        prompt_tokens = response.usage.prompt_tokens
        completion_tokens = response.usage.completion_tokens

        log_ai_call(
            logger,
            service="cv_extraction",
            model=settings.GROQ_MODEL,
            prompt_tokens=prompt_tokens,
            latency_ms=latency,
            success=True,
        )

        if db is not None:
            from app.repositories.ai_call_repo import record_ai_call

            record_ai_call(
                db,
                service="cv_extraction",
                model=settings.GROQ_MODEL,
                prompt_version=PROMPT_VERSION,
                prompt_tokens=prompt_tokens,
                completion_tokens=completion_tokens,
                latency_ms=latency,
                success=True,
            )

        return response.choices[0].message.content.strip()

    except Exception as e:
        latency = (time.monotonic() - t0) * 1000
        log_ai_call(
            logger,
            service="cv_extraction",
            model=settings.GROQ_MODEL,
            prompt_tokens=0,
            latency_ms=latency,
            success=False,
            error=str(e),
        )
        if db is not None:
            from app.repositories.ai_call_repo import record_ai_call

            record_ai_call(
                db,
                service="cv_extraction",
                model=settings.GROQ_MODEL,
                prompt_version=PROMPT_VERSION,
                prompt_tokens=0,
                completion_tokens=0,
                latency_ms=latency,
                success=False,
                error_message=str(e),
            )
        raise GroqAPIError(f"Groq CV extraction failed: {e}") from e


# ── Helpers ───────────────────────────────────────────────────────────────────


def extract_email_from_text(text: str) -> str | None:
    pattern = r"[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}"
    matches = re.findall(pattern, text or "")
    return matches[0] if matches else None


def extract_name_from_structured(structured_info: str) -> str | None:
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
    for line in (structured_info or "").splitlines():
        m = re.match(r"(?:\d+\.\s*)?e[-\s]?mail\s*[:\-]\s*(.+)", line.strip(), re.IGNORECASE)
        if m:
            email = extract_email_from_text(m.group(1).strip())
            if email:
                return email
    return extract_email_from_text(structured_info)


def generate_candidate_id() -> str:
    return uuid.uuid4().hex
