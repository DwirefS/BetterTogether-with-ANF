import os
import glob
import logging
from pymilvus import (
    connections,
    FieldSchema,
    CollectionSchema,
    DataType,
    Collection,
    utility,
)
from langchain_community.document_loaders import PyPDFLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from alpha_tools.nim_client import NIMClient

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Config
DATA_DIR = os.getenv("ANF_MOUNT_PATH", "/mnt/anf/data")
MILVUS_HOST = os.getenv("MILVUS_HOST", "localhost")
MILVUS_PORT = os.getenv("MILVUS_PORT", "19530")
COLLECTION_NAME = "sec_filings"


def setup_milvus():
    logger.info(f"Connecting to Milvus at {MILVUS_HOST}:{MILVUS_PORT} (Backed by ANF)")
    connections.connect("default", host=MILVUS_HOST, port=MILVUS_PORT)

    if utility.has_collection(COLLECTION_NAME):
        logger.info(
            f"Collection {COLLECTION_NAME} exists. Dropping for fresh ingest..."
        )
        utility.drop_collection(COLLECTION_NAME)

    fields = [
        FieldSchema(name="id", dtype=DataType.INT64, is_primary=True, auto_id=True),
        FieldSchema(
            name="vector", dtype=DataType.FLOAT_VECTOR, dim=1024
        ),  # NV-EmbedQA-E5-v5 is usually 1024 or 4096 depending on variant, assuming 1024 for standard E5
        FieldSchema(name="text", dtype=DataType.VARCHAR, max_length=65535),
        FieldSchema(name="source", dtype=DataType.VARCHAR, max_length=500),
    ]

    schema = CollectionSchema(fields, "SEC Filings extracted via NeMo Retriever")
    collection = Collection(COLLECTION_NAME, schema)

    # Create Index (assuming cuVS GPU acceleration if enabled in Helm)
    index_params = {
        "metric_type": "COSINE",
        "index_type": "HNSW",  # or "GPU_CAGRA" for cuVS
        "params": {"M": 8, "efConstruction": 64},
    }
    collection.create_index(field_name="vector", index_params=index_params)
    return collection


def ingest_documents(collection):
    pdf_files = glob.glob(os.path.join(DATA_DIR, "**", "*.pdf"), recursive=True)
    if not pdf_files:
        logger.warning(f"No PDF files found in {DATA_DIR}. Run load-data.sh first.")
        return

    nim_client = NIMClient()

    # Traditional extraction falls back to PyPDF if NeMo Retriever endpoint isn't up
    # In full enterprise, this calls NeMo Retriever NIM API for `nemo-retriever-parse`
    text_splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=100)

    for pdf_path in pdf_files:
        logger.info(f"Processing: {pdf_path}")

        try:
            logger.info("Calling NeMo Retriever Parse NIM...")
            raw_text = nim_client.extract_pdf(pdf_path)
            texts_to_embed = text_splitter.split_text(raw_text)
        except Exception as e:
            logger.warning(
                f"NeMo Retriever failed for {pdf_path}: {e}. Falling back to traditional PyPDFLoader."
            )
            loader = PyPDFLoader(pdf_path)
            docs = loader.load()
            chunks = text_splitter.split_documents(docs)
            texts_to_embed = [chunk.page_content for chunk in chunks]

        sources = [pdf_path for _ in texts_to_embed]

        # Batch Embed via NV-EmbedQA (1024 dim)
        embeddings = nim_client.get_embeddings(texts_to_embed)

        if embeddings:
            collection.insert([embeddings, texts_to_embed, sources])
            logger.info(
                f"Inserted {len(texts_to_embed)} chunks from {os.path.basename(pdf_path)} into Milvus."
            )

    collection.flush()
    logger.info(
        "Ingestion complete. Data persisted to Azure NetApp Files via Milvus PVC."
    )


if __name__ == "__main__":
    col = setup_milvus()
    ingest_documents(col)
