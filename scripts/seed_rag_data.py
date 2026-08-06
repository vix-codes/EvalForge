#!/usr/bin/env python3
"""Seed sample RAG dataset into EvalForge PostgreSQL database."""

import asyncio
import json
import sys
from pathlib import Path

import httpx

BASE_URL = sys.argv[1] if len(sys.argv) > 1 else "http://localhost:8000"
API = f"{BASE_URL}/api/v1"
RAG_DATASET_FILE = Path(__file__).parent.parent / "backend" / "data" / "rag_dataset.json"


async def seed_rag():
    if not RAG_DATASET_FILE.exists():
        print(f"Error: {RAG_DATASET_FILE} not found.")
        sys.exit(1)

    data = json.loads(RAG_DATASET_FILE.read_text(encoding="utf-8"))

    async with httpx.AsyncClient(base_url=API, timeout=30) as client:
        # 1. Create RAG Evaluation Suite
        resp = await client.post("/suites", json=data["suite"])
        resp.raise_for_status()
        suite = resp.json()
        suite_id = suite["id"]
        print(f"Created RAG Eval Suite: {suite['name']} ({suite_id})")

        # 2. Bulk create questions
        resp = await client.post(
            f"/suites/{suite_id}/questions/bulk",
            json={"questions": data["questions"]},
        )
        resp.raise_for_status()
        questions = resp.json()
        print(f"Created {len(questions)} RAG golden questions")

        print(f"\nRAG Suite ID: {suite_id}")
        print("You can now trigger RAG runs against this suite using:")
        print(f"  evalforge test --target-type rag --suite-id {suite_id}")


if __name__ == "__main__":
    asyncio.run(seed_rag())
