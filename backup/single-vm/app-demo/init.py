"""
AlphaAgent — Init Module
Entry point for the init container: generates synthetic data + builds embedding index.
Called by Docker Compose before the UI starts.
"""

from __future__ import annotations

import sys

from .config import get_settings
from .nim_client import wait_for_nim
from .data_gen import ensure_synthetic_dataset
from .indexer import build_index


def main():
    print("╔═════════════════════════════════════════════════════╗")
    print("║  AlphaAgent Init — Data Generation + Index Build   ║")
    print("╚═════════════════════════════════════════════════════╝")

    s = get_settings()

    # Step 1: Wait for NIM services to be healthy
    print("\n[1/3] Waiting for NVIDIA NIM services...")
    try:
        wait_for_nim(s.llm_base_url, "LLM", timeout_s=900)
        wait_for_nim(s.embed_base_url, "Embeddings", timeout_s=900)
    except Exception as e:
        print(f"  ❌ NIM not ready: {e}")
        print("  Hint: NIM containers may still be downloading model weights.")
        print("  Check: docker compose logs nim-llm nim-embed")
        sys.exit(1)

    # Step 2: Generate synthetic FSI dataset on ANF
    print("\n[2/3] Generating synthetic financial dataset on ANF...")
    ensure_synthetic_dataset(s.data_root)

    # Step 3: Build embedding index on ANF
    print("\n[3/3] Building embedding index on ANF...")
    build_index(
        data_root=s.data_root,
        index_root=s.index_root,
        embed_base_url=s.embed_base_url,
        embed_model=s.embed_model,
        chunk_chars=s.chunk_chars,
        chunk_overlap=s.chunk_overlap,
    )

    print("\n╔═════════════════════════════════════════════════════╗")
    print("║  ✅ Init complete! Data + index ready on ANF.      ║")
    print(f"║  Data: {s.data_root}")
    print(f"║  Index: {s.index_root}")
    print("╚═════════════════════════════════════════════════════╝")


if __name__ == "__main__":
    main()
