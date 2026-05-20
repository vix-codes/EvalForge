import asyncio
from uuid import UUID

import structlog

from app.workers.celery_app import celery_app

logger = structlog.get_logger(__name__)


def _run_async(coro):
    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


@celery_app.task(
    name="evalforge.run_evaluation",
    bind=True,
    max_retries=2,
    default_retry_delay=30,
)
def run_evaluation_task(self, run_id: str) -> dict:
    from app.db.session import get_db_context
    from app.services.evaluation import execute_evaluation_run

    async def _execute():
        async with get_db_context() as session:
            run = await execute_evaluation_run(UUID(run_id), session)
            return {
                "run_id": str(run.id),
                "status": run.status,
                "pass_rate": run.pass_rate,
                "hallucination_rate": run.hallucination_rate,
                "quality_gate_passed": run.quality_gate_passed,
            }

    try:
        logger.info("task.run_evaluation.started", run_id=run_id)
        result = _run_async(_execute())
        logger.info("task.run_evaluation.completed", run_id=run_id, result=result)
        return result
    except Exception as exc:
        logger.error("task.run_evaluation.failed", run_id=run_id, error=str(exc))
        try:
            self.retry(exc=exc)
        except self.MaxRetriesExceededError:
            _run_async(_mark_run_failed(run_id, str(exc)))
        raise


async def _mark_run_failed(run_id: str, error: str) -> None:
    from app.db.session import get_db_context
    from app.db.models import EvalRun
    from uuid import UUID

    async with get_db_context() as session:
        run = await session.get(EvalRun, UUID(run_id))
        if run:
            run.status = "failed"
            run.error_message = error[:1000]


@celery_app.task(name="evalforge.health_check")
def health_check_task() -> dict:
    return {"status": "ok", "worker": "alive"}
