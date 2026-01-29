"""
Flask frontend: dashboard for Safety Wrappers research.
Talks to FastAPI backend via HTTP.
"""

import os
from pathlib import Path
from urllib.parse import urljoin

import requests
from dotenv import load_dotenv
from flask import Flask, render_template, request, jsonify

# Load .env from project root (parent of frontend/)
_env_dir = Path(__file__).resolve().parent.parent
load_dotenv(_env_dir / ".env")

app = Flask(__name__)


def _backend_url(path: str) -> str:
    base = (os.environ.get("BACKEND_URL") or "http://127.0.0.1:8000").strip().rstrip("/")
    return urljoin(base + "/", path.lstrip("/"))


_DEFAULT_WRAPPERS = [
    {"id": "noop", "label": "No filter (baseline)", "description": "No safety check. Use to compare with other options."},
    {"id": "keyword", "label": "Block harmful keywords", "description": "Blocks prompts containing banned words (e.g. bomb, hack, weapon). Best for stopping obviously harmful requests."},
    {"id": "history", "label": "History-based", "description": "Avoids empty or repeated answers by re-asking the model (bounded history)."},
    {"id": "query_budget", "label": "Query budget", "description": "Limits how many times the model is called per request. Useful for cost control."},
]


def get_wrappers():
    try:
        r = requests.get(_backend_url("wrappers"), timeout=5)
        if r.ok:
            raw = r.json().get("wrappers", _DEFAULT_WRAPPERS)
            if raw and isinstance(raw[0], dict):
                return raw
            return [{"id": w, "label": w, "description": ""} for w in (raw or ["noop", "keyword", "history", "query_budget"])]
    except Exception:
        pass
    return _DEFAULT_WRAPPERS


@app.route("/")
def index():
    wrappers = get_wrappers()
    min_q, max_q, default_q = get_query_budget_config()
    return render_template(
        "index.html",
        wrappers=wrappers,
        query_budget_min=min_q,
        query_budget_max=max_q,
        query_budget_default=default_q,
    )


def get_query_budget_config():
    try:
        r = requests.get(_backend_url("config"), timeout=5)
        if r.ok:
            qb = r.json().get("query_budget", {})
            return qb.get("min_queries", 1), qb.get("max_queries", 10), qb.get("default_queries", 2)
    except Exception:
        pass
    return 1, 10, 2


@app.route("/query", methods=["POST"])
def query():
    data = request.get_json(force=True, silent=True) or {}
    prompt = data.get("prompt", "")
    wrapper_name = data.get("wrapper_name", "noop")
    max_queries = data.get("max_queries")
    payload = {"prompt": prompt, "wrapper_name": wrapper_name}
    if wrapper_name == "query_budget" and max_queries is not None:
        payload["max_queries"] = max_queries
    try:
        r = requests.post(
            _backend_url("query"),
            json=payload,
            timeout=120,
        )
        r.raise_for_status()
        return jsonify(r.json())
    except requests.RequestException as e:
        return jsonify({"error": str(e)}), 502


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=False)
