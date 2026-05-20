from datetime import datetime, timedelta
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.db.models import EvalResult, EvalRun, EvalSuite
from app.schemas.eval_result import AnalyticsSummary, ModelComparisonItem, TrendDataPoint

logger = get_logger(__name__)


async def get_analytics_summary(session: AsyncSession) -> AnalyticsSummary:
    stmt = select(
        func.count(EvalRun.id),
        func.avg(EvalRun.pass_rate),
        func.avg(EvalRun.hallucination_rate),
        func.avg(EvalRun.p95_latency_ms),
    ).where(EvalRun.status == "completed")
    row = (await session.execute(stmt)).one()

    models_stmt = select(EvalRun.model_name).where(EvalRun.status == "completed").distinct()
    models_result = await session.execute(models_stmt)
    models = [r[0] for r in models_result.all()]

    return AnalyticsSummary(
        total_runs=row[0] or 0,
        avg_pass_rate=round(float(row[1]), 4) if row[1] else None,
        avg_hallucination_rate=round(float(row[2]), 4) if row[2] else None,
        avg_p95_latency_ms=round(float(row[3]), 2) if row[3] else None,
        models_tested=models,
    )


async def get_model_comparison(
    session: AsyncSession,
    suite_id: UUID | None = None,
) -> list[ModelComparisonItem]:
    stmt = (
        select(
            EvalRun.model_name,
            func.count(EvalRun.id).label("run_count"),
            func.avg(EvalRun.pass_rate).label("avg_pass_rate"),
            func.avg(EvalRun.hallucination_rate).label("avg_hallucination_rate"),
            func.avg(EvalRun.p95_latency_ms).label("avg_p95_latency_ms"),
            func.avg(EvalRun.avg_latency_ms).label("avg_latency_ms"),
            func.max(EvalRun.id).label("latest_run_id"),
        )
        .where(EvalRun.status == "completed")
        .group_by(EvalRun.model_name)
    )
    if suite_id:
        stmt = stmt.where(EvalRun.suite_id == suite_id)

    rows = (await session.execute(stmt)).all()
    return [
        ModelComparisonItem(
            model_name=r.model_name,
            run_count=r.run_count,
            avg_pass_rate=round(float(r.avg_pass_rate), 4) if r.avg_pass_rate else None,
            avg_hallucination_rate=round(float(r.avg_hallucination_rate), 4) if r.avg_hallucination_rate else None,
            avg_p95_latency_ms=round(float(r.avg_p95_latency_ms), 2) if r.avg_p95_latency_ms else None,
            avg_latency_ms=round(float(r.avg_latency_ms), 2) if r.avg_latency_ms else None,
            latest_run_id=r.latest_run_id,
        )
        for r in rows
    ]


async def get_hallucination_trend(
    session: AsyncSession,
    days: int = 30,
    model_name: str | None = None,
) -> list[TrendDataPoint]:
    since = datetime.utcnow() - timedelta(days=days)
    stmt = (
        select(
            func.date_trunc("day", EvalRun.created_at).label("day"),
            func.avg(EvalRun.pass_rate).label("avg_pass_rate"),
            func.avg(EvalRun.hallucination_rate).label("avg_hallucination_rate"),
            func.avg(EvalRun.p95_latency_ms).label("avg_p95_latency_ms"),
            func.count(EvalRun.id).label("run_count"),
        )
        .where(EvalRun.status == "completed", EvalRun.created_at >= since)
        .group_by(func.date_trunc("day", EvalRun.created_at))
        .order_by(func.date_trunc("day", EvalRun.created_at))
    )
    if model_name:
        stmt = stmt.where(EvalRun.model_name == model_name)

    rows = (await session.execute(stmt)).all()
    return [
        TrendDataPoint(
            date=r.day.strftime("%Y-%m-%d"),
            pass_rate=round(float(r.avg_pass_rate), 4) if r.avg_pass_rate else None,
            hallucination_rate=round(float(r.avg_hallucination_rate), 4) if r.avg_hallucination_rate else None,
            p95_latency_ms=round(float(r.avg_p95_latency_ms), 2) if r.avg_p95_latency_ms else None,
            run_count=r.run_count,
        )
        for r in rows
    ]


async def get_failure_breakdown(
    session: AsyncSession,
    run_id: UUID,
) -> dict:
    stmt = (
        select(
            EvalResult.failure_reason,
            func.count(EvalResult.id).label("count"),
        )
        .where(EvalResult.run_id == run_id, EvalResult.passed == False)
        .group_by(EvalResult.failure_reason)
    )
    rows = (await session.execute(stmt)).all()
    return {r.failure_reason or "unknown": r.count for r in rows}
