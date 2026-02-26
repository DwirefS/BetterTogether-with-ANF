import os
import logging
from pymilvus import Collection, connections
from .nim_client import NIMClient

logger = logging.getLogger(__name__)


def anf_milvus_search(query: str, top_k: int = 5) -> str:
    """
    Semantic search against SEC filings stored in Milvus on Azure NetApp Files.

    Args:
        query: The question or risk factor to search for in the filings.
        top_k: Number of relevant chunks to retrieve.
    """
    logger.info(f"Connecting to Milvus vector DB for RAG retrieval: '{query}'")
    milvus_host = os.getenv("MILVUS_HOST", "localhost")
    milvus_port = os.getenv("MILVUS_PORT", "19530")

    try:
        connections.connect("default", host=milvus_host, port=milvus_port)
        collection = Collection("sec_filings")
        collection.load()

        # Embed the query
        nim = NIMClient()
        query_vector = nim.get_embeddings([query])[0]

        # Search Milvus
        search_params = {"metric_type": "COSINE", "params": {"ef": 64}}
        results = collection.search(
            data=[query_vector],
            anns_field="vector",
            param=search_params,
            limit=top_k,
            output_fields=["text", "source"],
        )

        context_chunks = []
        for i, hit in enumerate(results[0]):
            text = hit.entity.get("text")
            source = hit.entity.get("source", "Unknown file on ANF")
            context_chunks.append(f"[Chunk {i + 1} from {source}]:\n{text}")

        combined = "\n\n".join(context_chunks)
        return (
            combined if combined else "No relevant context found in corporate filings."
        )

    except Exception as e:
        logger.error(f"Milvus search failed: {e}")
        return f"Error retrieving data from Milvus vector DB: {e}"
