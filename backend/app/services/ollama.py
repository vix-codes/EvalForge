"""
Generic LLM adapter for Ollama-compatible endpoints.

Design decisions:
- Uses httpx.Client (synchronous) exclusively so Celery prefork workers never
  touch an asyncio event loop inside the sync execution path.
- All async public methods delegate to asyncio.to_thread so the FastAPI layer
  can await them without blocking.
- base_url can be overridden per-call so a single adapter instance works with
  any local or deployed endpoint, not just the default OLLAMA_BASE_URL.
- On HTTP 500 (OOM / Ollama crash) a retry is performed with halved num_predict
  and num_ctx to reduce host memory pressure.
"""

import asyncio
import time
from dataclasses import dataclass

import httpx

from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)

# Hard cap on prompt input length to prevent OOM on long golden-dataset questions
_DEFAULT_MAX_PROMPT_CHARS = 1200


@dataclass
class InferenceResult:
    response: str
    latency_ms: float
    model: str
    prompt_tokens: int = 0
    completion_tokens: int = 0


class OllamaError(Exception):
    pass


# Backwards-compatible alias
GenericLLMAdapterError = OllamaError


class GenericLLMAdapter:
    """
    Targets any Ollama-compatible /api/generate endpoint.

    Pass `base_url` at construction to set the default; optionally override
    it per generate() call so one adapter instance can hit different endpoints.
    """

    def __init__(self, base_url: str | None = None, timeout: int | None = None) -> None:
        self.base_url = (base_url or settings.OLLAMA_BASE_URL).rstrip("/")
        self.timeout = timeout or settings.OLLAMA_TIMEOUT

    # ------------------------------------------------------------------
    # Public async surface (safe for FastAPI routes)
    # ------------------------------------------------------------------

    async def health_check(self, base_url: str | None = None) -> bool:
        return await asyncio.to_thread(self.health_check_sync, base_url=base_url)

    async def list_models(self, base_url: str | None = None) -> list[str]:
        return await asyncio.to_thread(self.list_models_sync, base_url=base_url)

    async def generate(
        self,
        prompt: str,
        model: str | None = None,
        system_prompt: str | None = None,
        temperature: float = 0.1,
        max_tokens: int | None = None,
        base_url: str | None = None,
    ) -> InferenceResult:
        return await asyncio.to_thread(
            self.generate_sync,
            prompt=prompt,
            model=model,
            system_prompt=system_prompt,
            temperature=temperature,
            max_tokens=max_tokens,
            base_url=base_url,
        )

    async def pull_model(self, model: str, base_url: str | None = None) -> bool:
        return await asyncio.to_thread(self.pull_model_sync, model, base_url=base_url)

    # ------------------------------------------------------------------
    # Synchronous implementations — safe inside Celery workers
    # ------------------------------------------------------------------

    def health_check_sync(self, base_url: str | None = None) -> bool:
        try:
            with self._client(base_url=base_url) as client:
                response = client.get("/api/tags")
                return response.status_code == 200
        except Exception as exc:
            logger.warning("llm.health_check.failed", error=str(exc))
            return False

    def list_models_sync(self, base_url: str | None = None) -> list[str]:
        try:
            with self._client(base_url=base_url) as client:
                response = client.get("/api/tags")
            response.raise_for_status()
            data = response.json()
            return [m["name"] for m in data.get("models", [])]
        except Exception as exc:
            logger.error("llm.list_models.failed", error=str(exc))
            return []

    def generate_sync(
        self,
        prompt: str,
        model: str | None = None,
        system_prompt: str | None = None,
        temperature: float = 0.1,
        max_tokens: int | None = None,
        base_url: str | None = None,
    ) -> InferenceResult:
        model = model or settings.OLLAMA_DEFAULT_MODEL
        max_tokens = max_tokens or settings.OLLAMA_MAX_TOKENS

        # Truncate long prompts to avoid OOM on the Ollama host.
        # Many golden-dataset questions are 500+ words; phi4 at 4096 ctx can still
        # blow up VRAM when combined with a long system prompt and completion.
        max_prompt_chars = getattr(settings, "OLLAMA_MAX_PROMPT_CHARS", _DEFAULT_MAX_PROMPT_CHARS)
        if len(prompt) > max_prompt_chars:
            prompt = prompt[:max_prompt_chars] + "..."
            logger.debug("llm.prompt.truncated", truncated_to=max_prompt_chars)

        # Full-quality payload used on first attempt
        payload: dict = {
            "model": model,
            "prompt": prompt,
            "stream": False,
            "options": {
                "temperature": temperature,
                "num_predict": max_tokens,
                "num_ctx": settings.OLLAMA_NUM_CTX,
                "num_batch": settings.OLLAMA_NUM_BATCH,
            },
            "keep_alive": "2m",
        }
        if system_prompt:
            payload["system"] = system_prompt

        last_exc: Exception | None = None
        for attempt in range(1, settings.OLLAMA_MAX_RETRIES + 1):
            try:
                start = time.perf_counter()
                with self._client(base_url=base_url) as client:
                    response = client.post("/api/generate", json=payload)
                elapsed_ms = (time.perf_counter() - start) * 1000
                response.raise_for_status()
                data = response.json()
                result_text = data.get("response", "").strip()
                logger.info(
                    "llm.generate.success",
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
                    "llm.generate.timeout",
                    model=model,
                    attempt=attempt,
                    max_retries=settings.OLLAMA_MAX_RETRIES,
                )

            except httpx.HTTPStatusError as exc:
                last_exc = exc
                if exc.response.status_code < 500:
                    # 4xx — do not retry
                    raise OllamaError(
                        f"LLM endpoint returned {exc.response.status_code}: {exc.response.text}"
                    ) from exc

                # 5xx — likely OOM on the Ollama host; retry with reduced params
                logger.warning(
                    "llm.generate.server_error",
                    status_code=exc.response.status_code,
                    body=exc.response.text[:500],
                    attempt=attempt,
                    oom_recovery=True,
                )
                # Each retry shrinks the token budget further to relieve memory pressure
                if attempt == 1:
                    payload["options"]["num_predict"] = settings.OLLAMA_RETRY_NUM_PREDICT
                    payload["options"]["num_ctx"] = settings.OLLAMA_RETRY_NUM_CTX
                    payload["keep_alive"] = "1m"
                else:
                    # Last-resort: absolute minimum — just get any response out
                    payload["options"]["num_predict"] = 64
                    payload["options"]["num_ctx"] = 1024
                    payload["keep_alive"] = "30s"

            except Exception as exc:
                last_exc = exc
                logger.warning("llm.generate.error", error=str(exc), attempt=attempt)

        raise OllamaError(
            f"LLM inference failed after {settings.OLLAMA_MAX_RETRIES} attempts: {last_exc}"
        )

    def pull_model_sync(self, model: str, base_url: str | None = None) -> bool:
        try:
            with self._client(timeout=600, base_url=base_url) as client:
                response = client.post(
                    "/api/pull",
                    json={"name": model, "stream": False},
                )
            response.raise_for_status()
            logger.info("llm.pull_model.success", model=model)
            return True
        except Exception as exc:
            logger.error("llm.pull_model.failed", model=model, error=str(exc))
            return False

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def _client(self, timeout: int | None = None, base_url: str | None = None) -> httpx.Client:
        return httpx.Client(
            base_url=(base_url or self.base_url).rstrip("/"),
            timeout=httpx.Timeout(timeout or self.timeout),
            headers={"Content-Type": "application/json"},
        )


# ------------------------------------------------------------------
# Backwards-compatible alias
# ------------------------------------------------------------------
OllamaAdapter = GenericLLMAdapter


_adapter: GenericLLMAdapter | None = None


def get_ollama_adapter(base_url: str | None = None) -> GenericLLMAdapter:
    """
    Returns a GenericLLMAdapter.

    If base_url is provided, always returns a fresh adapter targeting that URL.
    Otherwise returns the cached singleton using OLLAMA_BASE_URL.
    """
    global _adapter
    if base_url:
        return GenericLLMAdapter(base_url=base_url)
    if _adapter is None:
        _adapter = GenericLLMAdapter()
    return _adapter
