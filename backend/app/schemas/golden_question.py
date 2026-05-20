from datetime import datetime
from uuid import UUID

from pydantic import Field, field_validator

from app.schemas.common import BaseSchema


class GoldenQuestionCreate(BaseSchema):
    question: str = Field(min_length=1)
    golden_answer: str = Field(min_length=1)
    category: str | None = None
    difficulty: str = "medium"
    expected_keywords: str | None = None
    max_latency_ms: float | None = Field(None, gt=0)
    weight: float = Field(1.0, gt=0)
    order_index: int = 0

    @field_validator("difficulty")
    @classmethod
    def validate_difficulty(cls, v: str) -> str:
        allowed = {"easy", "medium", "hard"}
        if v not in allowed:
            raise ValueError(f"difficulty must be one of {allowed}")
        return v


class GoldenQuestionUpdate(BaseSchema):
    question: str | None = None
    golden_answer: str | None = None
    category: str | None = None
    difficulty: str | None = None
    expected_keywords: str | None = None
    max_latency_ms: float | None = None
    weight: float | None = None
    order_index: int | None = None


class GoldenQuestionResponse(BaseSchema):
    id: UUID
    suite_id: UUID
    question: str
    golden_answer: str
    category: str | None
    difficulty: str
    expected_keywords: str | None
    max_latency_ms: float | None
    weight: float
    order_index: int
    created_at: datetime
    updated_at: datetime


class GoldenQuestionBulkCreate(BaseSchema):
    questions: list[GoldenQuestionCreate] = Field(min_length=1)
