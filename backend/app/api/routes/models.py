from fastapi import APIRouter

from app.core.logging import get_logger
from app.services.ollama import get_ollama_adapter

router = APIRouter(prefix="/models", tags=["models"])
logger = get_logger(__name__)


@router.get("")
async def list_available_models() -> dict:
    """
    Lists models available on the default Ollama endpoint.
    For custom endpoints, query the endpoint directly or pass model_name freely
    when creating an eval run — no whitelist is enforced.
    """
    adapter = get_ollama_adapter()
    installed = await adapter.list_models()
    return {
        "installed": installed,
        "default": "phi4",
        "note": "Any model name is accepted when creating an eval run.",
    }


@router.post("/{model_name}/pull")
async def pull_model(model_name: str) -> dict:
    """Pull any model by name from the default Ollama endpoint."""
    adapter = get_ollama_adapter()
    success = await adapter.pull_model(model_name)
    return {"success": success, "model": model_name}
