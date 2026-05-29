from pydantic_settings import BaseSettings, SettingsConfigDict
from functools import lru_cache


class Settings(BaseSettings):
    # ── AI ────────────────────────────────────────────────────────────────────
    GROQ_API_KEY: str
    GROQ_MODEL: str = "llama-3.3-70b-versatile"

    # ── Databases ─────────────────────────────────────────────────────────────
    DATABASE_URL: str = "postgresql+psycopg2://reecruto:reecruto@localhost:5432/reecruto"
    CHROMA_DB_PATH: str = "./chroma_db"
    CHROMA_HOST: str = "localhost"       # used in Docker (server mode)
    CHROMA_PORT: int = 8000
    CHROMA_USE_SERVER: bool = False      # False = local file mode, True = Docker server

    # ── Email ─────────────────────────────────────────────────────────────────
    EMAIL_ADDRESS: str
    EMAIL_PASSWORD: str

    # ── App ───────────────────────────────────────────────────────────────────
    APP_BASE_URL: str = "http://localhost:8503"   # candidate interview base URL
    SECRET_KEY: str = "change-me-before-production"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 8    # 8 hours

    # ── File upload limits ────────────────────────────────────────────────────
    MAX_UPLOAD_SIZE_MB: int = 10
    ALLOWED_EXTENSIONS: list[str] = ["pdf", "docx", "doc", "txt", "png", "jpg", "jpeg"]

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
