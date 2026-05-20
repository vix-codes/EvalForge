from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_session
from app.core.logging import get_logger
from app.db.models import EvalSuite, GoldenQuestion
from app.schemas.common import PaginatedResponse
from app.schemas.golden_question import (
    GoldenQuestionBulkCreate,
    GoldenQuestionCreate,
    GoldenQuestionResponse,
    GoldenQuestionUpdate,
)

router = APIRouter(prefix="/suites/{suite_id}/questions", tags=["datasets"])
logger = get_logger(__name__)


async def _get_suite_or_404(suite_id: UUID, session: AsyncSession) -> EvalSuite:
    suite = await session.get(EvalSuite, suite_id)
    if not suite:
        raise HTTPException(status_code=404, detail="Suite not found")
    return suite


@router.get("", response_model=PaginatedResponse[GoldenQuestionResponse])
async def list_questions(
    suite_id: UUID,
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    category: str | None = Query(None),
    session: AsyncSession = Depends(get_session),
) -> PaginatedResponse[GoldenQuestionResponse]:
    await _get_suite_or_404(suite_id, session)
    stmt = select(GoldenQuestion).where(GoldenQuestion.suite_id == suite_id)
    if category:
        stmt = stmt.where(GoldenQuestion.category == category)
    stmt = stmt.order_by(GoldenQuestion.order_index, GoldenQuestion.created_at)

    count_stmt = select(func.count()).select_from(stmt.subquery())
    total = (await session.execute(count_stmt)).scalar_one()

    stmt = stmt.offset((page - 1) * page_size).limit(page_size)
    questions = (await session.execute(stmt)).scalars().all()

    return PaginatedResponse(
        items=[GoldenQuestionResponse.model_validate(q) for q in questions],
        total=total,
        page=page,
        page_size=page_size,
        pages=(total + page_size - 1) // page_size,
    )


@router.post("", response_model=GoldenQuestionResponse, status_code=status.HTTP_201_CREATED)
async def create_question(
    suite_id: UUID,
    payload: GoldenQuestionCreate,
    session: AsyncSession = Depends(get_session),
) -> GoldenQuestionResponse:
    await _get_suite_or_404(suite_id, session)
    q = GoldenQuestion(suite_id=suite_id, **payload.model_dump())
    session.add(q)
    await session.flush()
    return GoldenQuestionResponse.model_validate(q)


@router.post("/bulk", response_model=list[GoldenQuestionResponse], status_code=status.HTTP_201_CREATED)
async def bulk_create_questions(
    suite_id: UUID,
    payload: GoldenQuestionBulkCreate,
    session: AsyncSession = Depends(get_session),
) -> list[GoldenQuestionResponse]:
    await _get_suite_or_404(suite_id, session)
    questions = [
        GoldenQuestion(suite_id=suite_id, **q.model_dump())
        for q in payload.questions
    ]
    session.add_all(questions)
    await session.flush()
    logger.info("dataset.bulk_create", suite_id=str(suite_id), count=len(questions))
    return [GoldenQuestionResponse.model_validate(q) for q in questions]


@router.get("/{question_id}", response_model=GoldenQuestionResponse)
async def get_question(
    suite_id: UUID,
    question_id: UUID,
    session: AsyncSession = Depends(get_session),
) -> GoldenQuestionResponse:
    q = await session.get(GoldenQuestion, question_id)
    if not q or q.suite_id != suite_id:
        raise HTTPException(status_code=404, detail="Question not found")
    return GoldenQuestionResponse.model_validate(q)


@router.patch("/{question_id}", response_model=GoldenQuestionResponse)
async def update_question(
    suite_id: UUID,
    question_id: UUID,
    payload: GoldenQuestionUpdate,
    session: AsyncSession = Depends(get_session),
) -> GoldenQuestionResponse:
    q = await session.get(GoldenQuestion, question_id)
    if not q or q.suite_id != suite_id:
        raise HTTPException(status_code=404, detail="Question not found")
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(q, field, value)
    await session.flush()
    return GoldenQuestionResponse.model_validate(q)


@router.delete("/{question_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_question(
    suite_id: UUID,
    question_id: UUID,
    session: AsyncSession = Depends(get_session),
) -> None:
    q = await session.get(GoldenQuestion, question_id)
    if not q or q.suite_id != suite_id:
        raise HTTPException(status_code=404, detail="Question not found")
    await session.delete(q)
