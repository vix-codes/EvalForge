import statistics
import time
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.logging import get_logger
from app.db.models import EvalResult, EvalRun, EvalSuite, GoldenQuestion
from app.services.gemini import GeminiError, GeminiJudge, get_gemini_judge
from app.services.ollama import GenericLLMAdapter, OllamaError, get_ollama_adapter
from app.services.scoring import score_response

logger = get_logger(__name__)

DEFAULT_SYSTEM_PROMPT = """\
You are being evaluated by EvalForge.
Answer the task directly and technically.
Keep the response under 220 words unless code is explicitly required.
If code is required, provide one concise snippet plus short notes.
Explicitly mention deadlock or performance risks when relevant.
Avoid introductions, disclaimers, and broad generic explanations.
"""


async def execute_evaluation_run(
    run_id: UUID,
    session: AsyncSession,
) -> EvalRun:
    run = await session.get(EvalRun, run_id)
    if not run:
        raise ValueError(f"EvalRun {run_id} not found")

    suite = await session.get(EvalSuite, run.suite_id)
    if not suite:
        raise ValueError(f"EvalSuite {run.suite_id} not found")

    stmt = (
        select(GoldenQuestion)
        .where(GoldenQuestion.suite_id == run.suite_id)
        .order_by(GoldenQuestion.order_index)
    )
    result = await session.execute(stmt)
    questions = result.scalars().all()

    if not questions:
        run.status = "failed"
        run.error_message = "No questions found in suite"
        await session.flush()
        return run

    run.status = "running"
    run.total_questions = len(questions)
    await session.flush()

    logger.info(
        "evaluation.run.started",
        run_id=str(run_id),
        model=run.model_name,
        provider=run.model_provider,
        endpoint=run.endpoint_url or settings.OLLAMA_BASE_URL,
        question_count=len(questions),
    )

    pipeline_start = time.perf_counter()
    results: list[EvalResult] = []
    latencies: list[float] = []

    # Resolve which system prompt to use for this run
    system_prompt = run.system_prompt_override or DEFAULT_SYSTEM_PROMPT

    if run.model_provider == "gemini":
        # Use Gemini as the inference model (not just judge)
        judge = get_gemini_judge()
        for question in questions:
            result_obj = await _evaluate_gemini_question(
                run=run,
                question=question,
                judge=judge,
                session=session,
            )
            results.append(result_obj)
            if result_obj.latency_ms is not None:
                latencies.append(result_obj.latency_ms)
    else:
        # Ollama-compatible endpoint: local or any deployed URL
        adapter = get_ollama_adapter(base_url=run.endpoint_url)
        for question in questions:
            result_obj = await _evaluate_question(
                run=run,
                question=question,
                adapter=adapter,
                system_prompt=system_prompt,
                session=session,
            )
            results.append(result_obj)
            if result_obj.latency_ms is not None:
                latencies.append(result_obj.latency_ms)

    total_runtime_ms = (time.perf_counter() - pipeline_start) * 1000

    _aggregate_metrics(run, results, latencies, total_runtime_ms)
    run.status = "completed"

    logger.info(
        "evaluation.run.completed",
        run_id=str(run_id),
        pass_rate=run.pass_rate,
        hallucination_rate=run.hallucination_rate,
        p95_latency_ms=run.p95_latency_ms,
    )

    await session.flush()
    return run


async def _evaluate_question(
    run: EvalRun,
    question: GoldenQuestion,
    adapter: GenericLLMAdapter,
    system_prompt: str,
    session: AsyncSession,
) -> EvalResult:
    result = EvalResult(
        run_id=run.id,
        question_id=question.id,
    )
    session.add(result)

    try:
        inference = await adapter.generate(
            prompt=question.question,
            model=run.model_name,
            system_prompt=system_prompt,
            # base_url is already baked into the adapter instance
        )
        result.model_response = inference.response
        result.latency_ms = inference.latency_ms

        scoring = await score_response(
            question=question.question,
            golden_answer=question.golden_answer,
            model_response=inference.response,
            expected_keywords=question.expected_keywords,
        )
        result.similarity_score = scoring.similarity_score
        result.keyword_coverage = scoring.keyword_coverage
        result.gemini_score = scoring.gemini_score
        result.gemini_reasoning = scoring.gemini_reasoning
        result.final_score = scoring.final_score
        result.passed = scoring.passed
        result.is_hallucination = scoring.is_hallucination
        result.failure_reason = scoring.failure_reason
        result.scoring_metadata = scoring.metadata

    except OllamaError as exc:
        logger.error(
            "evaluation.question.llm_error",
            question_id=str(question.id),
            error=str(exc),
        )
        result.error = str(exc)
        result.passed = False
        result.is_hallucination = False
        result.failure_reason = "inference_error"

    except Exception as exc:
        logger.error(
            "evaluation.question.unexpected_error",
            question_id=str(question.id),
            error=str(exc),
        )
        result.error = str(exc)
        result.passed = False
        result.failure_reason = "unexpected_error"

    await session.flush()
    return result


async def _evaluate_gemini_question(
    run: EvalRun,
    question: GoldenQuestion,
    judge: GeminiJudge,
    session: AsyncSession,
) -> EvalResult:
    """Use Gemini as the inference model (not just as a judge)."""
    result = EvalResult(run_id=run.id, question_id=question.id)
    session.add(result)

    try:
        import time as _time
        import httpx as _httpx
        from app.core.config import settings as _settings

        # Build a minimal Gemini generate request
        GEMINI_URL = "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
        api_key = _settings.GEMINI_API_KEY
        if not api_key:
            raise GeminiError("GEMINI_API_KEY is not configured")

        system_prompt = run.system_prompt_override or DEFAULT_SYSTEM_PROMPT
        prompt_text = f"{system_prompt}\n\n{question.question}"

        url = GEMINI_URL.format(model=_settings.GEMINI_MODEL)
        payload = {
            "contents": [{"parts": [{"text": prompt_text}]}],
            "generationConfig": {"temperature": 0.1, "maxOutputTokens": 512},
        }

        t0 = _time.perf_counter()
        async with _httpx.AsyncClient(timeout=60) as client:
            response = await client.post(url, json=payload, params={"key": api_key})
            latency_ms = (_time.perf_counter() - t0) * 1000
            response.raise_for_status()
            data = response.json()

        response_text = data["candidates"][0]["content"]["parts"][0]["text"].strip()
        result.model_response = response_text
        result.latency_ms = round(latency_ms, 2)

        scoring = await score_response(
            question=question.question,
            golden_answer=question.golden_answer,
            model_response=response_text,
            expected_keywords=question.expected_keywords,
        )
        result.similarity_score = scoring.similarity_score
        result.keyword_coverage = scoring.keyword_coverage
        result.gemini_score = scoring.gemini_score
        result.gemini_reasoning = scoring.gemini_reasoning
        result.final_score = scoring.final_score
        result.passed = scoring.passed
        result.is_hallucination = scoring.is_hallucination
        result.failure_reason = scoring.failure_reason
        result.scoring_metadata = scoring.metadata

    except GeminiError as exc:
        logger.error("evaluation.gemini.error", question_id=str(question.id), error=str(exc))
        result.error = str(exc)
        result.passed = False
        result.is_hallucination = False
        result.failure_reason = "inference_error"

    except Exception as exc:
        logger.error("evaluation.gemini.unexpected_error", question_id=str(question.id), error=str(exc))
        result.error = str(exc)
        result.passed = False
        result.failure_reason = "unexpected_error"

    await session.flush()
    return result


def _aggregate_metrics(
    run: EvalRun,
    results: list[EvalResult],
    latencies: list[float],
    total_runtime_ms: float,
) -> None:
    total = len(results)
    passed = sum(1 for r in results if r.passed)
    hallucinated = sum(1 for r in results if r.is_hallucination)

    run.passed_count = passed
    run.failed_count = total - passed
    run.hallucination_count = hallucinated
    run.pass_rate = round(passed / total, 4) if total else 0.0
    run.hallucination_rate = round(hallucinated / total, 4) if total else 0.0
    run.total_runtime_ms = round(total_runtime_ms, 2)

    sim_scores = [r.similarity_score for r in results if r.similarity_score is not None]
    kw_scores = [r.keyword_coverage for r in results if r.keyword_coverage is not None]

    run.avg_similarity_score = round(statistics.mean(sim_scores), 4) if sim_scores else None
    run.avg_keyword_coverage = round(statistics.mean(kw_scores), 4) if kw_scores else None

    if latencies:
        sorted_lat = sorted(latencies)
        run.avg_latency_ms = round(statistics.mean(latencies), 2)
        p50_idx = int(len(sorted_lat) * 0.50)
        p95_idx = int(len(sorted_lat) * 0.95)
        run.p50_latency_ms = sorted_lat[min(p50_idx, len(sorted_lat) - 1)]
        run.p95_latency_ms = sorted_lat[min(p95_idx, len(sorted_lat) - 1)]

    gate = _evaluate_quality_gate(run)
    run.quality_gate_passed = gate["passed"]
    run.quality_gate_details = gate


def _evaluate_quality_gate(run: EvalRun) -> dict:
    hallucination_ok = (
        run.hallucination_rate is not None
        and run.hallucination_rate <= settings.MAX_HALLUCINATION_RATE
    )
    latency_ok = (
        run.p95_latency_ms is None
        or run.p95_latency_ms <= settings.MAX_P95_LATENCY_MS
    )
    pass_rate_ok = (
        run.pass_rate is not None
        and run.pass_rate >= settings.MIN_PASS_RATE
    )

    return {
        "passed": hallucination_ok and latency_ok and pass_rate_ok,
        "hallucination_rate_ok": hallucination_ok,
        "latency_ok": latency_ok,
        "pass_rate_ok": pass_rate_ok,
        "thresholds": {
            "max_hallucination_rate": settings.MAX_HALLUCINATION_RATE,
            "max_p95_latency_ms": settings.MAX_P95_LATENCY_MS,
            "min_pass_rate": settings.MIN_PASS_RATE,
        },
        "actual": {
            "hallucination_rate": run.hallucination_rate,
            "p95_latency_ms": run.p95_latency_ms,
            "pass_rate": run.pass_rate,
        },
    }
