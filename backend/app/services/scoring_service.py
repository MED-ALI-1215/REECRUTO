"""
Local scoring engine — zero API calls.

Combines three signals into a final match score:
  - ChromaDB vector similarity score  (weight: 0.40)
  - Skills keyword overlap             (weight: 0.40)
  - Certification bonus                (weight: 0.20)
"""

import re
from dataclasses import dataclass

W_VECTOR = 0.40
W_SKILLS = 0.40
W_CERTS = 0.20

# ── Curated skill vocabulary ──────────────────────────────────────────────────
_SKILL_VOCAB = {
    # Languages
    "python",
    "javascript",
    "typescript",
    "java",
    "kotlin",
    "swift",
    "go",
    "golang",
    "rust",
    "c",
    "c++",
    "c#",
    "php",
    "ruby",
    "scala",
    "r",
    "matlab",
    "bash",
    "shell",
    "sql",
    "html",
    "css",
    "sass",
    "scss",
    # Frameworks / libraries
    "fastapi",
    "django",
    "flask",
    "express",
    "react",
    "vue",
    "angular",
    "nextjs",
    "nuxt",
    "svelte",
    "spring",
    "rails",
    "laravel",
    "nestjs",
    "graphql",
    "rest",
    "grpc",
    "celery",
    "pandas",
    "numpy",
    "scikit-learn",
    "sklearn",
    "tensorflow",
    "pytorch",
    "keras",
    "huggingface",
    "langchain",
    "langraph",
    "langgraph",
    "llama",
    "openai",
    "streamlit",
    "n8n",
    "spark",
    "kafka",
    "airflow",
    "dbt",
    # Databases
    "postgresql",
    "postgres",
    "mysql",
    "sqlite",
    "mongodb",
    "redis",
    "elasticsearch",
    "cassandra",
    "dynamodb",
    "neo4j",
    "pinecone",
    "chromadb",
    "qdrant",
    "weaviate",
    "bigquery",
    "snowflake",
    "supabase",
    "airtable",
    "etl",
    # DevOps / cloud
    "docker",
    "kubernetes",
    "k8s",
    "terraform",
    "ansible",
    "jenkins",
    "github",
    "gitlab",
    "git",
    "linux",
    "nginx",
    "apache",
    "prometheus",
    "grafana",
    "datadog",
    "aws",
    "azure",
    "gcp",
    "ci/cd",
    # AI / ML concepts
    "machine learning",
    "deep learning",
    "nlp",
    "llm",
    "rag",
    "embeddings",
    "vector search",
    "computer vision",
    "data science",
    "mlops",
    "fine-tuning",
    "transformers",
    "bert",
    "gpt",
    "reinforcement learning",
    "multi-agent",
    "agents",
    "data engineering",
    # Concepts
    "api",
    "microservices",
    "websocket",
    "oauth",
    "jwt",
    "devops",
    "agile",
    "scrum",
    "tdd",
    "testing",
    # Soft / domain
    "communication",
    "teamwork",
    "leadership",
    "analytical",
}

_MULTI_WORD_SKILLS = {s for s in _SKILL_VOCAB if " " in s}
_SINGLE_WORD_SKILLS = {s for s in _SKILL_VOCAB if " " not in s}

_CERT_TRIGGER_WORDS = {
    "certified",
    "certification",
    "certificate",
    "license",
    "credential",
    "aws",
    "azure",
    "gcp",
    "pmp",
    "cissp",
    "cpa",
    "cfa",
    "comptia",
    "kubernetes",
    "ckad",
    "cka",
    "scrum",
    "agile",
    "itil",
    "pmi",
    "ibm",
}


@dataclass
class ScoreBreakdown:
    final_score: float
    vector_score: float
    skills_score: float
    cert_score: float
    matched_skills: list[str]
    missing_skills: list[str]
    reasoning: str


def _extract_skills_from_text(text: str) -> set[str]:
    """Match text against curated vocab only — no raw word soup."""
    if not text:
        return set()
    text_lower = text.lower()
    found = set()
    for skill in _MULTI_WORD_SKILLS:
        if skill in text_lower:
            found.add(skill)
    words = set(re.findall(r"[a-zA-Z][a-zA-Z0-9\+\#\.]*", text_lower))
    for skill in _SINGLE_WORD_SKILLS:
        if skill in words:
            found.add(skill)
    return found


def _extract_candidate_skills(skills_text: str) -> set[str]:
    """
    Parse candidate skills — works on comma/slash/newline separated lists
    AND on full structured CV text (scans entire text for vocab terms).
    """
    if not skills_text:
        return set()
    # Always scan the full text for vocab terms — catches skills embedded
    # in project descriptions, experience bullets, etc.
    return _extract_skills_from_text(skills_text)


def _skills_overlap_score(
    jd_skills: set[str], candidate_skills: set[str]
) -> tuple[float, list, list]:
    if not jd_skills:
        return 50.0, [], []
    matched = jd_skills & candidate_skills
    missing = jd_skills - candidate_skills
    score = min(100.0, (len(matched) / len(jd_skills)) * 100)
    return round(score, 1), sorted(matched), sorted(missing)


def _certification_score(job_description: str, certifications_text: str) -> float:
    job_lower = job_description.lower()
    job_mentions_certs = any(w in job_lower for w in _CERT_TRIGGER_WORDS)
    if not job_mentions_certs:
        return 75.0
    if not certifications_text or not certifications_text.strip():
        return 50.0
    cert_tokens = set(re.findall(r"[a-zA-Z][a-zA-Z0-9\+\#\.]*", certifications_text.lower()))
    return 100.0 if cert_tokens & _CERT_TRIGGER_WORDS else 65.0


def compute_score(
    *,
    vector_score: float,
    job_description: str,
    skills_text: str,
    experience_text: str,
    certifications_text: str,
) -> ScoreBreakdown:
    jd_skills = _extract_skills_from_text(job_description)

    # Scan skills_text AND experience_text AND full structured info
    # — this catches skills buried in project descriptions
    combined_candidate_text = " ".join(filter(None, [skills_text, experience_text]))
    candidate_skills = _extract_candidate_skills(combined_candidate_text)

    skills_score, matched, missing = _skills_overlap_score(jd_skills, candidate_skills)
    cert_score = _certification_score(job_description, certifications_text or "")

    final = round(
        (vector_score * W_VECTOR) + (skills_score * W_SKILLS) + (cert_score * W_CERTS),
        1,
    )

    parts = [f"Vector similarity: {vector_score:.0f}/100"]
    if matched:
        parts.append(f"Matched skills: {', '.join(list(matched)[:8])}")
    if missing:
        parts.append(f"Missing skills: {', '.join(list(missing)[:5])}")

    return ScoreBreakdown(
        final_score=final,
        vector_score=vector_score,
        skills_score=skills_score,
        cert_score=cert_score,
        matched_skills=matched,
        missing_skills=missing,
        reasoning=" | ".join(parts),
    )
