from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy import Float, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID as PgUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, UUIDMixin

if TYPE_CHECKING:
    from app.db.models.eval_result import EvalResult
    from app.db.models.eval_suite import EvalSuite


class GoldenQuestion(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "golden_questions"

    suite_id: Mapped[UUID] = mapped_column(
        PgUUID(as_uuid=True),
        ForeignKey("eval_suites.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    question: Mapped[str] = mapped_column(Text, nullable=False)
    golden_answer: Mapped[str] = mapped_column(Text, nullable=False)
    category: Mapped[str | None] = mapped_column(String(100), nullable=True, index=True)
    difficulty: Mapped[str] = mapped_column(String(20), nullable=False, default="medium")
    expected_keywords: Mapped[str | None] = mapped_column(Text, nullable=True)
    max_latency_ms: Mapped[float | None] = mapped_column(Float, nullable=True)
    weight: Mapped[float] = mapped_column(Float, nullable=False, default=1.0)
    order_index: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    suite: Mapped["EvalSuite"] = relationship("EvalSuite", back_populates="questions")
    results: Mapped[list["EvalResult"]] = relationship(
        "EvalResult",
        back_populates="question",
        cascade="all, delete-orphan",
        lazy="noload",
    )

    def __repr__(self) -> str:
        return f"<GoldenQuestion id={self.id} category={self.category!r}>"
