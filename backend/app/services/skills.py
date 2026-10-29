"""
Skill-name normalisation and matching.

Both the CV and the job description are reduced to lists of skill names by
the LLM. Before comparing them we normalise each name (case, punctuation,
aliases) so that "Postgres", "PostgreSQL" and "postgresql " are the same skill.
"""

import re
import unicodedata

# alias -> canonical name (both sides already normalised: lowercase, single spaces)
ALIASES: dict[str, str] = {
    "postgres": "postgresql",
    "postgre sql": "postgresql",
    "k8s": "kubernetes",
    "js": "javascript",
    "ts": "typescript",
    "nodejs": "node.js",
    "node": "node.js",
    "reactjs": "react",
    "react.js": "react",
    "vuejs": "vue",
    "vue.js": "vue",
    "nextjs": "next.js",
    "golang": "go",
    "py": "python",
    "ml": "machine learning",
    "dl": "deep learning",
    "ai": "artificial intelligence",
    "nlp": "natural language processing",
    "llm": "llms",
    "large language models": "llms",
    "large language model": "llms",
    "gen ai": "generative ai",
    "genai": "generative ai",
    "retrieval augmented generation": "rag",
    "retrieval-augmented generation": "rag",
    "sklearn": "scikit-learn",
    "scikit learn": "scikit-learn",
    "torch": "pytorch",
    "tf": "tensorflow",
    "amazon web services": "aws",
    "google cloud": "gcp",
    "google cloud platform": "gcp",
    "microsoft azure": "azure",
    "apache spark": "spark",
    "pyspark": "spark",
    "apache kafka": "kafka",
    "apache airflow": "airflow",
    "mongo": "mongodb",
    "mongo db": "mongodb",
    "ci/cd": "ci/cd",
    "cicd": "ci/cd",
    "ci cd": "ci/cd",
    "continuous integration": "ci/cd",
    "rest": "rest api",
    "rest apis": "rest api",
    "restful api": "rest api",
    "restful apis": "rest api",
    "restful": "rest api",
    "git hub": "github",
    "github actions": "github actions",
    "c sharp": "c#",
    "csharp": "c#",
    "cpp": "c++",
    "dotnet": ".net",
    "vector database": "vector databases",
    "vector db": "vector databases",
    "ai agents": "agents",
    "llm agents": "agents",
    "agentic ai": "agents",
}

# Knowing the key skill implies the listed skills (with the same evidence).
IMPLIES: dict[str, tuple[str, ...]] = {
    "postgresql": ("sql",),
    "mysql": ("sql",),
    "sqlite": ("sql",),
    "oracle": ("sql",),
    "sql server": ("sql",),
    "fastapi": ("python", "rest api"),
    "django": ("python",),
    "flask": ("python",),
    "pytorch": ("deep learning", "python"),
    "tensorflow": ("deep learning", "python"),
    "keras": ("deep learning",),
    "scikit-learn": ("machine learning", "python"),
    "langchain": ("llms", "python"),
    "langgraph": ("llms", "agents", "python"),
    "chromadb": ("vector databases",),
    "qdrant": ("vector databases",),
    "pinecone": ("vector databases",),
    "weaviate": ("vector databases",),
    "milvus": ("vector databases",),
    "rag": ("llms",),
    "deep learning": ("machine learning",),
    "next.js": ("react",),
    "typescript": ("javascript",),
    "kubernetes": ("docker",),
    "github actions": ("ci/cd",),
    "gitlab ci": ("ci/cd",),
    "github": ("git",),
    "gitlab": ("git",),
}

_PAREN_ACRONYM = re.compile(r"\(([A-Za-z0-9.+#/\- ]{2,10})\)")


def normalize_skill(name: str) -> str:
    """Lowercase, unify punctuation/whitespace and resolve aliases."""
    if not name:
        return ""
    text = unicodedata.normalize("NFKC", str(name))
    # "Retrieval-Augmented Generation (RAG)" -> "RAG"
    acronym = _PAREN_ACRONYM.search(text)
    if acronym and len(acronym.group(1).strip()) <= 6:
        text = acronym.group(1)
    else:
        text = _PAREN_ACRONYM.sub("", text)
    text = text.lower()
    text = re.sub(r"[‐-―−]", "-", text)  # unicode dashes -> "-"
    text = re.sub(r"\s+", " ", text).strip(" .,;:-")
    text = re.sub(r"\s+v?\d+(\.\d+)*$", "", text)  # "python 3.11" -> "python"
    return ALIASES.get(text, text)


def expand(skills: set[str]) -> set[str]:
    """Add the skills implied by the ones we already have (transitively)."""
    out = set(skills)
    todo = list(skills)
    while todo:
        for implied in IMPLIES.get(todo.pop(), ()):
            if implied not in out:
                out.add(implied)
                todo.append(implied)
    return out


def normalize_list(names) -> list[str]:
    """Normalise a list of names, drop empties and duplicates, keep order."""
    seen: dict[str, None] = {}
    for name in names or []:
        if isinstance(name, str):
            norm = normalize_skill(name)
            if norm:
                seen.setdefault(norm, None)
    return list(seen)


def skill_in_set(skill: str, candidates: set[str]) -> bool:
    """
    True if `skill` is in `candidates`, or appears as a whole phrase inside one
    of them ("docker" in "docker compose"). Containment only for names of 3+
    characters, so "c" is never matched by "c++".
    """
    if skill in candidates:
        return True
    if len(skill) < 3:
        return False
    pattern = re.compile(rf"(?<![\w+#.]){re.escape(skill)}s?(?![\w+#])")
    return any(pattern.search(c) for c in candidates)


def skill_in_text(skill: str, text: str) -> bool:
    """Whole-word search of a (normalised) skill in free text."""
    if not text or len(skill) < 3:
        return False
    text = normalize_text(text)
    return re.search(rf"(?<![\w+#.]){re.escape(skill)}s?(?![\w+#])", text) is not None


def normalize_text(text: str) -> str:
    text = unicodedata.normalize("NFKC", text or "").lower()
    return re.sub(r"[‐-―−]", "-", text)
