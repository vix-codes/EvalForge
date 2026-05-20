#!/usr/bin/env python3
"""
Seed the ResolveHub golden dataset into EvalForge.
Run: python scripts/seed_resolvehub_suite.py
Requires: EVALFORGE_API_URL env var or defaults to localhost:8765
"""
import json
import os
import sys
from pathlib import Path

import httpx

BASE_URL = os.environ.get("EVALFORGE_API_URL", "http://localhost:8765").rstrip("/")
DATASET_FILE = Path(__file__).parent.parent / "data" / "resolvehub_golden_dataset.json"


def main():
    data = json.loads(DATASET_FILE.read_text())
    suite_meta = data["suite"]
    questions = data["questions"]

    print(f"Connecting to EvalForge at {BASE_URL}")
    print(f"Creating suite: {suite_meta['name']}")

    with httpx.Client(base_url=BASE_URL, timeout=30) as client:
        resp = client.post("/api/v1/suites", json=suite_meta)
        if resp.status_code not in (200, 201):
            print(f"Failed to create suite: {resp.status_code} {resp.text}")
            sys.exit(1)

        suite_id = resp.json()["id"]
        print(f"Created suite: {suite_id}")

        resp = client.post(
            f"/api/v1/suites/{suite_id}/questions/bulk",
            json={"questions": questions},
        )
        if resp.status_code not in (200, 201):
            print(f"Failed to bulk import questions: {resp.status_code} {resp.text}")
            sys.exit(1)

        created = resp.json()
        print(f"Imported {len(created)} questions into suite {suite_id}")
        print(f"\nResolveHub eval suite ready. Suite ID: {suite_id}")
        print(f"Trigger eval: POST {BASE_URL}/api/v1/resolvehub/eval")


if __name__ == "__main__":
    main()
