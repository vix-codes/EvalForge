from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_session
from app.core.logging import get_logger
from app.db.models import EvalSuite, GoldenQuestion
from app.schemas.common import PaginatedResponse
from app.schemas.eval_suite import EvalSuiteCreate, EvalSuiteResponse, EvalSuiteSummary, EvalSuiteUpdate

router = APIRouter(prefix="/suites", tags=["suites"])
logger = get_logger(__name__)


@router.get("", response_model=PaginatedResponse[EvalSuiteSummary])
async def list_suites(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    active_only: bool = Query(False),
    session: AsyncSession = Depends(get_session),
) -> PaginatedResponse[EvalSuiteSummary]:
    stmt = select(EvalSuite)
    if active_only:
        stmt = stmt.where(EvalSuite.is_active == True)
    stmt = stmt.order_by(EvalSuite.created_at.desc())

    count_stmt = select(func.count()).select_from(stmt.subquery())
    total = (await session.execute(count_stmt)).scalar_one()

    stmt = stmt.offset((page - 1) * page_size).limit(page_size)
    suites = (await session.execute(stmt)).scalars().all()

    items = []
    for suite in suites:
        q_count_stmt = select(func.count(GoldenQuestion.id)).where(
            GoldenQuestion.suite_id == suite.id
        )
        q_count = (await session.execute(q_count_stmt)).scalar_one()
        items.append(
            EvalSuiteSummary(
                id=suite.id,
                name=suite.name,
                version=suite.version,
                is_active=suite.is_active,
                question_count=q_count,
                created_at=suite.created_at,
            )
        )

    return PaginatedResponse(
        items=items,
        total=total,
        page=page,
        page_size=page_size,
        pages=(total + page_size - 1) // page_size,
    )


@router.post("", response_model=EvalSuiteResponse, status_code=status.HTTP_201_CREATED)
async def create_suite(
    payload: EvalSuiteCreate,
    session: AsyncSession = Depends(get_session),
) -> EvalSuiteResponse:
    suite = EvalSuite(**payload.model_dump())
    session.add(suite)
    await session.flush()
    logger.info("suite.created", suite_id=str(suite.id), name=suite.name)
    return EvalSuiteResponse(**{**suite.__dict__, "question_count": 0})


@router.get("/{suite_id}", response_model=EvalSuiteResponse)
async def get_suite(
    suite_id: UUID,
    session: AsyncSession = Depends(get_session),
) -> EvalSuiteResponse:
    suite = await session.get(EvalSuite, suite_id)
    if not suite:
        raise HTTPException(status_code=404, detail="Suite not found")
    q_count = (
        await session.execute(
            select(func.count(GoldenQuestion.id)).where(GoldenQuestion.suite_id == suite_id)
        )
    ).scalar_one()
    return EvalSuiteResponse(**{**suite.__dict__, "question_count": q_count})


@router.patch("/{suite_id}", response_model=EvalSuiteResponse)
async def update_suite(
    suite_id: UUID,
    payload: EvalSuiteUpdate,
    session: AsyncSession = Depends(get_session),
) -> EvalSuiteResponse:
    suite = await session.get(EvalSuite, suite_id)
    if not suite:
        raise HTTPException(status_code=404, detail="Suite not found")
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(suite, field, value)
    await session.flush()
    q_count = (
        await session.execute(
            select(func.count(GoldenQuestion.id)).where(GoldenQuestion.suite_id == suite_id)
        )
    ).scalar_one()
    return EvalSuiteResponse(**{**suite.__dict__, "question_count": q_count})


@router.delete("/{suite_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_suite(
    suite_id: UUID,
    session: AsyncSession = Depends(get_session),
) -> None:
    suite = await session.get(EvalSuite, suite_id)
    if not suite:
        raise HTTPException(status_code=404, detail="Suite not found")
    await session.delete(suite)
    logger.info("suite.deleted", suite_id=str(suite_id))
