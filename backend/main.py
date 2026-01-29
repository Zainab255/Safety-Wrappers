"""
FastAPI entry: black-box model + safety wrappers as finite-state monitors.
"""

import os
from datetime import datetime, timezone
from pathlib import Path

import uvicorn
import yaml
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException

# Load .env from project root so OPENROUTER_API_KEY is available
_root = Path(__file__).resolve().parent.parent
load_dotenv(_root / ".env")
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from backend.logging.logger import log_trace
from backend.models.openrouter_gemini import complete as model_complete
from backend.wrappers import get_wrapper
from backend.wrappers.base import Action

app = FastAPI(title="Safety Wrappers Research API")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

_CONFIG: dict = {}


def load_config() -> dict:
    global _CONFIG
    if _CONFIG:
        return _CONFIG
    root = Path(__file__).resolve().parent.parent
    config_path = Path(__file__).resolve().parent / "config" / "config.yaml"
    if not config_path.exists():
        config_path = root / "config" / "config.yaml"
    with open(config_path, "r", encoding="utf-8") as f:
        _CONFIG = yaml.safe_load(f)
    return _CONFIG


class QueryRequest(BaseModel):
    prompt: str
    wrapper_name: str | None = None
    max_queries: int | None = None  # For query_budget: max model calls per request (1–10)


class QueryResponse(BaseModel):
    final_output: str
    wrapper_decision: str
    decision_summary: str
    model_call_count: int
    raw_outputs: list[str]
    decisions_sequence: list[str]


def get_wrapper_config(cfg: dict, wrapper_name: str) -> dict:
    w = cfg.get("wrappers", {})
    if wrapper_name == "keyword":
        return w.get("keyword", {})
    if wrapper_name == "history":
        return w.get("history", {})
    if wrapper_name == "query_budget":
        return w.get("query_budget", {})
    return {}


@app.post("/query", response_model=QueryResponse)
async def query(req: QueryRequest):
    cfg = load_config()
    model_name = cfg.get("model", {}).get("name", "google/gemini-2.5-flash-lite")
    base_url = cfg.get("openrouter", {}).get("base_url", "https://openrouter.ai/api/v1")
    api_key = os.environ.get("OPENROUTER_API_KEY")
    wrapper_name = req.wrapper_name or cfg.get("wrappers", {}).get("default", "noop")
    wrapper_config = get_wrapper_config(cfg, wrapper_name)
    log_cfg = cfg.get("logging", {})
    log_dir = log_cfg.get("log_dir", "logs")
    trace_file = log_cfg.get("trace_file", "traces.jsonl")

    # Resolve log_dir relative to project root
    root = Path(__file__).resolve().parent.parent
    log_dir_abs = root / log_dir
    log_dir_abs.mkdir(parents=True, exist_ok=True)

    # Empty prompt handling: no model call, no safety decision
    prompt = (req.prompt or "").strip()
    if not prompt:
        return QueryResponse(
            final_output="[Empty prompt]",
            wrapper_decision="SKIP",
            decision_summary="No prompt entered; no model call. No safety decision applied.",
            model_call_count=0,
            raw_outputs=[],
            decisions_sequence=[],
        )

    wrapper = get_wrapper(wrapper_name, wrapper_config)
    wrapper.reset()

    max_queries = cfg.get("wrappers", {}).get("query_budget", {}).get("max_queries", 2)
    history_k = cfg.get("wrappers", {}).get("history", {}).get("k", 3)
    if wrapper_name == "query_budget":
        user_limit = req.max_queries
        if user_limit is not None and 1 <= user_limit <= 10:
            max_calls = user_limit
        else:
            max_calls = int(wrapper_config.get("max_queries", max_queries))
    elif wrapper_name == "history":
        max_calls = max(int(max_queries), int(wrapper_config.get("k", history_k)) + 2)
    else:
        max_calls = int(max_queries)

    # Keyword: pre-check prompt before calling model (block harmful prompts with 0 API calls)
    if wrapper_name == "keyword":
        pre_action, pre_output = wrapper.step(prompt, "", 0)
        if pre_action == Action.BLOCK:
            timestamp = datetime.now(timezone.utc).isoformat()
            log_trace(
                log_path=trace_file,
                log_dir=str(log_dir_abs),
                timestamp=timestamp,
                model_name=model_name,
                wrapper_name=wrapper_name,
                wrapper_config=wrapper_config,
                user_prompt=prompt,
                raw_model_outputs=[],
                wrapper_decisions=[Action.BLOCK.value],
                final_output=pre_output,
                total_model_calls=0,
                wrapper_state=wrapper.get_state(),
            )
            return QueryResponse(
                final_output=pre_output,
                wrapper_decision=Action.BLOCK.value,
                decision_summary="Blocked: your prompt contained a banned or harmful keyword. No model call made.",
                model_call_count=0,
                raw_outputs=[],
                decisions_sequence=[Action.BLOCK.value],
            )

    raw_outputs: list[str] = []
    decisions_sequence: list[str] = []
    final_output = ""
    call_index = 0

    while call_index < max_calls:
        try:
            out = await model_complete(
                prompt,
                model_name=model_name,
                base_url=base_url,
                api_key=api_key,
            )
        except Exception as e:
            raise HTTPException(status_code=502, detail=str(e))

        raw_outputs.append(out)
        action, output_to_use = wrapper.step(prompt, out, call_index)
        decisions_sequence.append(action.value)

        if action == Action.ALLOW:
            final_output = output_to_use
            break
        if action == Action.BLOCK:
            final_output = output_to_use
            break
        if action == Action.MODIFY:
            final_output = output_to_use
            break
        if action == Action.REQUERY:
            call_index += 1
            if call_index >= max_calls:
                final_output = raw_outputs[-1] if raw_outputs else ""
                break
            continue

    last_decision = decisions_sequence[-1] if decisions_sequence else Action.ALLOW.value
    num_calls = len(raw_outputs)
    if wrapper_name == "keyword" and last_decision == Action.BLOCK.value:
        decision_summary = "Blocked: your prompt contained a banned or harmful keyword."
    elif wrapper_name == "keyword" and last_decision == Action.ALLOW.value:
        decision_summary = "Allowed: no banned keywords detected in your prompt."
    elif wrapper_name == "noop":
        decision_summary = "No filter applied (baseline). Response was not checked for safety."
    elif wrapper_name == "history":
        if Action.REQUERY.value in decisions_sequence:
            decision_summary = f"History: re-queried due to empty or duplicate output; allowed after {num_calls} call(s)."
        else:
            decision_summary = f"History: response allowed after 1 call (no empty or duplicate)."
    elif wrapper_name == "query_budget":
        decision_summary = f"Query budget: up to {max_calls} call(s); used {num_calls}."
    else:
        decision_summary = f"Decision: {last_decision}."

    timestamp = datetime.now(timezone.utc).isoformat()
    log_trace(
        log_path=trace_file,
        log_dir=str(log_dir_abs),
        timestamp=timestamp,
        model_name=model_name,
        wrapper_name=wrapper_name,
        wrapper_config=wrapper_config,
        user_prompt=prompt,
        raw_model_outputs=raw_outputs,
        wrapper_decisions=decisions_sequence,
        final_output=final_output,
        total_model_calls=len(raw_outputs),
        wrapper_state=wrapper.get_state(),
    )

    return QueryResponse(
        final_output=final_output,
        wrapper_decision=last_decision,
        decision_summary=decision_summary,
        model_call_count=len(raw_outputs),
        raw_outputs=raw_outputs,
        decisions_sequence=decisions_sequence,
    )


@app.get("/wrappers")
async def list_wrappers():
    return {
        "wrappers": [
            {"id": "noop", "label": "No filter (baseline)", "description": "No safety check. Use to compare with other options."},
            {"id": "keyword", "label": "Block harmful keywords", "description": "Blocks prompts containing banned words (e.g. bomb, hack, weapon). Best for stopping obviously harmful requests."},
            {"id": "history", "label": "History-based", "description": "Avoids empty or repeated answers by re-asking the model (bounded history)."},
            {"id": "query_budget", "label": "Query budget", "description": "Limits how many times the model is called per request. Useful for cost control."},
        ]
    }


@app.get("/config")
async def get_config():
    cfg = load_config()
    qb = cfg.get("wrappers", {}).get("query_budget", {})
    return {
        "model_name": cfg.get("model", {}).get("name"),
        "default_wrapper": cfg.get("wrappers", {}).get("default"),
        "wrapper_configs": cfg.get("wrappers", {}),
        "query_budget": {
            "min_queries": 1,
            "max_queries": 10,
            "default_queries": int(qb.get("max_queries", 2)),
        },
    }


if __name__ == "__main__":
    load_config()
    uvicorn.run(app, host="0.0.0.0", port=8000)
