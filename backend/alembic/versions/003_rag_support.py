"""Add RAG evaluation target and RAGAS metrics columns

Revision ID: 003_rag_support
Revises: 002_dynamic_endpoint
Create Date: 2026-08-06 00:00:00.000000
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB

revision: str = "003_rag_support"
down_revision: Union[str, None] = "002_dynamic_endpoint"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # eval_runs columns
    op.add_column(
        "eval_runs",
        sa.Column("target_type", sa.String(50), nullable=False, server_default="raw_llm"),
    )
    op.create_index("ix_eval_runs_target_type", "eval_runs", ["target_type"])
    op.add_column(
        "eval_runs",
        sa.Column("avg_faithfulness", sa.Float(), nullable=True),
    )
    op.add_column(
        "eval_runs",
        sa.Column("avg_answer_relevance", sa.Float(), nullable=True),
    )
    op.add_column(
        "eval_runs",
        sa.Column("avg_context_precision", sa.Float(), nullable=True),
    )

    # eval_results columns
    op.add_column(
        "eval_results",
        sa.Column("retrieved_contexts", JSONB(), nullable=True),
    )
    op.add_column(
        "eval_results",
        sa.Column("faithfulness", sa.Float(), nullable=True),
    )
    op.add_column(
        "eval_results",
        sa.Column("answer_relevance", sa.Float(), nullable=True),
    )
    op.add_column(
        "eval_results",
        sa.Column("context_precision", sa.Float(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("eval_results", "context_precision")
    op.drop_column("eval_results", "answer_relevance")
    op.drop_column("eval_results", "faithfulness")
    op.drop_column("eval_results", "retrieved_contexts")

    op.drop_index("ix_eval_runs_target_type", table_name="eval_runs")
    op.drop_column("eval_runs", "avg_context_precision")
    op.drop_column("eval_runs", "avg_answer_relevance")
    op.drop_column("eval_runs", "avg_faithfulness")
    op.drop_column("eval_runs", "target_type")
