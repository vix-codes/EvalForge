from datetime import datetime
from uuid import UUID

from pydantic import Field

from app.schemas.common import BaseSchema


class EvalRunCreate(BaseSchema):
    suite_id: UUID
    model_name: str = Field(min_length=1, max_length=100)
    model_provider: str = "ollama"
    trigger: str = "manual"


class EvalRunResponse(BaseSchema):
    id: UUID
    suite_id: UUID
    model_name: str
    model_provider: str
    status: str
    trigger: str
    commit_sha: str | None
    commit_branch: str | None
    commit_message: str | None
    commit_author: str | None
    github_repo: str | None
    celery_task_id: str | None
    error_message: str | None
    total_questions: int
    passed_count: int
    failed_count: int
    hallucination_count: int
    pass_rate: float | None
    hallucination_rate: float | None
    avg_similarity_score: float | None
    avg_keyword_coverage: float | None
    avg_latency_ms: float | None
    p50_latency_ms: float | None
    p95_latency_ms: float | None
    total_runtime_ms: float | None
    quality_gate_passed: bool | None
    quality_gate_details: dict | None
    created_at: datetime
    updated_at: datetime


class EvalRunSummary(BaseSchema):
    id: UUID
    suite_id: UUID
    model_name: str
    status: str
    trigger: str
    pass_rate: float | None
    hallucination_rate: float | None
    p95_latency_ms: float | None
    quality_gate_passed: bool | None
    created_at: datetime


class QualityGateResult(BaseSchema):
    passed: bool
    hallucination_rate_ok: bool
    latency_ok: bool
    pass_rate_ok: bool
    details: dict
