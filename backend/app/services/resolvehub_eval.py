import time
from dataclasses import dataclass

import httpx

from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)

VALID_CATEGORIES = {
    "PLUMBING", "ELECTRICAL", "SECURITY", "CLEANING",
    "INTERNET", "HVAC", "STRUCTURAL", "GENERAL",
}
VALID_PRIORITIES = {"LOW", "MEDIUM", "HIGH", "CRITICAL"}

PRIORITY_LEVELS = {"LOW": 0, "MEDIUM": 1, "HIGH": 2, "CRITICAL": 3}


@dataclass
class CategorizationResult:
    category: str
    priority: str
    confidence: float
    tags: list[str]
    summary: str
    latency_ms: float
    raw: dict


class ResolvehubEvalAdapter:
    def __init__(self, base_url: str, eval_secret: str = "", timeout: float = 15.0):
        self.base_url = base_url.rstrip("/")
        self.eval_secret = eval_secret
        self.timeout = timeout

    async def categorize(self, complaint_text: str) -> CategorizationResult:
        url = f"{self.base_url}/api/eval/categorize"
        headers = {"Content-Type": "application/json"}
        if self.eval_secret:
            headers["X-Eval-Secret"] = self.eval_secret

        payload = {"text": complaint_text}
        start = time.perf_counter()

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.post(url, json=payload, headers=headers)
            latency_ms = (time.perf_counter() - start) * 1000

            if response.status_code != 200:
                raise ResolvehubEvalError(
                    f"ResolveHub eval endpoint returned {response.status_code}: {response.text[:200]}",
                    status_code=response.status_code,
                )

            data = response.json()

        category = str(data.get("category", "GENERAL")).upper()
        priority = str(data.get("priority", "MEDIUM")).upper()
        confidence = float(data.get("confidence", 0.0))

        return CategorizationResult(
            category=category if category in VALID_CATEGORIES else "GENERAL",
            priority=priority if priority in VALID_PRIORITIES else "MEDIUM",
            confidence=max(0.0, min(1.0, confidence)),
            tags=data.get("tags", []),
            summary=data.get("summary", ""),
            latency_ms=round(latency_ms, 2),
            raw=data,
        )

    async def health_check(self) -> bool:
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.get(f"{self.base_url}/health")
                return response.status_code == 200
        except Exception:
            return False


class ResolvehubEvalError(Exception):
    def __init__(self, message: str, status_code: int = 0):
        super().__init__(message)
        self.status_code = status_code


def score_categorization(
    result: CategorizationResult,
    expected_category: str,
    expected_priority: str | None = None,
    min_confidence: float = 0.65,
) -> dict:
    expected_cat = expected_category.upper()
    category_match = result.category == expected_cat

    priority_match = True
    priority_within_one = True
    if expected_priority:
        expected_prio = expected_priority.upper()
        priority_match = result.priority == expected_prio
        actual_level = PRIORITY_LEVELS.get(result.priority, 1)
        expected_level = PRIORITY_LEVELS.get(expected_prio, 1)
        priority_within_one = abs(actual_level - expected_level) <= 1

    confidence_ok = result.confidence >= min_confidence

    similarity_score = 1.0 if category_match else 0.0
    keyword_coverage = result.confidence
    final_score = (0.6 * similarity_score) + (0.4 * keyword_coverage)

    passed = category_match and confidence_ok
    is_hallucination = result.confidence < 0.35 and not category_match

    failure_reason = None
    if not category_match:
        failure_reason = f"wrong_category: got {result.category}, expected {expected_cat}"
    elif not confidence_ok:
        failure_reason = f"low_confidence: {result.confidence:.2f} < {min_confidence}"

    return {
        "category_match": category_match,
        "priority_match": priority_match,
        "priority_within_one": priority_within_one,
        "confidence_ok": confidence_ok,
        "similarity_score": round(similarity_score, 4),
        "keyword_coverage": round(keyword_coverage, 4),
        "final_score": round(final_score, 4),
        "passed": passed,
        "is_hallucination": is_hallucination,
        "failure_reason": failure_reason,
        "actual": {
            "category": result.category,
            "priority": result.priority,
            "confidence": result.confidence,
            "tags": result.tags,
        },
    }


def get_resolvehub_adapter() -> ResolvehubEvalAdapter:
    return ResolvehubEvalAdapter(
        base_url=settings.RESOLVEHUB_API_URL,
        eval_secret=settings.RESOLVEHUB_EVAL_SECRET,
        timeout=settings.RESOLVEHUB_EVAL_TIMEOUT,
    )
