from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy import Boolean, Float, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID as PgUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, UUIDMixin

if TYPE_CHECKING:
    from app.db.models.eval_run import EvalRun
    from app.db.models.golden_question import GoldenQuestion


class EvalResult(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "eval_results"

    run_id: Mapped[UUID] = mapped_column(
        PgUUID(as_uuid=True),
        ForeignKey("eval_runs.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    question_id: Mapped[UUID] = mapped_column(
        PgUUID(as_uuid=True),
        ForeignKey("golden_questions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    model_response: Mapped[str | None] = mapped_column(Text, nullable=True)
    latency_ms: Mapped[float | None] = mapped_column(Float, nullable=True)
    similarity_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    keyword_coverage: Mapped[float | None] = mapped_column(Float, nullable=True)
    gemini_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    gemini_reasoning: Mapped[str | None] = mapped_column(Text, nullable=True)
    final_score: Mapped[float | None] = mapped_column(Float, nullable=True)

    passed: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    is_hallucination: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    failure_reason: Mapped[str | None] = mapped_column(String(255), nullable=True)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    scoring_metadata: Mapped[dict | None] = mapped_column(JSONB, nullable=True)

    run: Mapped["EvalRun"] = relationship("EvalRun", back_populates="results")
    question: Mapped["GoldenQuestion"] = relationship(
        "GoldenQuestion", back_populates="results", lazy="selectin"
    )

    def __repr__(self) -> str:
        return f"<EvalResult id={self.id} passed={self.passed} score={self.final_score}>"
