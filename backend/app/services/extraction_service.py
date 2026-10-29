"""
Structured info extraction service.

The CV extraction prompt (cv_extraction_v2) makes Groq return a JSON profile.
This module validates that JSON into a predictable shape and derives the
compact text fields stored on the candidate. No API calls — pure parsing.
"""

import json
from dataclasses import dataclass, field
from typing import Any


@dataclass
class ParsedCV:
    skills_text: str  # comma-separated list of skills
    experience_text: str  # "title @ company" lines
    certifications_text: str  # one certification per line
    chroma_document: str  # compact text to embed in ChromaDB (signal only, no noise)
    profile: dict = field(default_factory=dict)  # validated JSON profile ({} if legacy)


def _str(value: Any) -> str:
    return str(value).strip() if value not in (None, "") else ""


def _str_list(value: Any) -> list[str]:
    if isinstance(value, str):
        value = value.split(",")
    if not isinstance(value, list):
        return []
    return [s for s in (_str(v) for v in value if not isinstance(v, (dict, list))) if s]


def _clean_items(items: Any, text_keys: tuple[str, ...], list_keys: tuple[str, ...]) -> list[dict]:
    """Keep only dict items, coerce each known key to str / list[str]."""
    out = []
    for item in items if isinstance(items, list) else []:
        if isinstance(item, str):  # model returned a bare string instead of an object
            item = {text_keys[0]: item}
        if not isinstance(item, dict):
            continue
        clean: dict[str, Any] = {k: _str(item.get(k)) for k in text_keys}
        clean.update({k: _str_list(item.get(k)) for k in list_keys})
        if any(clean.values()):
            out.append(clean)
    return out


def load_profile(structured_info: str | None) -> dict | None:
    """
    Parse and validate the JSON profile stored in `candidate.structured_info`.
    Returns None for legacy (markdown) extractions — those CVs must be re-uploaded.
    """
    if not structured_info:
        return None
    try:
        data = json.loads(structured_info)
    except (json.JSONDecodeError, TypeError):
        from app.core.ai import parse_json_object  # tolerate text around the JSON
        from app.core.exceptions import GroqParseError

        try:
            data = parse_json_object(structured_info)
        except GroqParseError:
            return None
    if not isinstance(data, dict):
        return None

    return {
        "full_name": _str(data.get("full_name")),
        "email": _str(data.get("email")),
        "phone": _str(data.get("phone")),
        "summary": _str(data.get("summary")),
        "skills": _str_list(data.get("skills")),
        "soft_skills": _str_list(data.get("soft_skills")),
        "experience": _clean_items(
            data.get("experience"),
            ("title", "company", "duration"),
            ("technologies", "highlights"),
        ),
        "projects": _clean_items(data.get("projects"), ("name", "description"), ("technologies",)),
        "education": _clean_items(data.get("education"), ("degree", "institution", "years"), ()),
        "certifications": _clean_items(data.get("certifications"), ("name", "issuer"), ("skills",)),
        "languages": _str_list(data.get("languages")),
    }


def parse_structured_info(structured_info: str) -> ParsedCV:
    """Turn the stored extraction into compact fields + the ChromaDB document."""
    profile = load_profile(structured_info)
    if profile is None:
        # Legacy / unparseable extraction: keep something searchable
        return ParsedCV("", "", "", (structured_info or "")[:1500], {})

    skills_text = ", ".join(profile["skills"])
    experience_text = "\n".join(
        " @ ".join(p for p in (e["title"], e["company"]) if p) for e in profile["experience"]
    )
    certifications_text = "\n".join(c["name"] for c in profile["certifications"] if c["name"])
    projects_text = "\n".join(
        f"{p['name']}: {', '.join(p['technologies'])}".strip(": ") for p in profile["projects"]
    )

    parts = []
    if profile["summary"]:
        parts.append(profile["summary"])
    if skills_text:
        parts.append(f"Skills: {skills_text}")
    if experience_text:
        parts.append(f"Experience:\n{experience_text}")
    if projects_text:
        parts.append(f"Projects:\n{projects_text}")
    if certifications_text:
        parts.append(f"Certifications:\n{certifications_text}")

    return ParsedCV(
        skills_text=skills_text,
        experience_text=experience_text,
        certifications_text=certifications_text,
        chroma_document="\n\n".join(parts) or (structured_info or "")[:1500],
        profile=profile,
    )
