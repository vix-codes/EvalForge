import statistics
import time
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.logging import get_logger
from app.db.models import EvalResult, EvalRun, EvalSuite, GoldenQuestion
from app.services.gemini import GeminiClassifier, GeminiError, get_gemini_classifier
from app.services.ollama import OllamaAdapter, OllamaError, get_ollama_adapter
from app.services.resolvehub_eval import ResolvehubEvalError, get_resolvehub_adapter, score_categorization
from app.services.scoring import score_response

logger = get_logger(__name__)


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
        question_count=len(questions),
    )

    pipeline_start = time.perf_counter()
    results: list[EvalResult] = []
    latencies: list[float] = []

    if run.model_provider == "resolvehub":
        resolvehub_adapter = get_resolvehub_adapter()
        for question in questions:
            result_obj = await _evaluate_resolvehub_question(
                run=run,
                question=question,
                adapter=resolvehub_adapter,
                session=session,
            )
            results.append(result_obj)
            if result_obj.latency_ms is not None:
                latencies.append(result_obj.latency_ms)
    elif run.model_provider == "gemini":
        classifier = get_gemini_classifier()
        for question in questions:
            result_obj = await _evaluate_gemini_question(
                run=run,
                question=question,
                classifier=classifier,
                session=session,
            )
            results.append(result_obj)
            if result_obj.latency_ms is not None:
                latencies.append(result_obj.latency_ms)
    else:
        adapter = get_ollama_adapter()
        for question in questions:
            result_obj = await _evaluate_question(
                run=run,
                question=question,
                adapter=adapter,
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
    adapter: OllamaAdapter,
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
            "evaluation.question.ollama_error",
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
    classifier: GeminiClassifier,
    session: AsyncSession,
) -> EvalResult:
    result = EvalResult(run_id=run.id, question_id=question.id)
    session.add(result)

    try:
        response_text, latency_ms = await classifier.classify(question.question)
        result.model_response = response_text
        result.latency_ms = latency_ms

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


async def _evaluate_resolvehub_question(
    run: EvalRun,
    question: GoldenQuestion,
    adapter,
    session: AsyncSession,
) -> EvalResult:
    result = EvalResult(
        run_id=run.id,
        question_id=question.id,
    )
    session.add(result)

    try:
        categorization = await adapter.categorize(question.question)

        result.model_response = (
            f"CATEGORY: {categorization.category}\n"
            f"PRIORITY: {categorization.priority}\n"
            f"CONFIDENCE: {categorization.confidence:.3f}\n"
            f"SUMMARY: {categorization.summary}"
        )
        result.latency_ms = categorization.latency_ms

        scoring = score_categorization(
            result=categorization,
            expected_category=question.golden_answer,
            expected_priority=question.category,
        )

        result.similarity_score = scoring["similarity_score"]
        result.keyword_coverage = scoring["keyword_coverage"]
        result.final_score = scoring["final_score"]
        result.passed = scoring["passed"]
        result.is_hallucination = scoring["is_hallucination"]
        result.failure_reason = scoring["failure_reason"]
        result.scoring_metadata = {
            "provider": "resolvehub",
            "category_match": scoring["category_match"],
            "priority_match": scoring["priority_match"],
            "priority_within_one": scoring["priority_within_one"],
            "confidence_ok": scoring["confidence_ok"],
            "actual": scoring["actual"],
        }

    except ResolvehubEvalError as exc:
        logger.error(
            "evaluation.resolvehub.api_error",
            question_id=str(question.id),
            status_code=exc.status_code,
            error=str(exc),
        )
        result.error = str(exc)
        result.passed = False
        result.is_hallucination = False
        result.failure_reason = "resolvehub_api_error"

    except Exception as exc:
        logger.error(
            "evaluation.resolvehub.unexpected_error",
            question_id=str(question.id),
            error=str(exc),
        )
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
