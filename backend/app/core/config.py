from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # ── AI ────────────────────────────────────────────────────────────────────
    GROQ_API_KEY: str
    GROQ_MODEL: str = "openai/gpt-oss-120b"

    # ── Databases ─────────────────────────────────────────────────────────────
    DATABASE_URL: str = "postgresql+psycopg2://reecruto:reecruto@localhost:5432/reecruto"
    CHROMA_DB_PATH: str = "./chroma_db"
    CHROMA_HOST: str = "localhost"  # used in Docker (server mode)
    CHROMA_PORT: int = 8000
    CHROMA_USE_SERVER: bool = False  # False = local file mode, True = Docker server

    # ── Email ─────────────────────────────────────────────────────────────────
    EMAIL_ADDRESS: str
    EMAIL_PASSWORD: str

    # ── App ───────────────────────────────────────────────────────────────────
    APP_BASE_URL: str = "http://localhost:3000/interview"  # candidate interview base URL
    SECRET_KEY: str = "change-me-before-production"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 8  # 8 hours

    # ── Recruiter login (single account until DB users exist) ────────────────
    RECRUITER_USERNAME: str = "admin"
    RECRUITER_PASSWORD: str = "reecruto-admin"

    # ── Matching (ChromaDB) ───────────────────────────────────────────────────
    # Stage 1 "retrieve": when there are at least MATCH_PREFILTER_MIN_CVS CVs,
    # ChromaDB pre-selects the MATCH_RETRIEVE_TOP_K CVs closest to the job and
    # only those are scored in detail (stage 2 "rank", evidence-based).
    MATCH_RETRIEVE_TOP_K: int = 100
    MATCH_PREFILTER_MIN_CVS: int = 500
    # Semantic skill matching: "Torch" ~ "PyTorch". Similar skills count for
    # SEMANTIC_MATCH_FACTOR of an exact match, above SKILL_SIMILARITY_THRESHOLD.
    SEMANTIC_SKILLS_ENABLED: bool = True
    SKILL_SIMILARITY_THRESHOLD: float = 0.80
    SEMANTIC_MATCH_FACTOR: float = 0.8

    # ── File upload limits ────────────────────────────────────────────────────
    MAX_UPLOAD_SIZE_MB: int = 10
    ALLOWED_EXTENSIONS: list[str] = [
        "pdf",
        "docx",
        "txt",
        "png",
        "jpg",
        "jpeg",
    ]  # no .doc: python-docx reads .docx only

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
    )

    @property
    def max_upload_bytes(self) -> int:
        return self.MAX_UPLOAD_SIZE_MB * 1024 * 1024


@lru_cache
def get_settings() -> Settings:
    """
    Return a cached Settings instance.
    FastAPI routes inject this via Depends(get_settings).
    Tests can override it with app.dependency_overrides.
    """
    return Settings()
