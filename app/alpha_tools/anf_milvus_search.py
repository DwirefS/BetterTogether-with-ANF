import os
import logging
from pymilvus import Collection, connections
from .nim_client import NIMClient

logger = logging.getLogger(__name__)

# Toggle reranking via environment variable. When enabled, the pipeline over-fetches
# candidates from Milvus, then uses NV-RerankQA-Mistral-4B-v3 to rescore and return
# only the most relevant results. This improves retrieval precision by 15-25%.
RERANK_ENABLED = os.getenv("RERANK_ENABLED", "true").lower() in ("true", "1", "yes")

# Over-fetch multiplier: retrieve N × top_k candidates from Milvus, then let the
# cross-encoder reranker distill down to the best top_k. Higher values give the
# reranker more candidates to evaluate but increase latency.
RERANK_OVERFETCH_FACTOR = int(os.getenv("RERANK_OVERFETCH_FACTOR", "3"))


def anf_milvus_search(query: str, top_k: int = 5) -> str:
    """
    Semantic search against SEC filings stored in Milvus on Azure NetApp Files.

    Pipeline:
      1. Embed query via NV-EmbedQA-E5-v5 NIM
      2. ANN search in Milvus (IVF_FLAT, COSINE) — over-fetches if reranking is on
      3. [Optional] Rescore with NV-RerankQA-Mistral-4B-v3 NIM cross-encoder
      4. Return top_k most relevant passages

    Args:
        query: The question or risk factor to search for in the filings.
        top_k: Number of relevant chunks to retrieve.
    """
    logger.info(f"Connecting to Milvus vector DB for RAG retrieval: '{query}'")
    milvus_host = os.getenv("MILVUS_HOST", "localhost")
    milvus_port = int(os.getenv("MILVUS_PORT", "19530"))

    try:
        connections.connect("default", host=milvus_host, port=milvus_port)
        collection = Collection("sec_filings")
        collection.load()

        # Step 1: Embed the query using NV-EmbedQA-E5-v5
        nim = NIMClient()
        query_vector = nim.get_embeddings([query])[0]

        # Step 2: ANN search in Milvus
        # Over-fetch when reranking is enabled so the cross-encoder has more
        # candidates to evaluate, then we trim back to top_k.
        fetch_limit = top_k * RERANK_OVERFETCH_FACTOR if RERANK_ENABLED else top_k

        # [COST OPTIMIZATION] IVF_FLAT uses "nprobe" (not "ef" which is for HNSW/GPU_CAGRA)
        search_params = {"metric_type": "COSINE", "params": {"nprobe": 16}}
        results = collection.search(
            data=[query_vector],
            anns_field="vector",
            param=search_params,
            limit=fetch_limit,
            output_fields=["text", "source"],
        )

        # Collect raw hits
        raw_hits = []
        for hit in results[0]:
            raw_hits.append({
                "text": hit.entity.get("text", ""),
                "source": hit.entity.get("source", "Unknown file on ANF"),
                "milvus_score": hit.score,
            })

        if not raw_hits:
            return "No relevant context found in corporate filings."

        # Step 3: Rerank with NV-RerankQA-Mistral-4B-v3 (cross-encoder)
        if RERANK_ENABLED and len(raw_hits) > 1:
            logger.info(
                f"Reranking {len(raw_hits)} candidates with NV-RerankQA-Mistral-4B-v3"
            )
            passages = [h["text"] for h in raw_hits]
            rankings = nim.rerank(query, passages)

            # Reorder hits by reranker relevance score, keep only top_k
            reranked_hits = []
            for rank_entry in rankings[:top_k]:
                idx = rank_entry["index"]
                if idx < len(raw_hits):
                    hit = raw_hits[idx].copy()
                    hit["rerank_score"] = rank_entry.get("logit", 0.0)
                    reranked_hits.append(hit)

            final_hits = reranked_hits
            logger.info(
                f"Reranking complete: top rerank_score={final_hits[0].get('rerank_score', 'N/A') if final_hits else 'N/A'}"
            )
        else:
            # Embedding-only mode: use Milvus cosine similarity ordering
            final_hits = raw_hits[:top_k]

        # Step 4: Format output
        context_chunks = []
        for i, hit in enumerate(final_hits):
            source = hit["source"]
            text = hit["text"]
            context_chunks.append(f"[Chunk {i + 1} from {source}]:\n{text}")

        return "\n\n".join(context_chunks)

    except Exception as e:
        logger.error(f"Milvus search failed: {e}")
        return f"Error retrieving data from Milvus vector DB: {e}"
