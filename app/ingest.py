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
import boto3
from botocore.config import Config

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Config
DATA_DIR = os.getenv("ANF_MOUNT_PATH", "/mnt/anf/data")
MILVUS_HOST = os.getenv("MILVUS_HOST", "localhost")
MILVUS_PORT = os.getenv("MILVUS_PORT", "19530")
COLLECTION_NAME = "sec_filings"

# ANF Object REST API Config (Optional S3 duality)
ANF_OBJECT_REST_ENDPOINT = os.getenv("ANF_OBJECT_REST_ENDPOINT")
ANF_ACCESS_KEY = os.getenv("ANF_ACCESS_KEY")
ANF_SECRET_KEY = os.getenv("ANF_SECRET_KEY")
ANF_BUCKET_NAME = os.getenv("ANF_BUCKET_NAME", "fsi-dropzone")


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

    # Create Index leveraging NVIDIA cuVS (RAPIDS) GPU acceleration
    index_params = {
        "metric_type": "COSINE",
        "index_type": "GPU_CAGRA",  # Using NVIDIA cuVS algorithm over standard CPU HNSW
        "params": {"intermediate_graph_degree": 64, "graph_degree": 32},
    }
    collection.create_index(field_name="vector", index_params=index_params)
    return collection


def ingest_documents(collection):
    pdf_files = []

    # 1. Try ANF Object REST API (S3) first for zero data movement
    if ANF_OBJECT_REST_ENDPOINT and ANF_ACCESS_KEY and ANF_SECRET_KEY:
        logger.info(f"Connecting to ANF Object REST API at {ANF_OBJECT_REST_ENDPOINT}")
        s3 = boto3.client(
            "s3",
            endpoint_url=ANF_OBJECT_REST_ENDPOINT,
            aws_access_key_id=ANF_ACCESS_KEY,
            aws_secret_access_key=ANF_SECRET_KEY,
            config=Config(signature_version="s3v4"),
        )
        try:
            objects = s3.list_objects_v2(Bucket=ANF_BUCKET_NAME)
            for obj in objects.get("Contents", []):
                if obj["Key"].endswith(".pdf"):
                    # Download temporarily to the pod for NIM processing
                    temp_path = f"/tmp/{os.path.basename(obj['Key'])}"
                    s3.download_file(ANF_BUCKET_NAME, obj["Key"], temp_path)
                    pdf_files.append(temp_path)
                    logger.info(f"Retrieved {obj['Key']} via ANF Object REST API.")
        except Exception as e:
            logger.error(
                f"Failed to read from ANF Object REST API: {e}. Falling back to POSIX mount."
            )

    # 2. Fall back to standard POSIX NFS mount if S3 is not configured
    if not pdf_files:
        logger.info(f"Scanning ANF NFS mount directory: {DATA_DIR}")
        pdf_files = glob.glob(os.path.join(DATA_DIR, "**", "*.pdf"), recursive=True)

    if not pdf_files:
        logger.warning(
            f"No PDF files found via REST or in {DATA_DIR}. Run load-data.sh first."
        )
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
