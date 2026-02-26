"""
AlphaAgent — Configuration
Settings from environment variables with sensible defaults.
"""

from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass(frozen=True)
class Settings:
    # NVIDIA NIM endpoints
    llm_base_url: str
    embed_base_url: str

    # Model identifiers (must match NIM container)
    llm_model: str = "nvidia/llama-3.1-nemotron-nano-4b-v1.1"
    embed_model: str = "nvidia/llama-3.2-nv-embedqa-1b-v2"

    # Azure NetApp Files mount paths
    data_root: str = "/mnt/anf/data"
    index_root: str = "/mnt/anf/index"

    # ANF Object REST API (S3-compatible) — optional for demo
    anf_object_endpoint: str = ""
    anf_access_key: str = ""
    anf_secret_key: str = ""
    anf_bucket_name: str = "fsi-dropzone"

    # RAG tuning parameters
    chunk_chars: int = 1200
    chunk_overlap: int = 150
    top_k: int = 5

    # Agent parameters
    max_agent_steps: int = 5
    llm_max_tokens: int = 1024
    llm_temperature: float = 0.15


def get_settings() -> Settings:
    """Load settings from environment variables."""
    return Settings(
        llm_base_url=os.environ.get("LLM_BASE_URL", "http://localhost:8000").rstrip("/"),
        embed_base_url=os.environ.get("EMBED_BASE_URL", "http://localhost:8001").rstrip("/"),
        data_root=os.environ.get("DATA_ROOT", "/mnt/anf/data"),
        index_root=os.environ.get("INDEX_ROOT", "/mnt/anf/index"),
        anf_object_endpoint=os.environ.get("ANF_OBJECT_REST_ENDPOINT", ""),
        anf_access_key=os.environ.get("ANF_ACCESS_KEY", ""),
        anf_secret_key=os.environ.get("ANF_SECRET_KEY", ""),
        anf_bucket_name=os.environ.get("ANF_BUCKET_NAME", "fsi-dropzone"),
    )
