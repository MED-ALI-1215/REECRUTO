"""
Prompt-injection guard for untrusted text (CVs, interview answers).

Defense in depth — no single layer is trusted on its own:

  1. Rules (this module) — fast regex patterns, English + French, run BEFORE the LLM.
  2. Isolation — untrusted text is wrapped in <tags> the model is told to treat as data;
     `wrap_untrusted` neutralises attempts to close those tags early.
  3. LLM self-report — prompts ask for "injection_detected" / "injection_reason".

Policy (see `should_neutralise`): an input is neutralised (answer scored 0) when
the LLM confirms the attempt, or when 2+ different rules fire. A single rule hit
the LLM does not confirm is only flagged for review — rules alone can misfire
(e.g. a candidate *describing* prompt injection). Every hit is recorded as a
SecurityEvent for the recruiter.
"""

import re
import unicodedata
from dataclasses import dataclass, field

# Invisible characters used to hide or split keywords ("ig<zero-width space>nore")
_INVISIBLE = re.compile("[\u200b-\u200f\u2060-\u2064\ufeff\u00ad]")

# Patterns target IMPERATIVES aimed at the evaluator, not the topic itself: an AI
# engineer may legitimately talk about "system prompts" or prompt injection.
# (reason shown to the recruiter, pattern on normalised lowercase text without accents)
_PATTERNS: list[tuple[str, re.Pattern]] = [
    (
        "Asks the AI to ignore its instructions",
        re.compile(
            r"\b(ignore|disregard|forget|override|bypass)\s+(all\s+|any\s+)?(of\s+)?"
            r"(the\s+|your\s+|these\s+|those\s+)?"
            r"(previous|prior|above|earlier|preceding|system|initial|original)\s+"
            r"(instructions?|prompts?|rules?|guidelines?|directives?)"
            r"|\b(ignore|disregard|forget)\s+(all\s+)?your\s+"
            r"(instructions?|rules?|guidelines?|programming)"
        ),
    ),
    (
        "Asks the AI to ignore its instructions (FR)",
        re.compile(
            r"\b(ignore[rz]?|oublie[rz]?|outrepasse[rz]?)\s+(toutes\s+)?"
            r"((tes|vos)\s+(instructions?|consignes?|regles?)"
            r"|les\s+(instructions?|consignes?|regles?)\s+"
            r"(precedentes?|anterieures?|du systeme|initiales?))"
        ),
    ),
    (
        "Tries to change the AI's role",
        re.compile(
            r"\b(you are now|from now on,? you (are|will)|pretend (to be|you are)|roleplay as"
            r"|act as (an? )?(ai|assistant|evaluator|grader|recruiter|interviewer"
            r"|hiring manager|system|chatgpt|gpt|llm)"
            r"|tu es (maintenant|desormais)|fais comme si tu etais"
            r"|agis (maintenant |desormais )?comme (un |une )?"
            r"(ia|assistant|evaluateur|recruteur|correcteur))\b"
        ),
    ),
    (
        "Asks the AI to reveal its prompt",
        re.compile(
            r"\b(reveal|show|print|repeat|output)\s+(me\s+)?(your|the)\s+(system\s+)?"
            r"(prompt|instructions)\b|\b(affiche|revele|repete)\s+(ton|le)\s+prompt\b"
        ),
    ),
    (
        "Contains chat role markers",
        re.compile(
            r"<\|?(im_start|im_end|system|assistant)\|?>|\[/?inst\]|<</?sys>>"
            r"|###\s*(system|instructions?)\b"
        ),
    ),
    (
        "Tries to dictate its own score",
        re.compile(
            r"\b(give|assign|award|rate|score|grade|mark)\s+"
            r"(me|this (answer|response|candidate)|my (answer|response))\b.{0,25}"
            r"\b(100|10\s*/\s*10|full marks?|maximum|max|perfect|highest)\b"
            r"|\b(donne|donnez|attribue|attribuez|mets|mettez|accorde|accordez)"
            r"(-|\s+)(moi|lui)\b.{0,25}"
            r"\b(100|10\s*/\s*10|20\s*/\s*20|note maximale|la meilleure note|maximum)\b"
            r"|[\"'](overall_)?score[\"']\s*:\s*\d"
            r"|[\"']?injection_detected[\"']?\s*:\s*false"
        ),
    ),
    (
        "Tells the AI how to rank this candidate",
        re.compile(
            r"\b(rank|classify|score|rate|list)\s+(this|the)\s+candidate\s+(as\s+)?"
            r"(the\s+)?(first|top|#1|number one|highest|best)\b"
            r"|\bclasse[rz]?\s+ce\s+candidat\s+(en\s+)?(premier|tete|numero un)\b"
            r"|\b(note|message|instructions?)\s+(to|for)\s+(the\s+)?"
            r"(ai|llm|model|chatgpt|gpt|recruiter ai|ats)\b"
        ),
    ),
    (
        "Tries to close the data delimiters",
        re.compile(r"</\s*(candidate_answer|cv|untrusted|data)\s*>"),
    ),
]

_EXCERPT_RADIUS = 120


@dataclass
class GuardResult:
    flagged: bool = False
    reasons: list[str] = field(default_factory=list)
    excerpt: str = ""


def normalize(text: str) -> str:
    """Lowercase, strip accents and invisible characters, collapse whitespace."""
    text = _INVISIBLE.sub("", text or "")
    text = unicodedata.normalize("NFKD", text)
    text = "".join(c for c in text if not unicodedata.combining(c))
    return re.sub(r"[ \t]+", " ", text.lower())


def scan(text: str) -> GuardResult:
    """Run the rule-based detector on untrusted text."""
    norm = normalize(text)
    result = GuardResult()
    for reason, pattern in _PATTERNS:
        match = pattern.search(norm)
        if match:
            result.flagged = True
            result.reasons.append(reason)
            if not result.excerpt:
                start = max(0, match.start() - _EXCERPT_RADIUS)
                result.excerpt = norm[start : match.end() + _EXCERPT_RADIUS].strip()
    return result


def wrap_untrusted(text: str, tag: str) -> str:
    """
    Put untrusted text inside <tag>...</tag> and neutralise any attempt to open or
    close the tag from inside, so the text cannot "escape" into the instructions.
    """
    safe = re.sub(rf"<\s*/?\s*{tag}\s*>", "[removed tag]", text or "", flags=re.IGNORECASE)
    return f"<{tag}>\n{safe}\n</{tag}>"


def merge(rule_result: GuardResult, llm_flag: bool, llm_reason: str, text: str) -> GuardResult:
    """Combine the rule-based result with the LLM's self-report."""
    if not llm_flag:
        return rule_result
    reasons = list(rule_result.reasons)
    reasons.append(f"AI evaluator: {llm_reason}" if llm_reason else "Flagged by the AI evaluator")
    excerpt = rule_result.excerpt or normalize(text)[: 2 * _EXCERPT_RADIUS]
    return GuardResult(True, reasons, excerpt)


def detector_name(rule_result: GuardResult, llm_flag: bool) -> str:
    if rule_result.flagged and llm_flag:
        return "rules+llm"
    return "llm" if llm_flag else "rules"


def should_neutralise(rule_result: GuardResult, llm_flag: bool) -> bool:
    """Score 0 when the LLM confirms, or when several independent rules agree."""
    return llm_flag or len(rule_result.reasons) >= 2
