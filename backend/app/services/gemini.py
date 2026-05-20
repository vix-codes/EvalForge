import httpx

from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)

GEMINI_API_URL = "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"


class GeminiError(Exception):
    pass


class GeminiJudge:
    def __init__(self, api_key: str | None = None) -> None:
        self.api_key = api_key or settings.GEMINI_API_KEY
        self.model = settings.GEMINI_MODEL

    async def judge(
        self,
        question: str,
        golden_answer: str,
        model_response: str,
    ) -> tuple[float, str]:
        if not self.api_key:
            raise GeminiError("GEMINI_API_KEY is not configured")

        prompt = (
            "You are a strict LLM evaluation judge. Score the model response against the golden answer.\n\n"
            f"Question: {question}\n\n"
            f"Golden Answer: {golden_answer}\n\n"
            f"Model Response: {model_response}\n\n"
            "Provide:\n"
            "1. A score from 0.0 to 1.0 (1.0 = perfect match, 0.0 = completely wrong/hallucinated)\n"
            "2. Brief reasoning (1-2 sentences)\n\n"
            "Respond in this exact format:\n"
            "SCORE: <float>\n"
            "REASONING: <text>"
        )

        url = GEMINI_API_URL.format(model=self.model)
        payload = {
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {"temperature": 0.0, "maxOutputTokens": 256},
        }

        try:
            async with httpx.AsyncClient(timeout=30) as client:
                response = await client.post(
                    url,
                    json=payload,
                    params={"key": self.api_key},
                )
                response.raise_for_status()
                data = response.json()

            text = data["candidates"][0]["content"]["parts"][0]["text"].strip()
            score, reasoning = self._parse_response(text)
            logger.info("gemini.judge.success", score=score)
            return score, reasoning

        except GeminiError:
            raise
        except httpx.HTTPStatusError as exc:
            logger.error("gemini.judge.http_error", status=exc.response.status_code, body=exc.response.text[:200])
            raise GeminiError(f"Gemini API error {exc.response.status_code}") from exc
        except Exception as exc:
            logger.error("gemini.judge.failed", error=str(exc))
            raise GeminiError(str(exc)) from exc

    def _parse_response(self, text: str) -> tuple[float, str]:
        score = 0.5
        reasoning = text
        for line in text.splitlines():
            line = line.strip()
            if line.startswith("SCORE:"):
                try:
                    score = float(line.split(":", 1)[1].strip())
                    score = max(0.0, min(1.0, score))
                except ValueError:
                    pass
            elif line.startswith("REASONING:"):
                reasoning = line.split(":", 1)[1].strip()
        return score, reasoning


_gemini_judge: GeminiJudge | None = None


def get_gemini_judge() -> GeminiJudge:
    global _gemini_judge
    if _gemini_judge is None:
        _gemini_judge = GeminiJudge()
    return _gemini_judge
