import redis.asyncio as aioredis
from fastapi import APIRouter
from sqlalchemy import text

from app.core.config import settings
from app.core.logging import get_logger
from app.db.session import engine
from app.schemas.common import HealthStatus

router = APIRouter()
logger = get_logger(__name__)


@router.get("/health", response_model=HealthStatus, tags=["system"])
async def health_check() -> HealthStatus:
    services: dict[str, str] = {}

    try:
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        services["database"] = "ok"
    except Exception as exc:
        logger.warning("health.database.failed", error=str(exc))
        services["database"] = "error"

    try:
        client = aioredis.from_url(settings.REDIS_URL, socket_connect_timeout=2)
        await client.ping()
        await client.aclose()
        services["redis"] = "ok"
    except Exception as exc:
        logger.warning("health.redis.failed", error=str(exc))
        services["redis"] = "error"

    try:
        import httpx
        async with httpx.AsyncClient(timeout=3) as client:
            resp = await client.get(f"{settings.OLLAMA_BASE_URL}/api/tags")
            services["ollama"] = "ok" if resp.status_code == 200 else "degraded"
    except Exception:
        services["ollama"] = "unavailable"

    overall = "healthy" if all(v == "ok" for v in services.values()) else "degraded"

    return HealthStatus(
        status=overall,
        version=settings.APP_VERSION,
        services=services,
    )


@router.get("/health/ready", tags=["system"])
async def readiness_check() -> dict:
    return {"ready": True}


@router.get("/health/live", tags=["system"])
async def liveness_check() -> dict:
    return {"alive": True}
