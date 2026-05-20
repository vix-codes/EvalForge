from typing import TYPE_CHECKING

from sqlalchemy import Boolean, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, UUIDMixin

if TYPE_CHECKING:
    from app.db.models.eval_run import EvalRun
    from app.db.models.golden_question import GoldenQuestion


class EvalSuite(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "eval_suites"

    name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    version: Mapped[str] = mapped_column(String(50), nullable=False, default="1.0.0")
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    tags: Mapped[str | None] = mapped_column(Text, nullable=True)

    questions: Mapped[list["GoldenQuestion"]] = relationship(
        "GoldenQuestion",
        back_populates="suite",
        cascade="all, delete-orphan",
        lazy="selectin",
    )
    runs: Mapped[list["EvalRun"]] = relationship(
        "EvalRun",
        back_populates="suite",
        cascade="all, delete-orphan",
        lazy="noload",
    )

    def __repr__(self) -> str:
        return f"<EvalSuite id={self.id} name={self.name!r}>"
