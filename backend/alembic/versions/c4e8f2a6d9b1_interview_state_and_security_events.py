"""server-side interview state, job interview questions and security events

Revision ID: c4e8f2a6d9b1
Revises: b7d2c4e9a1f3
Create Date: 2026-10-29 12:30:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "c4e8f2a6d9b1"
down_revision: str | Sequence[str] | None = "b7d2c4e9a1f3"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    with op.batch_alter_table("interview_sessions") as batch:
        batch.add_column(sa.Column("job_id", sa.Integer(), nullable=True))
        batch.add_column(sa.Column("candidate_id", sa.String(length=64), nullable=True))
        batch.add_column(sa.Column("questions_json", sa.Text(), nullable=True))
        batch.add_column(sa.Column("progress_json", sa.Text(), nullable=True))
        batch.create_foreign_key(
            "fk_interview_sessions_job_id", "jobs", ["job_id"], ["id"], ondelete="SET NULL"
        )
        batch.create_foreign_key(
            "fk_interview_sessions_candidate_id",
            "candidates",
            ["candidate_id"],
            ["id"],
            ondelete="SET NULL",
        )
    with op.batch_alter_table("jobs") as batch:
        batch.add_column(sa.Column("interview_questions_json", sa.Text(), nullable=True))

    op.create_table(
        "security_events",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("source", sa.String(length=32), nullable=False),
        sa.Column("detector", sa.String(length=16), nullable=False),
        sa.Column("reasons", sa.Text(), nullable=False),
        sa.Column("excerpt", sa.Text(), nullable=False),
        sa.Column("candidate_id", sa.String(length=64), nullable=True),
        sa.Column("candidate_name", sa.String(length=256), nullable=True),
        sa.Column("session_token", sa.String(length=64), nullable=True),
        sa.Column("question_index", sa.Integer(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_security_events_candidate_id", "security_events", ["candidate_id"])
    op.create_index("ix_security_events_session_token", "security_events", ["session_token"])


def downgrade() -> None:
    op.drop_index("ix_security_events_session_token", table_name="security_events")
    op.drop_index("ix_security_events_candidate_id", table_name="security_events")
    op.drop_table("security_events")
    with op.batch_alter_table("jobs") as batch:
        batch.drop_column("interview_questions_json")
    with op.batch_alter_table("interview_sessions") as batch:
        batch.drop_constraint("fk_interview_sessions_candidate_id", type_="foreignkey")
        batch.drop_constraint("fk_interview_sessions_job_id", type_="foreignkey")
        batch.drop_column("progress_json")
        batch.drop_column("questions_json")
        batch.drop_column("candidate_id")
        batch.drop_column("job_id")
