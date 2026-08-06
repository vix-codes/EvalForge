"""
Lightweight RAG Pipeline Service using LangChain and Chroma Vector Store.

Features:
- Ingests Markdown (.md) and PDF (.pdf) documents from the /docs directory.
- Chunks documents using RecursiveCharacterTextSplitter.
- Embeds and stores chunks in Chroma vector store.
- Retrieves relevant context chunks and passes them to Ollama/Gemini for generation.
"""

import glob
import os
import time
from pathlib import Path
from typing import Any

from app.core.config import settings
from app.core.logging import get_logger
from app.services.ollama import get_ollama_adapter

logger = get_logger(__name__)

_vectorstore_instance = None


def get_docs_dir() -> Path:
    """Resolve absolute path to docs directory."""
    # Check project root / docs, then current working directory / docs
    possible_paths = [
        Path(settings.DOCS_DIR),
        Path(__file__).parent.parent.parent.parent / "docs",
        Path.cwd() / "docs",
    ]
    for p in possible_paths:
        if p.exists() and p.is_dir():
            return p.resolve()
    
    # Fallback create default docs directory
    default_dir = (Path.cwd() / "docs").resolve()
    default_dir.mkdir(parents=True, exist_ok=True)
    return default_dir


def load_documents_from_dir(docs_dir: Path) -> list[dict[str, str]]:
    """Load text content from .md and .pdf files in docs directory."""
    docs = []
    
    # Process Markdown files
    for md_path in docs_dir.glob("**/*.md"):
        try:
            content = md_path.read_text(encoding="utf-8")
            if content.strip():
                docs.append({
                    "content": content,
                    "source": md_path.name,
                    "path": str(md_path)
                })
        except Exception as exc:
            logger.warning("rag.load_md.failed", file=str(md_path), error=str(exc))

    # Process PDF files if pypdf is available
    for pdf_path in docs_dir.glob("**/*.pdf"):
        try:
            from pypdf import PdfReader
            reader = PdfReader(str(pdf_path))
            text = ""
            for page in reader.pages:
                extracted = page.extract_text()
                if extracted:
                    text += extracted + "\n"
            if text.strip():
                docs.append({
                    "content": text,
                    "source": pdf_path.name,
                    "path": str(pdf_path)
                })
        except Exception as exc:
            logger.warning("rag.load_pdf.failed", file=str(pdf_path), error=str(exc))

    return docs


def split_documents(docs: list[dict[str, str]]) -> list[dict[str, Any]]:
    """Split raw document dicts into smaller text chunks."""
    from langchain_text_splitters import RecursiveCharacterTextSplitter
    
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=settings.RAG_CHUNK_SIZE,
        chunk_overlap=settings.RAG_CHUNK_OVERLAP,
    )
    
    chunks = []
    chunk_id = 0
    for doc in docs:
        split_texts = splitter.split_text(doc["content"])
        for idx, text in enumerate(split_texts):
            chunks.append({
                "id": f"{doc['source']}_chunk_{idx}",
                "text": text,
                "metadata": {
                    "source": doc["source"],
                    "chunk_index": idx,
                    "doc_path": doc["path"],
                }
            })
            chunk_id += 1

    return chunks


def get_embedding_function():
    """Returns local HuggingFace embeddings or lightweight fallback embeddings."""
    try:
        from langchain_huggingface import HuggingFaceEmbeddings
        return HuggingFaceEmbeddings(model_name=settings.EMBEDDING_MODEL_NAME)
    except ImportError:
        try:
            from langchain_community.embeddings import HuggingFaceEmbeddings
            return HuggingFaceEmbeddings(model_name=settings.EMBEDDING_MODEL_NAME)
        except Exception as exc:
            logger.warning("rag.embeddings.fallback", error=str(exc))
            # Basic SentenceTransformer fallback or Chroma default
            return None


def initialize_vectorstore(force_reindex: bool = False) -> Any:
    """Builds or loads persistent Chroma vector store from ingested docs."""
    global _vectorstore_instance
    if _vectorstore_instance is not None and not force_reindex:
        return _vectorstore_instance

    docs_dir = get_docs_dir()
    logger.info("rag.vectorstore.initializing", docs_dir=str(docs_dir))

    raw_docs = load_documents_from_dir(docs_dir)
    chunks = split_documents(raw_docs)
    logger.info("rag.docs.chunked", total_docs=len(raw_docs), total_chunks=len(chunks))

    texts = [c["text"] for c in chunks]
    metadatas = [c["metadata"] for c in chunks]
    ids = [c["id"] for c in chunks]

    embedding_fn = get_embedding_function()

    try:
        from langchain_chroma import Chroma
        if embedding_fn:
            store = Chroma(
                collection_name="evalforge_docs",
                embedding_function=embedding_fn,
                persist_directory=settings.CHROMA_PERSIST_DIR,
            )
        else:
            store = Chroma(
                collection_name="evalforge_docs",
                persist_directory=settings.CHROMA_PERSIST_DIR,
            )

        if texts and (force_reindex or store._collection.count() == 0):
            store.add_texts(texts=texts, metadatas=metadatas, ids=ids)
            logger.info("rag.vectorstore.indexed", count=len(texts))

        _vectorstore_instance = store
        return store

    except Exception as exc:
        logger.error("rag.vectorstore.failed", error=str(exc))
        # Lightweight in-memory fallback store
        return InMemStore(chunks)


class InMemStore:
    """Simple in-memory vector/keyword retrieval fallback if Chroma fails."""
    def __init__(self, chunks: list[dict[str, Any]]):
        self.chunks = chunks

    def similarity_search_with_score(self, query: str, k: int = 3) -> list[tuple[Any, float]]:
        query_words = set(query.lower().split())
        scored = []
        for c in self.chunks:
            text_words = set(c["text"].lower().split())
            overlap = len(query_words & text_words)
            score = overlap / (len(query_words) or 1)
            scored.append((DocObj(c["text"], c["metadata"]), score))
        scored.sort(key=lambda x: x[1], reverse=True)
        return scored[:k]

    def similarity_search(self, query: str, k: int = 3) -> list[Any]:
        return [doc for doc, _ in self.similarity_search_with_score(query, k=k)]


class DocObj:
    def __init__(self, page_content: str, metadata: dict):
        self.page_content = page_content
        self.metadata = metadata


async def retrieve_contexts(query: str, top_k: int = None) -> list[dict[str, Any]]:
    """Retrieve top-k relevant context chunks for a query."""
    top_k = top_k or settings.RAG_TOP_K
    store = initialize_vectorstore()

    try:
        if hasattr(store, "similarity_search_with_score"):
            results = store.similarity_search_with_score(query, k=top_k)
            retrieved = []
            for doc_item in results:
                if isinstance(doc_item, tuple):
                    doc, score = doc_item[0], float(doc_item[1])
                else:
                    doc, score = doc_item, 1.0
                retrieved.append({
                    "content": getattr(doc, "page_content", str(doc)),
                    "source": getattr(doc, "metadata", {}).get("source", "unknown"),
                    "score": round(score, 4),
                })
            return retrieved
        else:
            docs = store.similarity_search(query, k=top_k)
            return [
                {
                    "content": getattr(d, "page_content", str(d)),
                    "source": getattr(d, "metadata", {}).get("source", "unknown"),
                    "score": 1.0,
                }
                for d in docs
            ]
    except Exception as exc:
        logger.error("rag.retrieve.failed", query=query, error=str(exc))
        return []


async def execute_rag_pipeline(
    question: str,
    model_name: str,
    endpoint_url: str | None = None,
    system_prompt: str | None = None,
) -> dict[str, Any]:
    """Execute complete RAG pipeline: Retrieve context -> Construct prompt -> LLM inference."""
    start_time = time.perf_counter()

    # 1. Retrieve top-k context chunks
    contexts = await retrieve_contexts(question, top_k=settings.RAG_TOP_K)
    context_str = "\n\n".join(
        [f"[Source: {c['source']}]\n{c['content']}" for c in contexts]
    )

    # 2. Build RAG system prompt & prompt
    base_sys_prompt = system_prompt or "You are an assistant answering questions based strictly on the provided context."
    rag_prompt = (
        f"Context Information:\n{context_str}\n\n"
        f"Question: {question}\n\n"
        "Provide a concise, factual answer based strictly on the context above."
    )

    # 3. Generate LLM inference
    adapter = get_ollama_adapter(base_url=endpoint_url)
    inference = await adapter.generate(
        prompt=rag_prompt,
        model=model_name,
        system_prompt=base_sys_prompt,
    )

    elapsed_ms = (time.perf_counter() - start_time) * 1000

    return {
        "model_response": inference.response,
        "retrieved_contexts": contexts,
        "latency_ms": round(elapsed_ms, 2),
    }
