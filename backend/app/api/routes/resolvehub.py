from fastapi import APIRouter, Depends, Header, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_session
from app.core.config import settings
from app.core.logging import get_logger
from app.db.models import EvalRun, EvalSuite
from app.schemas.eval_run import EvalRunResponse
from app.services.resolvehub_eval import ResolvehubEvalError, get_resolvehub_adapter

router = APIRouter(prefix="/resolvehub", tags=["resolvehub"])
logger = get_logger(__name__)


class CategorizeRequest(BaseModel):
    text: str
    title: str | None = None


class CategorizeResponse(BaseModel):
    category: str
    priority: str
    confidence: float
    tags: list[str]
    summary: str
    latency_ms: float


class ResolvehubEvalTrigger(BaseModel):
    suite_id: str | None = None
    note: str | None = None


@router.get("/health")
async def resolvehub_health():
    adapter = get_resolvehub_adapter()
    healthy = await adapter.health_check()
    return {
        "resolvehub_reachable": healthy,
        "resolvehub_url": settings.RESOLVEHUB_API_URL,
    }


@router.post("/probe", response_model=CategorizeResponse)
async def probe_categorization(payload: CategorizeRequest):
    adapter = get_resolvehub_adapter()
    if not settings.RESOLVEHUB_API_URL:
        raise HTTPException(status_code=503, detail="RESOLVEHUB_API_URL not configured")

    try:
        result = await adapter.categorize(payload.text)
    except ResolvehubEvalError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    except Exception as exc:
        logger.error("resolvehub.probe.failed", error=str(exc))
        raise HTTPException(status_code=500, detail="Probe failed") from exc

    return CategorizeResponse(
        category=result.category,
        priority=result.priority,
        confidence=result.confidence,
        tags=result.tags,
        summary=result.summary,
        latency_ms=result.latency_ms,
    )


@router.post("/eval", response_model=EvalRunResponse, status_code=status.HTTP_201_CREATED)
async def trigger_resolvehub_eval(
    payload: ResolvehubEvalTrigger,
    session: AsyncSession = Depends(get_session),
) -> EvalRunResponse:
    from sqlalchemy import select

    if payload.suite_id:
        from uuid import UUID
        suite = await session.get(EvalSuite, UUID(payload.suite_id))
    else:
        stmt = (
            select(EvalSuite)
            .where(EvalSuite.is_active == True)
            .where(EvalSuite.tags.ilike("%resolvehub%"))
            .limit(1)
        )
        result = await session.execute(stmt)
        suite = result.scalar_one_or_none()

        if not suite:
            stmt = select(EvalSuite).where(EvalSuite.is_active == True).limit(1)
            result = await session.execute(stmt)
            suite = result.scalar_one_or_none()

    if not suite:
        raise HTTPException(status_code=404, detail="No active eval suite found for ResolveHub")

    run = EvalRun(
        suite_id=suite.id,
        model_name="resolvehub-gemini",
        model_provider="resolvehub",
        trigger="manual",
        commit_message=payload.note,
    )
    session.add(run)
    await session.flush()

    from app.workers.tasks import run_evaluation_task
    task = run_evaluation_task.delay(str(run.id))
    run.celery_task_id = task.id
    await session.flush()

    logger.info("resolvehub.eval.triggered", run_id=str(run.id), suite_id=str(suite.id))
    return EvalRunResponse.model_validate(run)
