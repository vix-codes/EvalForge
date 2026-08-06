"""
RAGAS-Style Metrics Scoring Service for RAG Evaluation Target.

Calculates three essential RAG evaluation metrics:
1. Faithfulness: Degree to which the response is grounded in the retrieved contexts.
2. Answer Relevance: Degree to which the response directly answers the user query.
3. Context Precision: Precision@K ranking quality of retrieved context chunks against golden answer & question.

Uses Ollama LLM-as-judge scoring with deterministic local NLP fallback heuristics.
"""

import json
import re
from dataclasses import dataclass
from typing import Any

from app.core.config import settings
from app.core.logging import get_logger
from app.services.ollama import get_ollama_adapter
from app.services.scoring import cosine_similarity, keyword_coverage

logger = get_logger(__name__)


@dataclass
class RAGScoringResult:
    faithfulness: float
    answer_relevance: float
    context_precision: float
    similarity_score: float
    keyword_coverage: float
    final_score: float
    passed: bool
    is_hallucination: bool
    failure_reason: str | None
    scoring_metadata: dict[str, Any]


def extract_json_score(response_text: str, default: float = 0.5) -> float:
    """Extract numeric score (0.0 - 1.0) from LLM response text or JSON."""
    if not response_text:
        return default
    
    # Try finding JSON {"score": 0.85}
    match = re.search(r'\{\s*"score"\s*:\s*([0-9\.]+)', response_text, re.IGNORECASE)
    if match:
        try:
            val = float(match.group(1))
            return max(0.0, min(1.0, val))
        except ValueError:
            pass

    # Try finding "Score: 0.85" or plain numbers
    match = re.search(r'(?:score|rating|value)\s*[:=]\s*([0-9\.]+)', response_text, re.IGNORECASE)
    if match:
        try:
            val = float(match.group(1))
            return max(0.0, min(1.0, val))
        except ValueError:
            pass

    # Find any standalone decimal between 0 and 1
    floats = re.findall(r'\b0\.[0-9]+\b|\b1\.0\b|\b0\b|\b1\b', response_text)
    if floats:
        try:
            val = float(floats[0])
            return max(0.0, min(1.0, val))
        except ValueError:
            pass

    return default


async def score_faithfulness(
    model_response: str,
    retrieved_contexts: list[dict[str, Any]],
    model_name: str | None = None,
    endpoint_url: str | None = None,
) -> float:
    """Measure if the response statements are supported by retrieved contexts."""
    if not model_response or not retrieved_contexts:
        return 0.0

    context_text = "\n".join([c.get("content", "") for c in retrieved_contexts])
    
    # LLM-as-judge prompt
    prompt = (
        "Evaluate the FAITHFULNESS of the generated answer based ONLY on the provided context.\n"
        "Faithfulness measures if all statements in the answer are directly supported by the context without hallucination.\n\n"
        f"Context:\n{context_text[:1500]}\n\n"
        f"Answer:\n{model_response[:1000]}\n\n"
        "Return ONLY a JSON object: {\"score\": <float between 0.0 and 1.0>, \"reason\": \"<short explanation>\"}"
    )

    try:
        adapter = get_ollama_adapter(base_url=endpoint_url)
        res = await adapter.generate(
            prompt=prompt,
            model=model_name or settings.OLLAMA_DEFAULT_MODEL,
            temperature=0.0,
        )
        score = extract_json_score(res.response, default=-1.0)
        if score >= 0.0:
            return round(score, 4)
    except Exception as exc:
        logger.warning("rag_scoring.faithfulness_llm.failed", error=str(exc))

    # Fallback NLP Heuristic: Chunk/token overlap of response in context
    resp_words = [w.lower() for w in re.findall(r'\b\w{4,}\b', model_response)]
    if not resp_words:
        return 1.0
    context_lower = context_text.lower()
    found = sum(1 for w in resp_words if w in context_lower)
    return round(found / len(resp_words), 4)


async def score_answer_relevance(
    question: str,
    model_response: str,
    model_name: str | None = None,
    endpoint_url: str | None = None,
) -> float:
    """Measure if the model response directly addresses the question."""
    if not model_response:
        return 0.0

    prompt = (
        "Evaluate the RELEVANCE of the answer to the user question.\n"
        "Answer Relevance measures if the response directly addresses the question without off-topic info.\n\n"
        f"Question:\n{question}\n\n"
        f"Answer:\n{model_response[:1000]}\n\n"
        "Return ONLY a JSON object: {\"score\": <float between 0.0 and 1.0>, \"reason\": \"<short explanation>\"}"
    )

    try:
        adapter = get_ollama_adapter(base_url=endpoint_url)
        res = await adapter.generate(
            prompt=prompt,
            model=model_name or settings.OLLAMA_DEFAULT_MODEL,
            temperature=0.0,
        )
        score = extract_json_score(res.response, default=-1.0)
        if score >= 0.0:
            return round(score, 4)
    except Exception as exc:
        logger.warning("rag_scoring.relevance_llm.failed", error=str(exc))

    # Fallback NLP Heuristic: Cosine similarity between question & model response
    return cosine_similarity(question, model_response)


async def score_context_precision(
    question: str,
    golden_answer: str,
    retrieved_contexts: list[dict[str, Any]],
    model_name: str | None = None,
    endpoint_url: str | None = None,
) -> float:
    """
    Calculate Context Precision (Average Precision@K of retrieved chunks against golden answer & question).
    Precision@k = (relevant chunks up to rank k) / k
    Context Precision = Sum(Precision@k * is_relevant_k) / Total Relevant Chunks
    """
    if not retrieved_contexts:
        return 0.0

    relevant_flags = []
    
    for c in retrieved_contexts:
        content = c.get("content", "")
        # Heuristic check + similarity to question & golden answer
        sim_q = cosine_similarity(question, content)
        sim_g = cosine_similarity(golden_answer, content)
        
        # A chunk is relevant if it has strong keyword/similarity overlap with golden answer or question
        is_rel = 1 if (sim_g >= 0.20 or sim_q >= 0.25) else 0
        relevant_flags.append(is_rel)

    if sum(relevant_flags) == 0:
        return 0.0

    precisions = []
    running_rel = 0
    for k, rel in enumerate(relevant_flags, start=1):
        if rel:
            running_rel += 1
            precisions.append(running_rel / k)

    if not precisions:
        return 0.0

    ap = sum(precisions) / len(precisions)
    return round(ap, 4)


async def score_rag_response(
    question: str,
    golden_answer: str,
    model_response: str,
    retrieved_contexts: list[dict[str, Any]],
    expected_keywords: str | None = None,
    model_name: str | None = None,
    endpoint_url: str | None = None,
) -> RAGScoringResult:
    """Comprehensive scoring function for RAG target runs combining RAGAS and standard metrics."""
    if not model_response or not model_response.strip():
        return RAGScoringResult(
            faithfulness=0.0,
            answer_relevance=0.0,
            context_precision=0.0,
            similarity_score=0.0,
            keyword_coverage=0.0,
            final_score=0.0,
            passed=False,
            is_hallucination=True,
            failure_reason="empty_response",
            scoring_metadata={"error": "empty model response"},
        )

    # 1. Compute RAGAS Metrics
    faithfulness = await score_faithfulness(
        model_response=model_response,
        retrieved_contexts=retrieved_contexts,
        model_name=model_name,
        endpoint_url=endpoint_url,
    )

    relevance = await score_answer_relevance(
        question=question,
        model_response=model_response,
        model_name=model_name,
        endpoint_url=endpoint_url,
    )

    precision = await score_context_precision(
        question=question,
        golden_answer=golden_answer,
        retrieved_contexts=retrieved_contexts,
        model_name=model_name,
        endpoint_url=endpoint_url,
    )

    # 2. Standard Similarity & Keyword Metrics
    sim = cosine_similarity(golden_answer, model_response)
    kw_cov = keyword_coverage(model_response, expected_keywords, golden_answer)

    # 3. Overall Weighted Score:
    # 30% Faithfulness + 25% Answer Relevance + 20% Context Precision + 15% Similarity + 10% Keyword Coverage
    final_score = (
        (faithfulness * 0.30)
        + (relevance * 0.25)
        + (precision * 0.20)
        + (sim * 0.15)
        + (kw_cov * 0.10)
    )
    final_score = round(final_score, 4)

    is_hallucination = faithfulness < 0.40 or sim < settings.HALLUCINATION_SIMILARITY_THRESHOLD
    passed = final_score >= settings.SIMILARITY_THRESHOLD and faithfulness >= 0.50 and not is_hallucination

    failure_reason = None
    if is_hallucination:
        failure_reason = "unfaithful_or_hallucinated"
    elif faithfulness < 0.50:
        failure_reason = "low_faithfulness"
    elif relevance < 0.50:
        failure_reason = "low_answer_relevance"
    elif final_score < settings.SIMILARITY_THRESHOLD:
        failure_reason = "low_overall_rag_score"

    return RAGScoringResult(
        faithfulness=faithfulness,
        answer_relevance=relevance,
        context_precision=precision,
        similarity_score=sim,
        keyword_coverage=kw_cov,
        final_score=final_score,
        passed=passed,
        is_hallucination=is_hallucination,
        failure_reason=failure_reason,
        scoring_metadata={
            "retrieved_context_count": len(retrieved_contexts),
            "weights": {
                "faithfulness": 0.30,
                "answer_relevance": 0.25,
                "context_precision": 0.20,
                "similarity": 0.15,
                "keyword_coverage": 0.10,
            },
        },
    )
