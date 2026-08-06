# EvalForge Frequently Asked Questions (FAQ)

## Frequently Asked Questions

### Q1: What vector store does EvalForge use for local RAG evaluations?
EvalForge uses ChromaDB as its local vector store because it requires no external cloud service and persists indexes locally.

### Q2: What embedding model is used by default?
EvalForge uses `sentence-transformers/all-MiniLM-L6-v2` for local, high-speed document embedding and semantic retrieval.

### Q3: How are chunk size and overlap configured?
Document chunking uses `RecursiveCharacterTextSplitter` configured with a chunk size of 500 characters and a chunk overlap of 50 characters.

### Q4: Can I run evaluation jobs against deployed custom LLMs?
Yes, EvalForge supports custom `endpoint_url` overrides per run, allowing you to benchmark any local or deployed Ollama-compatible LLM endpoint.

### Q5: What database does EvalForge use to persist evaluation runs and results?
EvalForge uses PostgreSQL with JSONB columns for flexible scoring metadata and retrieved context persistence.
