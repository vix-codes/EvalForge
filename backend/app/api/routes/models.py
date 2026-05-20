from fastapi import APIRouter

from app.core.logging import get_logger
from app.services.ollama import SUPPORTED_MODELS, get_ollama_adapter

router = APIRouter(prefix="/models", tags=["models"])
logger = get_logger(__name__)


@router.get("")
async def list_available_models() -> dict:
    adapter = get_ollama_adapter()
    installed = await adapter.list_models()
    return {
        "supported": list(SUPPORTED_MODELS),
        "installed": installed,
        "default": "phi4",
    }


@router.post("/{model_name}/pull")
async def pull_model(model_name: str) -> dict:
    if model_name not in SUPPORTED_MODELS:
        return {"success": False, "message": f"Model '{model_name}' is not in supported list"}
    adapter = get_ollama_adapter()
    success = await adapter.pull_model(model_name)
    return {"success": success, "model": model_name}
