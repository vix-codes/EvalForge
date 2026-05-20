import math
import re
from dataclasses import dataclass, field

from app.core.config import settings
from app.core.logging import get_logger
from app.services.gemini import GeminiError, get_gemini_judge

logger = get_logger(__name__)


@dataclass
class ScoringResult:
    similarity_score: float
    keyword_coverage: float
    gemini_score: float | None
    gemini_reasoning: str | None
    final_score: float
    passed: bool
    is_hallucination: bool
    failure_reason: str | None
    metadata: dict = field(default_factory=dict)


def _normalize(text: str) -> str:
    return re.sub(r"\s+", " ", text.lower().strip())


def _tokenize(text: str) -> list[str]:
    return re.findall(r"\b[a-z0-9]+\b", _normalize(text))


def _tfidf_vector(tokens: list[str], vocab: set[str]) -> dict[str, float]:
    freq: dict[str, int] = {}
    for t in tokens:
        freq[t] = freq.get(t, 0) + 1
    total = len(tokens) or 1
    return {w: freq.get(w, 0) / total for w in vocab}


def cosine_similarity(text_a: str, text_b: str) -> float:
    tokens_a = _tokenize(text_a)
    tokens_b = _tokenize(text_b)
    if not tokens_a or not tokens_b:
        return 0.0
    vocab = set(tokens_a) | set(tokens_b)
    vec_a = _tfidf_vector(tokens_a, vocab)
    vec_b = _tfidf_vector(tokens_b, vocab)
    dot = sum(vec_a[w] * vec_b[w] for w in vocab)
    mag_a = math.sqrt(sum(v ** 2 for v in vec_a.values()))
    mag_b = math.sqrt(sum(v ** 2 for v in vec_b.values()))
    if mag_a == 0 or mag_b == 0:
        return 0.0
    return round(dot / (mag_a * mag_b), 4)


def keyword_coverage(response: str, keywords_str: str | None, golden_answer: str) -> float:
    if keywords_str:
        keywords = [k.strip().lower() for k in keywords_str.split(",") if k.strip()]
    else:
        tokens_golden = _tokenize(golden_answer)
        # Use top non-trivial words from golden answer as implicit keywords
        stopwords = {"the", "a", "an", "is", "are", "was", "were", "be", "been",
                     "being", "have", "has", "had", "do", "does", "did", "will",
                     "would", "shall", "should", "may", "might", "must", "can",
                     "could", "of", "in", "on", "at", "to", "for", "with", "by",
                     "from", "as", "into", "through", "during", "about", "and",
                     "or", "but", "not", "it", "its", "this", "that"}
        keywords = [t for t in tokens_golden if t not in stopwords and len(t) > 3][:10]

    if not keywords:
        return 1.0

    normalized_response = _normalize(response)
    covered = sum(1 for k in keywords if k in normalized_response)
    return round(covered / len(keywords), 4)


def detect_hallucination(similarity: float, keyword_cov: float) -> bool:
    return (
        similarity < settings.HALLUCINATION_SIMILARITY_THRESHOLD
        and keyword_cov < settings.HALLUCINATION_KEYWORD_THRESHOLD
    )


async def score_response(
    question: str,
    golden_answer: str,
    model_response: str,
    expected_keywords: str | None = None,
    use_gemini: bool | None = None,
) -> ScoringResult:
    use_gemini_judge = (
        settings.GEMINI_JUDGE_ENABLED if use_gemini is None else use_gemini
    )

    if not model_response or not model_response.strip():
        return ScoringResult(
            similarity_score=0.0,
            keyword_coverage=0.0,
            gemini_score=None,
            gemini_reasoning=None,
            final_score=0.0,
            passed=False,
            is_hallucination=True,
            failure_reason="empty_response",
            metadata={"error": "model returned empty response"},
        )

    sim = cosine_similarity(golden_answer, model_response)
    kw_cov = keyword_coverage(model_response, expected_keywords, golden_answer)
    is_hallucination = detect_hallucination(sim, kw_cov)

    gemini_score: float | None = None
    gemini_reasoning: str | None = None

    if use_gemini_judge and settings.GEMINI_API_KEY:
        try:
            judge = get_gemini_judge()
            gemini_score, gemini_reasoning = await judge.judge(
                question, golden_answer, model_response
            )
        except GeminiError as exc:
            logger.warning("scoring.gemini_judge.skipped", error=str(exc))

    if gemini_score is not None:
        final_score = (sim * 0.35) + (kw_cov * 0.25) + (gemini_score * 0.40)
    else:
        final_score = (sim * 0.60) + (kw_cov * 0.40)

    final_score = round(final_score, 4)
    passed = (
        final_score >= settings.SIMILARITY_THRESHOLD
        and kw_cov >= settings.KEYWORD_COVERAGE_THRESHOLD
        and not is_hallucination
    )

    failure_reason: str | None = None
    if is_hallucination:
        failure_reason = "hallucination_detected"
    elif final_score < settings.SIMILARITY_THRESHOLD:
        failure_reason = "low_similarity"
    elif kw_cov < settings.KEYWORD_COVERAGE_THRESHOLD:
        failure_reason = "low_keyword_coverage"

    logger.debug(
        "scoring.result",
        similarity=sim,
        keyword_coverage=kw_cov,
        gemini_score=gemini_score,
        final_score=final_score,
        passed=passed,
        is_hallucination=is_hallucination,
    )

    return ScoringResult(
        similarity_score=sim,
        keyword_coverage=kw_cov,
        gemini_score=gemini_score,
        gemini_reasoning=gemini_reasoning,
        final_score=final_score,
        passed=passed,
        is_hallucination=is_hallucination,
        failure_reason=failure_reason,
        metadata={
            "weights": {
                "similarity": 0.35 if gemini_score is not None else 0.60,
                "keyword_coverage": 0.25 if gemini_score is not None else 0.40,
                "gemini": 0.40 if gemini_score is not None else 0.0,
            }
        },
    )
