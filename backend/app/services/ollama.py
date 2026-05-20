import time
from dataclasses import dataclass

import httpx

from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)

SUPPORTED_MODELS = {"phi4", "llama3.2", "qwen2.5", "gemma3"}


@dataclass
class InferenceResult:
    response: str
    latency_ms: float
    model: str
    prompt_tokens: int = 0
    completion_tokens: int = 0


class OllamaError(Exception):
    pass


class OllamaAdapter:
    def __init__(self, base_url: str | None = None, timeout: int | None = None) -> None:
        self.base_url = (base_url or settings.OLLAMA_BASE_URL).rstrip("/")
        self.timeout = timeout or settings.OLLAMA_TIMEOUT
        self._client: httpx.AsyncClient | None = None

    async def _get_client(self) -> httpx.AsyncClient:
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(
                base_url=self.base_url,
                timeout=httpx.Timeout(self.timeout),
                headers={"Content-Type": "application/json"},
            )
        return self._client

    async def close(self) -> None:
        if self._client and not self._client.is_closed:
            await self._client.aclose()

    async def health_check(self) -> bool:
        try:
            client = await self._get_client()
            response = await client.get("/api/tags")
            return response.status_code == 200
        except Exception as exc:
            logger.warning("ollama.health_check.failed", error=str(exc))
            return False

    async def list_models(self) -> list[str]:
        try:
            client = await self._get_client()
            response = await client.get("/api/tags")
            response.raise_for_status()
            data = response.json()
            return [m["name"] for m in data.get("models", [])]
        except Exception as exc:
            logger.error("ollama.list_models.failed", error=str(exc))
            return []

    async def generate(
        self,
        prompt: str,
        model: str | None = None,
        system_prompt: str | None = None,
        temperature: float = 0.1,
        max_tokens: int = 1024,
    ) -> InferenceResult:
        model = model or settings.OLLAMA_DEFAULT_MODEL
        payload: dict = {
            "model": model,
            "prompt": prompt,
            "stream": False,
            "options": {
                "temperature": temperature,
                "num_predict": max_tokens,
            },
        }
        if system_prompt:
            payload["system"] = system_prompt

        last_exc: Exception | None = None
        for attempt in range(1, settings.OLLAMA_MAX_RETRIES + 1):
            try:
                start = time.perf_counter()
                client = await self._get_client()
                response = await client.post("/api/generate", json=payload)
                elapsed_ms = (time.perf_counter() - start) * 1000
                response.raise_for_status()
                data = response.json()
                result_text = data.get("response", "").strip()
                logger.info(
                    "ollama.generate.success",
                    model=model,
                    latency_ms=round(elapsed_ms, 2),
                    attempt=attempt,
                )
                return InferenceResult(
                    response=result_text,
                    latency_ms=round(elapsed_ms, 2),
                    model=model,
                    prompt_tokens=data.get("prompt_eval_count", 0),
                    completion_tokens=data.get("eval_count", 0),
                )
            except httpx.TimeoutException as exc:
                last_exc = exc
                logger.warning(
                    "ollama.generate.timeout",
                    model=model,
                    attempt=attempt,
                    max_retries=settings.OLLAMA_MAX_RETRIES,
                )
            except httpx.HTTPStatusError as exc:
                last_exc = exc
                if exc.response.status_code < 500:
                    raise OllamaError(f"Ollama returned {exc.response.status_code}: {exc.response.text}") from exc
                logger.warning(
                    "ollama.generate.server_error",
                    status_code=exc.response.status_code,
                    attempt=attempt,
                )
            except Exception as exc:
                last_exc = exc
                logger.warning("ollama.generate.error", error=str(exc), attempt=attempt)

        raise OllamaError(
            f"Ollama inference failed after {settings.OLLAMA_MAX_RETRIES} attempts: {last_exc}"
        )

    async def pull_model(self, model: str) -> bool:
        try:
            client = await self._get_client()
            response = await client.post(
                "/api/pull",
                json={"name": model, "stream": False},
                timeout=httpx.Timeout(600),
            )
            response.raise_for_status()
            logger.info("ollama.pull_model.success", model=model)
            return True
        except Exception as exc:
            logger.error("ollama.pull_model.failed", model=model, error=str(exc))
            return False


_ollama_adapter: OllamaAdapter | None = None


def get_ollama_adapter() -> OllamaAdapter:
    global _ollama_adapter
    if _ollama_adapter is None:
        _ollama_adapter = OllamaAdapter()
    return _ollama_adapter
