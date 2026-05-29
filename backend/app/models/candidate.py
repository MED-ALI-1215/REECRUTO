from datetime import datetime, timezone
from sqlalchemy import String, Text, DateTime
from sqlalchemy.orm import Mapped, mapped_column

from app.db.session import Base


class Candidate(Base):
    __tablename__ = "candidates"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    name: Mapped[str] = mapped_column(String(256))
    email: Mapped[str | None] = mapped_column(String(256), nullable=True)
    file_name: Mapped[str | None] = mapped_column(String(512), nullable=True)

    # ── Full structured output from Groq (never truncated) ────────────────────
    structured_info: Mapped[str | None] = mapped_column(Text, nullable=True)
    cv_text: Mapped[str | None] = mapped_column(Text, nullable=True)

    # ── Extracted semantic fields (parsed from structured_info at upload time) ─
    # These power the local scoring formula — no extra Groq call needed.
    skills_text: Mapped[str | None] = mapped_column(Text, nullable=True)         # comma-separated skills
    experience_text: Mapped[str | None] = mapped_column(Text, nullable=True)     # job titles + companies
    certifications_text: Mapped[str | None] = mapped_column(Text, nullable=True) # cert names

    uploaded_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
    )

    def __repr__(self) -> str:
        return f"<Candidate id={self.id!r} name={self.name!r}>"
