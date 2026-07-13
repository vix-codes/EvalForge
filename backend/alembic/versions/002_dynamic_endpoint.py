"""Add dynamic endpoint fields to eval_runs

Adds endpoint_url and system_prompt_override columns so any local or deployed
LLM can be targeted per eval run without hardcoding the Ollama base URL.

Revision ID: 002_dynamic_endpoint
Revises: 001_initial
Create Date: 2026-07-14 00:00:00.000000
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "002_dynamic_endpoint"
down_revision: Union[str, None] = "001_initial"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "eval_runs",
        sa.Column("endpoint_url", sa.String(500), nullable=True),
    )
    op.add_column(
        "eval_runs",
        sa.Column("system_prompt_override", sa.Text(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("eval_runs", "system_prompt_override")
    op.drop_column("eval_runs", "endpoint_url")
