"""saved jobs and per-candidate job matches

Revision ID: b7d2c4e9a1f3
Revises: 17dbf7118f92
Create Date: 2026-10-29 11:30:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "b7d2c4e9a1f3"
down_revision: str | Sequence[str] | None = "17dbf7118f92"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "jobs",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("title", sa.String(length=256), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("required_skills_json", sa.Text(), nullable=False),
        sa.Column("nice_skills_json", sa.Text(), nullable=False),
        sa.Column("soft_skills_json", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "job_matches",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("job_id", sa.Integer(), nullable=False),
        sa.Column("candidate_id", sa.String(length=64), nullable=False),
        sa.Column("score", sa.Float(), nullable=False),
        sa.Column("required_score", sa.Float(), nullable=True),
        sa.Column("nice_score", sa.Float(), nullable=True),
        sa.Column("soft_score", sa.Float(), nullable=True),
        sa.Column("breakdown_json", sa.Text(), nullable=False),
        sa.Column("reasoning", sa.Text(), nullable=True),
        sa.Column("legacy_profile", sa.Boolean(), nullable=False),
        sa.Column("retrieved", sa.Boolean(), server_default=sa.true(), nullable=False),
        sa.Column("scoring_version", sa.String(length=32), nullable=False),
        sa.Column("matched_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["job_id"], ["jobs.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["candidate_id"], ["candidates.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("job_id", "candidate_id", name="uq_job_candidate"),
    )
    op.create_index("ix_job_matches_job_id", "job_matches", ["job_id"])
    op.create_index("ix_job_matches_candidate_id", "job_matches", ["candidate_id"])


def downgrade() -> None:
    op.drop_index("ix_job_matches_candidate_id", table_name="job_matches")
    op.drop_index("ix_job_matches_job_id", table_name="job_matches")
    op.drop_table("job_matches")
    op.drop_table("jobs")
