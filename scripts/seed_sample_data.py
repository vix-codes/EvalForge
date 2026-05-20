#!/usr/bin/env python3
"""Seed sample evaluation data into EvalForge."""

import asyncio
import json
import sys
from pathlib import Path

import httpx

BASE_URL = sys.argv[1] if len(sys.argv) > 1 else "http://localhost:8000"
API = f"{BASE_URL}/api/v1"
DATASET_FILE = Path(__file__).parent.parent / "backend" / "data" / "sample_dataset.json"


async def seed():
    data = json.loads(DATASET_FILE.read_text())

    async with httpx.AsyncClient(base_url=API, timeout=30) as client:
        # Create suite
        resp = await client.post("/suites", json=data["suite"])
        resp.raise_for_status()
        suite = resp.json()
        suite_id = suite["id"]
        print(f"Created suite: {suite['name']} ({suite_id})")

        # Bulk create questions
        resp = await client.post(
            f"/suites/{suite_id}/questions/bulk",
            json={"questions": data["questions"]},
        )
        resp.raise_for_status()
        questions = resp.json()
        print(f"Created {len(questions)} golden questions")

        print(f"\nSuite ID: {suite_id}")
        print("Set EVALFORGE_SUITE_ID to this value in your CI/CD secrets")


if __name__ == "__main__":
    asyncio.run(seed())
