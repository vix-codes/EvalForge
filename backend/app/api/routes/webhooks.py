from fastapi import APIRouter, Depends, Header, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_session
from app.core.config import settings
from app.core.logging import get_logger
from app.core.security import verify_github_signature
from app.db.models import EvalRun, EvalSuite
from app.schemas.webhook import GitHubPushPayload, WebhookTriggerResponse

router = APIRouter(prefix="/webhooks", tags=["webhooks"])
logger = get_logger(__name__)


@router.post("/github", response_model=WebhookTriggerResponse)
async def github_webhook(
    request: Request,
    x_hub_signature_256: str | None = Header(None),
    x_github_event: str | None = Header(None),
    session: AsyncSession = Depends(get_session),
) -> WebhookTriggerResponse:
    raw_body = await request.body()

    if settings.GITHUB_WEBHOOK_SECRET:
        if not x_hub_signature_256:
            raise HTTPException(status_code=401, detail="Missing webhook signature")
        if not verify_github_signature(raw_body, x_hub_signature_256, settings.GITHUB_WEBHOOK_SECRET):
            raise HTTPException(status_code=401, detail="Invalid webhook signature")

    if x_github_event != "push":
        logger.info("webhook.github.ignored", event=x_github_event)
        return WebhookTriggerResponse(received=True, message=f"Event '{x_github_event}' ignored")

    try:
        payload = GitHubPushPayload.model_validate_json(raw_body)
    except Exception as exc:
        logger.error("webhook.github.parse_error", error=str(exc))
        raise HTTPException(status_code=400, detail="Invalid payload") from exc

    from sqlalchemy import select
    stmt = select(EvalSuite).where(EvalSuite.is_active == True).limit(1)
    result = await session.execute(stmt)
    suite = result.scalar_one_or_none()

    if not suite:
        logger.warning("webhook.github.no_active_suite")
        return WebhookTriggerResponse(
            received=True,
            message="No active eval suite found — skipping evaluation",
        )

    commit = payload.commits[0] if payload.commits else None
    branch = payload.ref.removeprefix("refs/heads/") if payload.ref else None

    run = EvalRun(
        suite_id=suite.id,
        model_name=settings.OLLAMA_DEFAULT_MODEL,
        model_provider="ollama",
        trigger="github_push",
        commit_sha=payload.after,
        commit_branch=branch,
        commit_message=commit.message if commit else None,
        commit_author=commit.author.get("name") if commit else None,
        github_repo=payload.repository.full_name if payload.repository else None,
    )
    session.add(run)
    await session.flush()

    from app.workers.tasks import run_evaluation_task
    task = run_evaluation_task.delay(str(run.id))
    run.celery_task_id = task.id
    await session.flush()

    logger.info(
        "webhook.github.eval_triggered",
        run_id=str(run.id),
        commit=payload.after,
        branch=branch,
    )

    return WebhookTriggerResponse(
        received=True,
        eval_run_id=str(run.id),
        message=f"Evaluation triggered for commit {payload.after[:8] if payload.after else 'unknown'}",
    )
