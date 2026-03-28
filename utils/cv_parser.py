import PyPDF2
import docx
import io
import re
from typing import Optional

try:
    import pytesseract
    from PIL import Image
    OCR_AVAILABLE = True
except ImportError:
    OCR_AVAILABLE = False


# ─────────────────────────────────────────────────────────────────────────────
# Raw text extractors
# ─────────────────────────────────────────────────────────────────────────────

def extract_text_from_pdf(file) -> str:
    try:
        pdf_reader = PyPDF2.PdfReader(file)
        return "".join(page.extract_text() or "" for page in pdf_reader.pages)
    except Exception as e:
        return f"Error extracting PDF: {str(e)}"


def extract_text_from_docx(file) -> str:
    try:
        doc = docx.Document(file)
        return "\n".join(p.text for p in doc.paragraphs)
    except Exception as e:
        return f"Error extracting DOCX: {str(e)}"


def extract_text_from_image(file) -> str:
    if not OCR_AVAILABLE:
        return "OCR not available — install pytesseract and Pillow."
    try:
        image = Image.open(file)
        return pytesseract.image_to_string(image)
    except Exception as e:
        return f"Error extracting from image: {str(e)}"


def extract_text_from_txt(file) -> str:
    try:
        return file.read().decode("utf-8")
    except Exception as e:
        return f"Error extracting TXT: {str(e)}"


def parse_cv(file) -> str:
    """Dispatch to the correct extractor based on file extension."""
    ext = file.name.split(".")[-1].lower()
    if ext == "pdf":
        return extract_text_from_pdf(file)
    elif ext in ("docx", "doc"):
        return extract_text_from_docx(file)
    elif ext in ("png", "jpg", "jpeg", "tiff", "bmp"):
        return extract_text_from_image(file)
    elif ext == "txt":
        return extract_text_from_txt(file)
    else:
        return "Unsupported file format. Please upload PDF, DOCX, TXT, or image files."


# ─────────────────────────────────────────────────────────────────────────────
# Helpers: extract name & email from raw CV text (fallback, no AI needed)
# ─────────────────────────────────────────────────────────────────────────────

def extract_email_from_text(text: str) -> Optional[str]:
    """Return the first email address found in *text*, or None."""
    pattern = r"[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}"
    matches = re.findall(pattern, text or "")
    return matches[0] if matches else None


def extract_name_from_structured(structured_info: str) -> Optional[str]:
    """
    Parse the name from the AI-generated structured_info block.
    Looks for lines like:
        Full Name: John Doe
        1. Full Name: John Doe
        Name: John Doe
    """
    if not structured_info:
        return None
    for line in structured_info.splitlines():
        line = line.strip()
        m = re.match(
            r"(?:\d+\.\s*)?(?:full\s*name|name)\s*[:\-]\s*(.+)",
            line,
            re.IGNORECASE,
        )
        if m:
            name = m.group(1).strip().strip("*").strip()
            if name and name.lower() not in ("n/a", "unknown", "not provided", ""):
                return name
    return None


def extract_email_from_structured(structured_info: str) -> Optional[str]:
    """
    Parse the email from the AI-generated structured_info block.
    Looks for lines like:
        Email: john@example.com
        2. Email: john@example.com
    Then falls back to a plain regex scan.
    """
    if not structured_info:
        return None
    # Labelled line first
    for line in structured_info.splitlines():
        line = line.strip()
        m = re.match(r"(?:\d+\.\s*)?e[-\s]?mail\s*[:\-]\s*(.+)", line, re.IGNORECASE)
        if m:
            candidate = m.group(1).strip()
            email = extract_email_from_text(candidate)
            if email:
                return email
    # Fallback: any email in the block
    return extract_email_from_text(structured_info)


# ─────────────────────────────────────────────────────────────────────────────
# AI extraction — Groq
# ─────────────────────────────────────────────────────────────────────────────

def extract_cv_info_with_ai(cv_text: str, api_key: str, model: str = "llama-3.3-70b-versatile") -> str:
    """
    Use Groq to extract structured information from CV text.
    Returns a plain-text structured block.
    """
    from groq import Groq

    client = Groq(api_key=api_key)

    prompt = f"""Analyze this CV and extract the following information in a structured format:

CV Text:
{cv_text}

Please extract and clearly label each section:
1. Full Name
2. Email
3. Phone Number
4. Education (degree, institution, year)
5. Work Experience (job title, company, duration, key responsibilities)
6. Skills (technical and soft skills)
7. Certifications
8. Summary / Objective

Use this exact format for the first two fields:
Full Name: <value>
Email: <value>

Then continue with the remaining sections using headers."""

    try:
        response = client.chat.completions.create(
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You are a professional CV analyst. Extract information accurately "
                        "and present it in a clean, structured format. "
                        "Always include 'Full Name:' and 'Email:' as the first two lines."
                    ),
                },
                {"role": "user", "content": prompt},
            ],
            model=model,
            temperature=0.1,
            max_tokens=2000,
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        return f"Error using Groq AI to extract info: {str(e)}"