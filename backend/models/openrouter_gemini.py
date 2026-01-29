"""
Black-box model backend: Gemini 2.5 Flash Lite via OpenRouter.
No assumptions about internals; API only.
"""

import os
from typing import Optional

import httpx


async def complete(
    prompt: str,
    model_name: str,
    base_url: str,
    api_key: Optional[str] = None,
) -> str:
    """
    Single completion call. Pure black-box: send prompt, receive text.
    """
    key = api_key or os.environ.get("OPENROUTER_API_KEY")
    if not key:
        raise ValueError("OPENROUTER_API_KEY not set")

    url = f"{base_url.rstrip('/')}/chat/completions"
    payload = {
        "model": model_name,
        "messages": [{"role": "user", "content": prompt}],
        "max_tokens": 1024,
    }
    headers = {
        "Authorization": f"Bearer {key}",
        "Content-Type": "application/json",
        "HTTP-Referer": "https://safety-wrappers-research.local",
    }

    async with httpx.AsyncClient(timeout=60.0) as client:
        resp = await client.post(url, json=payload, headers=headers)
        resp.raise_for_status()
        data = resp.json()

    choices = data.get("choices", [])
    if not choices:
        return ""
    content = choices[0].get("message", {}).get("content", "")
    return content if isinstance(content, str) else str(content)
