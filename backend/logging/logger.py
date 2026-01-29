"""
Formal trace logging: every interaction as JSONL.
Trace: USER_INPUT → MODEL_OUTPUT → WRAPPER_DECISION → ...
"""

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, List


def ensure_log_dir(log_dir: str) -> Path:
    p = Path(log_dir)
    p.mkdir(parents=True, exist_ok=True)
    return p


def log_trace(
    log_path: str,
    log_dir: str,
    timestamp: str,
    model_name: str,
    wrapper_name: str,
    wrapper_config: dict,
    user_prompt: str,
    raw_model_outputs: List[str],
    wrapper_decisions: List[str],
    final_output: str,
    total_model_calls: int,
    wrapper_state: dict,
) -> None:
    """
    Append one JSONL record for a single run.
    """
    dir_path = ensure_log_dir(log_dir)
    file_path = dir_path / log_path
    record = {
        "timestamp": timestamp,
        "model_name": model_name,
        "wrapper_name": wrapper_name,
        "wrapper_config": wrapper_config,
        "user_prompt": user_prompt,
        "raw_model_outputs": raw_model_outputs,
        "wrapper_decisions": wrapper_decisions,
        "final_output": final_output,
        "total_model_calls": total_model_calls,
        "wrapper_state": wrapper_state,
    }
    with open(file_path, "a", encoding="utf-8") as f:
        f.write(json.dumps(record, ensure_ascii=False) + "\n")
