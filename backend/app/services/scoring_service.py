"""
Evidence-based scoring — zero API calls.

For every skill the job asks for, look for proof in the candidate's profile:

    listed in "skills" only ........ 0.4
    used in a project .............. 0.8
    used in professional experience  1.0
    covered by a certification ..... +0.2 (capped at 1.0)

    score = 0.70 × required coverage + 0.20 × nice-to-have coverage + 0.10 × soft skills

Categories the job doesn't mention are dropped and the weights re-normalised
(no nice-to-have → 0.90 / 0.10). Each skill keeps the list of sources that
proved it, so the recruiter sees *why* a candidate got their score.

When a job skill has no exact match, semantically similar skills found by
ChromaDB ("torch" for "pytorch") can prove it, at SEMANTIC_MATCH_FACTOR of the
evidence (a similar skill is weaker proof than the exact one).
"""

from dataclasses import asdict, dataclass, field

from app.services.skills import expand, normalize_list, skill_in_set, skill_in_text

SCORING_VERSION = "evidence_v2"  # bump when the formula changes: old matches get rescored

WEIGHTS = {"required": 0.70, "nice": 0.20, "soft": 0.10}
EVIDENCE_LISTED = 0.4
EVIDENCE_PROJECT = 0.8
EVIDENCE_EXPERIENCE = 1.0
CERT_BONUS = 0.2
DEFAULT_SEMANTIC_FACTOR = 0.8
STRONG_THRESHOLD = 0.8  # >= this counts as "matched", below as "partial"


@dataclass
class SkillEvidence:
    skill: str
    category: str  # required | nice | soft
    score: float  # 0..1
    sources: list[dict] = field(default_factory=list)  # [{"type": ..., "label": ...}]


@dataclass
class MatchScore:
    final_score: float
    required_score: float | None
    nice_score: float | None
    soft_score: float | None
    skills: list[SkillEvidence]
    matched_skills: list[str]
    partial_skills: list[str]
    missing_skills: list[str]
    reasoning: str
    legacy_profile: bool = False

    def breakdown(self) -> list[dict]:
        return [asdict(s) for s in self.skills]


@dataclass
class _Source:
    label: str
    skills: set[str]  # normalised + implied skills declared for this item
    text: str  # free text searched as a fallback


@dataclass
class _CandidateIndex:
    listed: set[str]
    experience: list[_Source]
    projects: list[_Source]
    certifications: list[_Source]
    soft: set[str]
    soft_text: str


def _index(profile: dict) -> _CandidateIndex:
    experience = []
    for e in profile.get("experience", []):
        label = " @ ".join(p for p in (e.get("title"), e.get("company")) if p) or "Experience"
        text = " ".join([e.get("title", ""), *e.get("highlights", [])])
        experience.append(_Source(label, expand(set(normalize_list(e.get("technologies")))), text))

    projects = []
    for p in profile.get("projects", []):
        projects.append(
            _Source(
                p.get("name") or "Project",
                expand(set(normalize_list(p.get("technologies")))),
                " ".join([p.get("name", ""), p.get("description", "")]),
            )
        )

    certifications = []
    for c in profile.get("certifications", []):
        name = c.get("name") or "Certification"
        certifications.append(_Source(name, expand(set(normalize_list(c.get("skills")))), name))

    highlights = " ".join(h for e in profile.get("experience", []) for h in e.get("highlights", []))
    return _CandidateIndex(
        listed=expand(set(normalize_list(profile.get("skills")))),
        experience=experience,
        projects=projects,
        certifications=certifications,
        soft=set(normalize_list(profile.get("soft_skills"))),
        soft_text=" ".join([profile.get("summary", ""), highlights]),
    )


def _found_in(skill: str, source: _Source) -> bool:
    return skill_in_set(skill, source.skills) or skill_in_text(skill, source.text)


def _exact_evidence(skill: str, idx: _CandidateIndex) -> tuple[float, list[dict]]:
    sources: list[dict] = []
    best = 0.0

    if skill_in_set(skill, idx.listed):
        best = EVIDENCE_LISTED
        sources.append({"type": "skills", "label": "Listed in skills"})
    for src in idx.projects:
        if _found_in(skill, src):
            best = max(best, EVIDENCE_PROJECT)
            sources.append({"type": "project", "label": src.label})
    for src in idx.experience:
        if _found_in(skill, src):
            best = max(best, EVIDENCE_EXPERIENCE)
            sources.append({"type": "experience", "label": src.label})

    certs = [src for src in idx.certifications if _found_in(skill, src)]
    for src in certs:
        sources.append({"type": "certification", "label": src.label})
    return min(1.0, best + (CERT_BONUS if certs else 0.0)), sources


def _technical_evidence(
    skill: str,
    category: str,
    idx: _CandidateIndex,
    similar: list[tuple[str, float]],
    semantic_factor: float,
) -> SkillEvidence:
    score, sources = _exact_evidence(skill, idx)

    # Semantic fallback: a similar skill (found by ChromaDB) can prove this one,
    # with a discount. Kept only if it beats the exact evidence.
    for other, similarity in similar:
        alt_score, alt_sources = _exact_evidence(other, idx)
        alt_score = round(alt_score * semantic_factor, 2)
        if alt_score > score:
            score = alt_score
            sources = [{**src, "via": other, "similarity": similarity} for src in alt_sources]

    return SkillEvidence(skill, category, round(score, 2), sources)


def _soft_evidence(skill: str, idx: _CandidateIndex) -> SkillEvidence:
    if skill_in_set(skill, idx.soft):
        return SkillEvidence(
            skill, "soft", 1.0, [{"type": "skills", "label": "Listed in soft skills"}]
        )
    if skill_in_text(skill, idx.soft_text):
        return SkillEvidence(
            skill, "soft", 1.0, [{"type": "experience", "label": "Mentioned in CV"}]
        )
    return SkillEvidence(skill, "soft", 0.0, [])


def _mean(values: list[float]) -> float | None:
    return round(100 * sum(values) / len(values), 1) if values else None


def compute_match(
    job_skills: dict,
    profile: dict | None,
    similar: dict[str, list[tuple[str, float]]] | None = None,
    semantic_factor: float = DEFAULT_SEMANTIC_FACTOR,
) -> MatchScore:
    """
    job_skills: {"required": [...], "nice": [...], "soft": [...]} — normalised names.
    profile:    validated JSON profile from extraction_service.load_profile (None = legacy CV).
    similar:    job skill -> [(similar CV skill, cosine similarity)] from ChromaDB.
    """
    similar = similar or {}
    required = normalize_list(job_skills.get("required"))
    nice = [s for s in normalize_list(job_skills.get("nice")) if s not in required]
    soft = normalize_list(job_skills.get("soft"))

    legacy = profile is None
    idx = _index(profile or {})

    skills = [
        _technical_evidence(s, "required", idx, similar.get(s, []), semantic_factor)
        for s in required
    ]
    skills += [
        _technical_evidence(s, "nice", idx, similar.get(s, []), semantic_factor) for s in nice
    ]
    skills += [_soft_evidence(s, idx) for s in soft]

    scores = {
        "required": _mean([s.score for s in skills if s.category == "required"]),
        "nice": _mean([s.score for s in skills if s.category == "nice"]),
        "soft": _mean([s.score for s in skills if s.category == "soft"]),
    }
    active = {k: w for k, w in WEIGHTS.items() if scores[k] is not None}
    total_weight = sum(active.values())
    final = (
        round(sum(scores[k] * w for k, w in active.items()) / total_weight, 1)
        if total_weight
        else 0.0
    )

    technical = [s for s in skills if s.category != "soft"]
    matched = [s.skill for s in technical if s.score >= STRONG_THRESHOLD]
    partial = [s.skill for s in technical if 0 < s.score < STRONG_THRESHOLD]
    missing = [s.skill for s in technical if s.score == 0]

    return MatchScore(
        final_score=final,
        required_score=scores["required"],
        nice_score=scores["nice"],
        soft_score=scores["soft"],
        skills=skills,
        matched_skills=matched,
        partial_skills=partial,
        missing_skills=missing,
        reasoning=_reasoning(skills, legacy),
        legacy_profile=legacy,
    )


def _reasoning(skills: list[SkillEvidence], legacy: bool) -> str:
    if legacy:
        return "This CV was extracted with the old format — re-upload it to score it."
    req = [s for s in skills if s.category == "required"]
    parts = []
    if req:
        covered = sum(1 for s in req if s.score >= STRONG_THRESHOLD)
        parts.append(f"{covered}/{len(req)} required skills proven by experience or projects")
    strong = [s for s in skills if s.category != "soft" and s.score >= STRONG_THRESHOLD]
    if strong:
        examples = []
        for s in strong[:4]:
            best = next((src for src in s.sources if src["type"] == "experience"), None) or next(
                (src for src in s.sources if src["type"] == "project"), None
            )
            if best:
                via = f", via {best['via']}" if best.get("via") else ""
                examples.append(f"{s.skill} ({best['label']}{via})")
            else:
                examples.append(s.skill)
        parts.append("Strong: " + ", ".join(examples))
    listed_only = [
        s.skill for s in skills if s.category != "soft" and 0 < s.score < STRONG_THRESHOLD
    ]
    if listed_only:
        parts.append("Partial (listed or certified only): " + ", ".join(listed_only[:5]))
    missing = [s.skill for s in skills if s.category == "required" and s.score == 0]
    if missing:
        parts.append("Missing: " + ", ".join(missing[:5]))
    return " · ".join(parts) or "No skills to compare."


def profile_skill_names(profile: dict | None) -> set[str]:
    """Every normalised skill name a CV mentions (for the ChromaDB skill vocabulary)."""
    if not profile:
        return set()
    names = list(profile.get("skills", []))
    for item in profile.get("experience", []) + profile.get("projects", []):
        names += item.get("technologies", [])
    for cert in profile.get("certifications", []):
        names += cert.get("skills", [])
    return set(normalize_list(names))
