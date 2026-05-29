"""
Structured info extraction service.
Parses the text block that Groq returns from CV extraction into
discrete semantic fields: skills, experience, certifications.

No API calls — pure text parsing.
"""

import re
from dataclasses import dataclass


@dataclass
class ParsedCV:
    skills_text: str  # comma-separated list of skills
    experience_text: str  # job titles + companies, one per line
    certifications_text: str
    chroma_document: str  # compact text to embed in ChromaDB (signal only, no noise)


# ── Section header patterns ───────────────────────────────────────────────────

_SECTION_PATTERNS = {
    "skills": re.compile(
        r"(?:^|\n)\s*(?:\d+\.\s*)?(?:skills?|technical skills?|core competenc(?:y|ies)|technologies)\s*[:\-]?\s*\n",
        re.IGNORECASE,
    ),
    "experience": re.compile(
        r"(?:^|\n)\s*(?:\d+\.\s*)?(?:work experience|experience|employment(?: history)?|professional background)\s*[:\-]?\s*\n",
        re.IGNORECASE,
    ),
    "certifications": re.compile(
        r"(?:^|\n)\s*(?:\d+\.\s*)?(?:certifications?|certificates?|licenses?|credentials?)\s*[:\-]?\s*\n",
        re.IGNORECASE,
    ),
    "projects": re.compile(
        r"(?:^|\n)\s*(?:\d+\.\s*)?(?:projects?|personal projects?|key projects?)\s*[:\-]?\s*\n",
        re.IGNORECASE,
    ),
    "education": re.compile(r"(?:^|\n)\s*(?:\d+\.\s*)?education\s*[:\-]?\s*\n", re.IGNORECASE),
}

# Next-section pattern — used to find where a section ends
_NEXT_SECTION = re.compile(
    r"(?:^|\n)\s*(?:\d+\.\s*)?(?:skills?|technical skills?|work experience|experience|employment"
    r"|certifications?|projects?|education|summary|objective|references?|languages?)\s*[:\-]?\s*\n",
    re.IGNORECASE,
)


def _extract_section(text: str, pattern: re.Pattern) -> str:
    """Extract the content of a named section, stopping at the next section header."""
    m = pattern.search(text)
    if not m:
        return ""
    start = m.end()
    # Find next section header after this one
    next_m = _NEXT_SECTION.search(text, start)
    end = next_m.start() if next_m else len(text)
    return text[start:end].strip()


def _clean_lines(raw: str) -> list[str]:
    """Return non-empty, stripped lines from a section block."""
    return [
        re.sub(r"^[\-\*\•]\s*", "", line).strip()
        for line in raw.splitlines()
        if line.strip() and not re.match(r"^\s*[\-\*\•]\s*$", line)
    ]


def parse_structured_info(structured_info: str) -> ParsedCV:
    """
    Parse Groq's structured CV output into discrete semantic fields.
    Returns a ParsedCV with all fields populated (empty string if not found).
    """
    text = structured_info or ""

    # ── Skills ────────────────────────────────────────────────────────────────
    skills_raw = _extract_section(text, _SECTION_PATTERNS["skills"])
    # Also pick up inline "Skills: Python, FastAPI, ..." lines
    inline_skills = re.findall(r"(?:skills?|technologies)\s*[:\-]\s*(.+)", text, re.IGNORECASE)
    skills_lines = _clean_lines(skills_raw) + [s.strip() for s in inline_skills]
    # Flatten comma-separated items within lines
    skills_flat = []
    for line in skills_lines:
        skills_flat.extend([s.strip() for s in re.split(r"[,;|]", line) if s.strip()])
    skills_text = ", ".join(dict.fromkeys(skills_flat))  # deduplicate, preserve order

    # ── Experience ────────────────────────────────────────────────────────────
    exp_raw = _extract_section(text, _SECTION_PATTERNS["experience"])
    exp_lines = _clean_lines(exp_raw)
    # Keep only lines that look like job titles or companies (not bullet responsibilities)
    title_lines = [
        line
        for line in exp_lines
        if len(line) < 120
        and not line.lower().startswith(
            ("responsible", "developed", "managed", "led", "built", "worked", "collaborated")
        )
    ]
    experience_text = "\n".join(title_lines[:20])  # cap at 20 lines

    # ── Certifications ────────────────────────────────────────────────────────
    cert_raw = _extract_section(text, _SECTION_PATTERNS["certifications"])
    cert_lines = _clean_lines(cert_raw)
    # Also pick up inline cert mentions
    inline_certs = re.findall(
        r"(?:certified?|certification)\s+(?:in\s+)?([A-Z][^\n,\.]{3,60})", text
    )
    cert_lines += inline_certs
    certifications_text = "\n".join(dict.fromkeys(cert_lines))

    # ── Projects ─────────────────────────────────────────────────────────────
    proj_raw = _extract_section(text, _SECTION_PATTERNS["projects"])
    proj_lines = _clean_lines(proj_raw)
    projects_text = "\n".join(proj_lines[:10])

    # ── ChromaDB document: compact, signal-rich embedding text ────────────────
    parts = []
    if skills_text:
        parts.append(f"Skills: {skills_text}")
    if experience_text:
        parts.append(f"Experience:\n{experience_text}")
    if projects_text:
        parts.append(f"Projects:\n{projects_text}")
    if certifications_text:
        parts.append(f"Certifications:\n{certifications_text}")

    # Fallback: if parsing found nothing, use first 1500 chars of structured_info
    chroma_document = "\n\n".join(parts) if parts else text[:1500]

    return ParsedCV(
        skills_text=skills_text,
        experience_text=experience_text,
        certifications_text=certifications_text,
        chroma_document=chroma_document,
    )
