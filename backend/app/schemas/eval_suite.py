from datetime import datetime
from uuid import UUID

from pydantic import Field

from app.schemas.common import BaseSchema


class EvalSuiteCreate(BaseSchema):
    name: str = Field(min_length=1, max_length=255)
    description: str | None = None
    version: str = "1.0.0"
    tags: str | None = None


class EvalSuiteUpdate(BaseSchema):
    name: str | None = Field(None, min_length=1, max_length=255)
    description: str | None = None
    version: str | None = None
    is_active: bool | None = None
    tags: str | None = None


class EvalSuiteResponse(BaseSchema):
    id: UUID
    name: str
    description: str | None
    version: str
    is_active: bool
    tags: str | None
    created_at: datetime
    updated_at: datetime
    question_count: int = 0


class EvalSuiteSummary(BaseSchema):
    id: UUID
    name: str
    version: str
    is_active: bool
    question_count: int = 0
    created_at: datetime
