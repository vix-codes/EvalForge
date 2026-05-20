from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_session
from app.core.logging import get_logger
from app.db.models import EvalResult, EvalRun, EvalSuite
from app.schemas.common import PaginatedResponse
from app.schemas.eval_result import EvalResultResponse, EvalResultSummary
from app.schemas.eval_run import EvalRunCreate, EvalRunResponse, EvalRunSummary

router = APIRouter(prefix="/evals", tags=["evaluations"])
logger = get_logger(__name__)


@router.get("", response_model=PaginatedResponse[EvalRunSummary])
async def list_runs(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    suite_id: UUID | None = Query(None),
    model_name: str | None = Query(None),
    status_filter: str | None = Query(None, alias="status"),
    session: AsyncSession = Depends(get_session),
) -> PaginatedResponse[EvalRunSummary]:
    stmt = select(EvalRun).order_by(EvalRun.created_at.desc())
    if suite_id:
        stmt = stmt.where(EvalRun.suite_id == suite_id)
    if model_name:
        stmt = stmt.where(EvalRun.model_name == model_name)
    if status_filter:
        stmt = stmt.where(EvalRun.status == status_filter)

    count_stmt = select(func.count()).select_from(stmt.subquery())
    total = (await session.execute(count_stmt)).scalar_one()

    stmt = stmt.offset((page - 1) * page_size).limit(page_size)
    runs = (await session.execute(stmt)).scalars().all()

    return PaginatedResponse(
        items=[EvalRunSummary.model_validate(r) for r in runs],
        total=total,
        page=page,
        page_size=page_size,
        pages=(total + page_size - 1) // page_size,
    )


@router.post("", response_model=EvalRunResponse, status_code=status.HTTP_201_CREATED)
async def create_run(
    payload: EvalRunCreate,
    session: AsyncSession = Depends(get_session),
) -> EvalRunResponse:
    suite = await session.get(EvalSuite, payload.suite_id)
    if not suite:
        raise HTTPException(status_code=404, detail="Suite not found")

    run = EvalRun(**payload.model_dump())
    session.add(run)
    await session.flush()

    from app.workers.tasks import run_evaluation_task
    task = run_evaluation_task.delay(str(run.id))
    run.celery_task_id = task.id
    await session.flush()
    await session.refresh(run)

    logger.info("eval.run.created", run_id=str(run.id), task_id=task.id)
    return EvalRunResponse.model_validate(run)


@router.get("/{run_id}", response_model=EvalRunResponse)
async def get_run(
    run_id: UUID,
    session: AsyncSession = Depends(get_session),
) -> EvalRunResponse:
    run = await session.get(EvalRun, run_id)
    if not run:
        raise HTTPException(status_code=404, detail="Eval run not found")
    return EvalRunResponse.model_validate(run)


@router.get("/{run_id}/results", response_model=PaginatedResponse[EvalResultSummary])
async def list_run_results(
    run_id: UUID,
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    passed: bool | None = Query(None),
    is_hallucination: bool | None = Query(None),
    session: AsyncSession = Depends(get_session),
) -> PaginatedResponse[EvalResultSummary]:
    run = await session.get(EvalRun, run_id)
    if not run:
        raise HTTPException(status_code=404, detail="Eval run not found")

    stmt = select(EvalResult).where(EvalResult.run_id == run_id)
    if passed is not None:
        stmt = stmt.where(EvalResult.passed == passed)
    if is_hallucination is not None:
        stmt = stmt.where(EvalResult.is_hallucination == is_hallucination)

    count_stmt = select(func.count()).select_from(stmt.subquery())
    total = (await session.execute(count_stmt)).scalar_one()

    stmt = stmt.offset((page - 1) * page_size).limit(page_size)
    results = (await session.execute(stmt)).scalars().all()

    return PaginatedResponse(
        items=[EvalResultSummary.model_validate(r) for r in results],
        total=total,
        page=page,
        page_size=page_size,
        pages=(total + page_size - 1) // page_size,
    )


@router.get("/{run_id}/results/{result_id}", response_model=EvalResultResponse)
async def get_result_detail(
    run_id: UUID,
    result_id: UUID,
    session: AsyncSession = Depends(get_session),
) -> EvalResultResponse:
    result = await session.get(EvalResult, result_id)
    if not result or result.run_id != run_id:
        raise HTTPException(status_code=404, detail="Result not found")
    return EvalResultResponse.model_validate(result)
