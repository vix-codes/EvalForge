from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_session
from app.schemas.eval_result import AnalyticsSummary, ModelComparisonItem, TrendDataPoint
from app.services.analytics import (
    get_analytics_summary,
    get_failure_breakdown,
    get_hallucination_trend,
    get_model_comparison,
)

router = APIRouter(prefix="/analytics", tags=["analytics"])


@router.get("/summary", response_model=AnalyticsSummary)
async def summary(session: AsyncSession = Depends(get_session)) -> AnalyticsSummary:
    return await get_analytics_summary(session)


@router.get("/models", response_model=list[ModelComparisonItem])
async def model_comparison(
    suite_id: UUID | None = Query(None),
    session: AsyncSession = Depends(get_session),
) -> list[ModelComparisonItem]:
    return await get_model_comparison(session, suite_id=suite_id)


@router.get("/trends", response_model=list[TrendDataPoint])
async def trends(
    days: int = Query(30, ge=1, le=365),
    model_name: str | None = Query(None),
    session: AsyncSession = Depends(get_session),
) -> list[TrendDataPoint]:
    return await get_hallucination_trend(session, days=days, model_name=model_name)


@router.get("/failures/{run_id}", response_model=dict)
async def failure_breakdown(
    run_id: UUID,
    session: AsyncSession = Depends(get_session),
) -> dict:
    return await get_failure_breakdown(session, run_id=run_id)
