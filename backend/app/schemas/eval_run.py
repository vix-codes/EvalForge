from datetime import datetime
from uuid import UUID

from pydantic import Field

from app.schemas.common import BaseSchema


class EvalRunCreate(BaseSchema):
    suite_id: UUID
    model_name: str = Field(min_length=1, max_length=100)
    model_provider: str = "ollama"
    target_type: str = "raw_llm"
    trigger: str = "manual"
    # Dynamic endpoint — leave empty to use server default (OLLAMA_BASE_URL)
    endpoint_url: str | None = None
    # Override the evaluation system prompt to describe the LLM's purpose
    system_prompt_override: str | None = None


class EvalRunResponse(BaseSchema):
    id: UUID
    suite_id: UUID
    model_name: str
    model_provider: str
    target_type: str = "raw_llm"
    status: str
    trigger: str
    commit_sha: str | None
    commit_branch: str | None
    commit_message: str | None
    commit_author: str | None
    github_repo: str | None
    celery_task_id: str | None
    error_message: str | None
    endpoint_url: str | None
    system_prompt_override: str | None
    total_questions: int
    passed_count: int
    failed_count: int
    hallucination_count: int
    pass_rate: float | None
    hallucination_rate: float | None
    avg_similarity_score: float | None
    avg_keyword_coverage: float | None
    avg_faithfulness: float | None = None
    avg_answer_relevance: float | None = None
    avg_context_precision: float | None = None
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
    target_type: str = "raw_llm"
    status: str
    trigger: str
    pass_rate: float | None
    hallucination_rate: float | None
    avg_faithfulness: float | None = None
    avg_answer_relevance: float | None = None
    avg_context_precision: float | None = None
    p95_latency_ms: float | None
    quality_gate_passed: bool | None
    created_at: datetime


class QualityGateResult(BaseSchema):
    passed: bool
    hallucination_rate_ok: bool
    latency_ok: bool
    pass_rate_ok: bool
    details: dict
