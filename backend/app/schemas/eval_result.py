from datetime import datetime
from uuid import UUID

from app.schemas.common import BaseSchema
from app.schemas.golden_question import GoldenQuestionResponse


class EvalResultResponse(BaseSchema):
    id: UUID
    run_id: UUID
    question_id: UUID
    model_response: str | None
    latency_ms: float | None
    similarity_score: float | None
    keyword_coverage: float | None
    gemini_score: float | None
    gemini_reasoning: str | None
    final_score: float | None
    passed: bool
    is_hallucination: bool
    failure_reason: str | None
    error: str | None
    scoring_metadata: dict | None
    question: GoldenQuestionResponse | None = None
    created_at: datetime
    updated_at: datetime


class EvalResultSummary(BaseSchema):
    id: UUID
    question_id: UUID
    passed: bool
    is_hallucination: bool
    final_score: float | None
    latency_ms: float | None
    failure_reason: str | None


class AnalyticsSummary(BaseSchema):
    total_runs: int
    avg_pass_rate: float | None
    avg_hallucination_rate: float | None
    avg_p95_latency_ms: float | None
    models_tested: list[str]


class ModelComparisonItem(BaseSchema):
    model_name: str
    run_count: int
    avg_pass_rate: float | None
    avg_hallucination_rate: float | None
    avg_p95_latency_ms: float | None
    avg_latency_ms: float | None
    latest_run_id: UUID | None


class TrendDataPoint(BaseSchema):
    date: str
    pass_rate: float | None
    hallucination_rate: float | None
    p95_latency_ms: float | None
    run_count: int
