# RAG Evaluation Guidelines & RAGAS Metrics

EvalForge supports evaluating Retrieval-Augmented Generation (RAG) pipelines using RAGAS-style metrics alongside raw LLM output benchmarking.

## RAGAS Evaluation Metrics

1. **Faithfulness**:
   - Evaluates whether the generated response is strictly grounded in the retrieved context chunks.
   - Prevents hallucinations and unauthorized extrapolation beyond provided documents.
   - Range: 0.0 (unfaithful/hallucinated) to 1.0 (fully grounded).

2. **Answer Relevance**:
   - Measures how directly and completely the generated response answers the user's prompt without introducing off-topic information.
   - Range: 0.0 (irrelevant) to 1.0 (highly relevant).

3. **Context Precision**:
   - Evaluates the retrieval quality of the vector store by calculating Average Precision at rank K (AP@k).
   - Higher scores indicate that the most relevant context chunks are ranked at the top of the retrieved context list.
   - Range: 0.0 (poor ranking) to 1.0 (perfect ranking).

## Evaluation Target Routing

EvalForge supports two evaluation targets:
- `raw_llm`: Evaluates direct LLM outputs without context retrieval.
- `rag`: Evaluates RAG pipelines with document ingestion, chunking, Chroma retrieval, and RAGAS metric calculation.
