# EvalForge Architecture Overview

EvalForge is an enterprise AI evaluation and benchmarking platform designed to test LLMs and RAG pipelines against golden datasets.

## Core System Components

1. **FastAPI Application Backend**:
   - Provides RESTful APIs for suite management, golden questions, evaluation run triggering, and quality analytics.
   - Built on Python 3.11+ using asynchronous SQLAlchemy 2.0 with PostgreSQL.

2. **Celery Worker Pipeline**:
   - Asynchronous worker queue powered by Redis broker.
   - Executes evaluation batches in background worker processes without blocking API routes.
   - Handles LLM inference calls, vector retrieval, and LLM-as-judge scoring.

3. **Chroma Vector Store & RAG Engine**:
   - Local Chroma vector database for storing document embeddings.
   - Ingests Markdown and PDF documents from the `/docs` directory.
   - Uses `RecursiveCharacterTextSplitter` with default chunk size of 500 characters and 50 character overlap.
   - Uses HuggingFace `all-MiniLM-L6-v2` embedding model for fast semantic retrieval.

4. **Quality Gates & Metrics**:
   - Automated quality gates enforcing strict pass rate thresholds (min 80%), max hallucination rate (max 15%), and p95 latency targets (max 10,000 ms).
