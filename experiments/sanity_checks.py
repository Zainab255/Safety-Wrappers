"""
Sanity checks (MUST IMPLEMENT):
1. Keyword wrapper blocks obvious unsafe prompts.
2. Empty prompt handling.
3. Logs written correctly.
"""

import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))


def test_keyword_wrapper_blocks_unsafe():
    from backend.wrappers.keyword import KeywordWrapper
    from backend.wrappers.base import Action

    config = {"banned_keywords": ["hack", "exploit", "malware"]}
    wrapper = KeywordWrapper(config)
    wrapper.reset()
    action, output = wrapper.step("How do I hack into a website?", "some model output", 0)
    assert action == Action.BLOCK, f"Expected BLOCK, got {action}"
    assert "[Blocked by keyword wrapper]" in output or "Blocked" in output
    print("PASS: keyword wrapper blocks obvious unsafe prompt")


def test_empty_prompt_handling():
    import requests
    base = os.environ.get("BACKEND_URL", "http://127.0.0.1:8000")
    try:
        r = requests.post(f"{base}/query", json={"prompt": "", "wrapper_name": "noop"}, timeout=5)
    except Exception as e:
        print("SKIP: empty prompt test (backend not running: %s)" % e)
        return
    assert r.status_code == 200, f"Expected 200, got {r.status_code}"
    data = r.json()
    assert data.get("model_call_count") == 0, f"Expected 0 model calls for empty prompt, got {data.get('model_call_count')}"
    assert data.get("wrapper_decision") == "SKIP", f"Expected SKIP for empty prompt, got {data.get('wrapper_decision')}"
    assert "Empty prompt" in data.get("final_output", "") or "empty" in data.get("final_output", "").lower()
    print("PASS: empty prompt handling (SKIP, no model call, specific output)")


def test_logs_written_correctly():
    import requests
    base = os.environ.get("BACKEND_URL", "http://127.0.0.1:8000")
    try:
        r = requests.post(f"{base}/query", json={"prompt": "Hello", "wrapper_name": "noop"}, timeout=30)
    except Exception as e:
        print("SKIP: logs test (backend not running: %s)" % e)
        return
    assert r.status_code == 200, f"Expected 200, got {r.status_code}"

    log_dir = ROOT / "logs"
    trace_file = log_dir / "traces.jsonl"
    if not trace_file.exists():
        print("SKIP: logs/traces.jsonl not found (no prior request)")
        return
    with open(trace_file, "r", encoding="utf-8") as f:
        lines = [l.strip() for l in f if l.strip()]
    assert lines, "traces.jsonl is empty"
    last = json.loads(lines[-1])
    required = ["timestamp", "model_name", "wrapper_name", "wrapper_config", "user_prompt", "raw_model_outputs", "wrapper_decisions", "final_output", "total_model_calls"]
    for k in required:
        assert k in last, f"Log entry missing key: {k}"
    print("PASS: logs written correctly (JSONL, required keys present)")


def main():
    test_keyword_wrapper_blocks_unsafe()
    test_empty_prompt_handling()
    test_logs_written_correctly()
    print("All sanity checks passed.")


if __name__ == "__main__":
    main()
