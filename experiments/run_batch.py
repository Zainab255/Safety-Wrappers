"""
Batch experiment: run risky and benign prompts through wrappers, log traces.
"""

import asyncio
import json
import os
import sys
from pathlib import Path

# Project root
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import httpx

BACKEND_URL = os.environ.get("BACKEND_URL", "http://127.0.0.1:8000")


def load_prompts(path: Path) -> list:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


async def run_one(client: httpx.AsyncClient, prompt: str, wrapper: str) -> dict:
    r = await client.post(
        f"{BACKEND_URL}/query",
        json={"prompt": prompt, "wrapper_name": wrapper},
        timeout=120.0,
    )
    r.raise_for_status()
    return r.json()


async def main():
    risky_path = ROOT / "data" / "risky_prompts.json"
    benign_path = ROOT / "data" / "benign_prompts.json"
    if not risky_path.exists() or not benign_path.exists():
        print("Missing data/risky_prompts.json or data/benign_prompts.json")
        sys.exit(1)

    risky = load_prompts(risky_path)
    benign = load_prompts(benign_path)
    wrappers = ["noop", "keyword", "history", "query_budget"]

    async with httpx.AsyncClient() as client:
        for label, prompts in [("risky", risky), ("benign", benign)]:
            for wrapper in wrappers:
                for i, prompt in enumerate(prompts):
                    try:
                        out = await run_one(client, prompt, wrapper)
                        print(f"{label} {wrapper} [{i}] calls={out.get('model_call_count', 0)}")
                    except Exception as e:
                        print(f"{label} {wrapper} [{i}] error: {e}")

    print("Batch done. Check logs/ for traces.jsonl.")


if __name__ == "__main__":
    asyncio.run(main())
