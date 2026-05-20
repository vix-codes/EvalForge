from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy import Float, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID as PgUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, UUIDMixin

if TYPE_CHECKING:
    from app.db.models.eval_result import EvalResult
    from app.db.models.eval_suite import EvalSuite


class EvalRun(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "eval_runs"

    suite_id: Mapped[UUID] = mapped_column(
        PgUUID(as_uuid=True),
        ForeignKey("eval_suites.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    model_name: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    model_provider: Mapped[str] = mapped_column(String(50), nullable=False, default="ollama")
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default="pending", index=True
    )
    trigger: Mapped[str] = mapped_column(String(50), nullable=False, default="manual")
    commit_sha: Mapped[str | None] = mapped_column(String(40), nullable=True, index=True)
    commit_branch: Mapped[str | None] = mapped_column(String(255), nullable=True)
    commit_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    commit_author: Mapped[str | None] = mapped_column(String(255), nullable=True)
    github_repo: Mapped[str | None] = mapped_column(String(255), nullable=True)
    celery_task_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Aggregate metrics
    total_questions: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    passed_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    failed_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    hallucination_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    pass_rate: Mapped[float | None] = mapped_column(Float, nullable=True)
    hallucination_rate: Mapped[float | None] = mapped_column(Float, nullable=True)
    avg_similarity_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    avg_keyword_coverage: Mapped[float | None] = mapped_column(Float, nullable=True)
    avg_latency_ms: Mapped[float | None] = mapped_column(Float, nullable=True)
    p50_latency_ms: Mapped[float | None] = mapped_column(Float, nullable=True)
    p95_latency_ms: Mapped[float | None] = mapped_column(Float, nullable=True)
    total_runtime_ms: Mapped[float | None] = mapped_column(Float, nullable=True)

    quality_gate_passed: Mapped[bool | None] = mapped_column(nullable=True)
    quality_gate_details: Mapped[dict | None] = mapped_column(JSONB, nullable=True)

    suite: Mapped["EvalSuite"] = relationship("EvalSuite", back_populates="runs")
    results: Mapped[list["EvalResult"]] = relationship(
        "EvalResult",
        back_populates="run",
        cascade="all, delete-orphan",
        lazy="noload",
    )

    def __repr__(self) -> str:
        return f"<EvalRun id={self.id} model={self.model_name!r} status={self.status!r}>"
