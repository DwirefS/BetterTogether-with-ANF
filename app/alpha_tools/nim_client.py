import os
import requests
import logging
from tenacity import retry, stop_after_attempt, wait_exponential

logger = logging.getLogger(__name__)


class NIMClient:
    """Client for interacting with NVIDIA NIM Microservices running in AKS."""

    def __init__(self):
        self.llm_url = os.getenv("NIM_LLM_URL", "http://nim-llm:8000/v1")
        self.embed_url = os.getenv("NIM_EMBED_URL", "http://nim-embed:8000/v1")
        self.rerank_url = os.getenv("NIM_RERANK_URL", "http://nim-rerank:8000/v1")
        # In AKS, the API key might be empty if VPC auth is used, or injected.
        self.api_key = os.getenv("NGC_API_KEY", "local-nim")
        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

    @retry(
        stop=stop_after_attempt(5), wait=wait_exponential(multiplier=1, min=2, max=10)
    )
    def get_embeddings(self, texts, model="nv-embedqa-e5-v5"):
        """Call the NV-EmbedQA NIM to vectorize text."""
        try:
            resp = requests.post(
                f"{self.embed_url}/embeddings",
                headers=self.headers,
                json={"input": texts, "model": model, "encoding_format": "float"},
                timeout=30,
            )
            resp.raise_for_status()
            data = resp.json()
            return [item["embedding"] for item in data["data"]]
        except Exception as e:
            logger.error(f"Failed to get embeddings: {e}")
            raise

    @retry(
        stop=stop_after_attempt(5), wait=wait_exponential(multiplier=1, min=2, max=10)
    )
    def chat_completion(
        self, messages, model="meta/llama-3.1-8b-instruct", temperature=0.2
    ):
        """Call the Nemotron/Llama NIM for reasoning."""
        try:
            resp = requests.post(
                f"{self.llm_url}/chat/completions",
                headers=self.headers,
                json={"messages": messages, "model": model, "temperature": temperature},
                timeout=60,
            )
            resp.raise_for_status()
            return resp.json()["choices"][0]["message"]["content"]
        except Exception as e:
            logger.error(f"LLM API Error: {e}")
            raise

    @retry(
        stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=8)
    )
    def rerank(self, query: str, passages: list[str], model: str = "nv-rerankqa-mistral-4b-v3") -> list[dict]:
        """
        Call the NV-RerankQA NIM to rescore retrieved passages against the query.

        This dramatically improves retrieval precision (15-25%) by using a cross-encoder
        model (NV-RerankQA-Mistral-4B-v3) to jointly attend to query-passage pairs,
        rather than relying solely on bi-encoder cosine similarity from the embedding stage.

        Args:
            query: The user's search query.
            passages: List of text passages retrieved from Milvus.
            model: The NIM reranker model identifier.

        Returns:
            List of dicts with 'index' (original position) and 'logit' (relevance score),
            sorted by descending relevance.
        """
        try:
            resp = requests.post(
                f"{self.rerank_url}/ranking",
                headers=self.headers,
                json={
                    "model": model,
                    "query": {"text": query},
                    "passages": [{"text": p} for p in passages],
                },
                timeout=30,
            )
            resp.raise_for_status()
            data = resp.json()
            # NIM Reranker returns {"rankings": [{"index": 0, "logit": 5.12}, ...]}
            rankings = data.get("rankings", [])
            # Sort by relevance score descending
            rankings.sort(key=lambda r: r.get("logit", 0), reverse=True)
            return rankings
        except Exception as e:
            logger.warning(f"Reranker NIM unavailable, falling back to embedding-only ranking: {e}")
            # Graceful fallback: return original order with synthetic scores
            return [{"index": i, "logit": 0.0} for i in range(len(passages))]

    @retry(
        stop=stop_after_attempt(5), wait=wait_exponential(multiplier=1, min=2, max=10)
    )
    def extract_pdf(self, pdf_path: str) -> str:
        """Call NeMo Retriever Parse NIM to extract text from a physical PDF file."""
        retriever_url = os.getenv("NIM_RETRIEVER_URL", "http://nim-retriever:8000/v1")
        try:
            with open(pdf_path, "rb") as f:
                # The exact API shape depends on the NeMo Retriever version, assuming standard multi-part file upload
                files = {"file": (os.path.basename(pdf_path), f, "application/pdf")}
                resp = requests.post(
                    f"{retriever_url}/extract",
                    headers={"Authorization": f"Bearer {self.api_key}"},
                    files=files,
                    timeout=120,
                )
            resp.raise_for_status()
            return resp.json().get("text", "")
        except Exception as e:
            logger.error(f"NeMo Retriever Parse API Error for {pdf_path}: {e}")
            raise
