"""
Prompt loader — reads versioned prompt templates from the prompts/ directory.
Services call load_prompt() instead of writing f-strings inline.
"""
from pathlib import Path
from functools import lru_cache

_PROMPTS_DIR = Path(__file__).parent.parent.parent / "prompts"


@lru_cache(maxsize=None)
def _read(filename: str) -> str:
    path = _PROMPTS_DIR / filename
    if not path.exists():
        raise FileNotFoundError(f"Prompt file not found: {path}")
    return path.read_text(encoding="utf-8")


def load_prompt(name: str, **kwargs) -> str:
    """
    Load a prompt template and substitute keyword arguments.

    Usage:
        load_prompt("cv_extraction_v1.txt", cv_text=raw_text)
        load_prompt("question_generation_v1.txt", n=5, job_title="Engineer", job_description="...")
    """
    template = _read(name)
    return template.format(**kwargs) if kwargs else template
