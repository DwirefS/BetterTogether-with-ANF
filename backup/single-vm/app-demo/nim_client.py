"""
AlphaAgent — NVIDIA NIM Client
Thin wrapper for NIM OpenAI-compatible API (chat + embeddings).
"""

from __future__ import annotations

import time
from typing import Any, Dict, List, Optional

import requests


class NIMError(RuntimeError):
    """Raised when a NIM API call fails."""
    pass


def _post_json(url: str, payload: Dict[str, Any], timeout_s: int = 180) -> Dict[str, Any]:
    """POST JSON to a NIM endpoint and return the parsed response."""
    r = requests.post(url, json=payload, timeout=timeout_s)
    if r.status_code >= 400:
        raise NIMError(f"HTTP {r.status_code} from {url}: {r.text[:500]}")
    return r.json()


def wait_for_nim(base_url: str, kind: str, timeout_s: int = 900) -> None:
    """
    Block until a NIM service is healthy.
    NIM images can take several minutes to download/optimize on first run.
    We probe /v1/models until it responds.
    """
    deadline = time.time() + timeout_s
    url = f"{base_url.rstrip('/')}/v1/models"
    last_err: Optional[str] = None

    while time.time() < deadline:
        try:
            r = requests.get(url, timeout=10)
            if r.status_code < 400:
                print(f"  ✅ {kind} NIM ready at {base_url}")
                return
            last_err = f"HTTP {r.status_code}"
        except Exception as e:
            last_err = str(e)
        time.sleep(5)

    raise NIMError(f"Timed out waiting for {kind} NIM at {base_url} (last error: {last_err})")


def embed_texts(
    embed_base_url: str,
    model: str,
    texts: List[str],
    input_type: str = "passage",
) -> List[List[float]]:
    """Generate embeddings for a list of texts using a NIM embedding model."""
    url = f"{embed_base_url.rstrip('/')}/v1/embeddings"
    payload = {"model": model, "input": texts, "input_type": input_type}
    out = _post_json(url, payload, timeout_s=120)

    if "data" not in out:
        raise NIMError(f"Unexpected embeddings response: {list(out.keys())}")

    return [item["embedding"] for item in out["data"]]


def chat_completion(
    llm_base_url: str,
    model: str,
    messages: List[Dict[str, str]],
    max_tokens: int = 1024,
    temperature: float = 0.15,
) -> str:
    """Generate a chat completion using a NIM LLM."""
    url = f"{llm_base_url.rstrip('/')}/v1/chat/completions"
    payload = {
        "model": model,
        "messages": messages,
        "max_tokens": max_tokens,
        "temperature": temperature,
    }
    out = _post_json(url, payload, timeout_s=180)

    try:
        return out["choices"][0]["message"]["content"]
    except (KeyError, IndexError):
        raise NIMError(f"Unexpected chat response structure: {list(out.keys())}")
