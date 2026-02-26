"""
AlphaAgent — Skill: ANF Data Reader
Reads documents from Azure NetApp Files.
Supports both direct NFS file access (primary) and Object REST API via boto3 (S3-compatible).

This skill proves the "File/Object Duality" narrative:
  - Legacy systems write data to ANF via NFS/SMB
  - AI agents read the exact same data via S3-compatible Object REST API
  - Zero data movement, zero ETL
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Dict, List, Optional

import boto3
from botocore.config import Config as BotoConfig
from botocore.exceptions import ClientError, NoCredentialsError


def list_anf_files(data_root: str, extension: Optional[str] = None) -> List[Dict[str, str]]:
    """
    List files on the ANF NFS mount.

    Args:
        data_root: Path to the ANF data directory (e.g., /mnt/anf/data)
        extension: Optional filter by extension (e.g., ".pdf")

    Returns:
        List of dicts with 'name', 'path', 'size_kb', 'category'
    """
    root = Path(data_root)
    if not root.exists():
        return []

    files = []
    for p in sorted(root.rglob("*")):
        if not p.is_file():
            continue
        if extension and p.suffix.lower() != extension.lower():
            continue
        files.append({
            "name": p.name,
            "path": str(p),
            "size_kb": f"{p.stat().st_size / 1024:.1f}",
            "category": p.parent.name,
        })
    return files


def read_file_from_nfs(file_path: str) -> bytes:
    """
    Read a file directly from the ANF NFS mount.
    This is the primary access method — direct POSIX file read.
    """
    path = Path(file_path)
    if not path.exists():
        raise FileNotFoundError(f"File not found on ANF: {file_path}")
    return path.read_bytes()


def read_file_from_object_api(
    file_key: str,
    endpoint: Optional[str] = None,
    access_key: Optional[str] = None,
    secret_key: Optional[str] = None,
    bucket: Optional[str] = None,
) -> bytes:
    """
    Read a file from ANF via the Object REST API (S3-compatible).

    This demonstrates the "File/Object Duality" — the exact same file written
    by a legacy system via NFS/SMB can be read by AI agents via S3 APIs.

    Args:
        file_key: S3 object key (e.g., "research/ALPH_SellSide_Research_Note.pdf")
        endpoint: ANF Object REST API endpoint URL
        access_key: S3-compatible access key
        secret_key: S3-compatible secret key
        bucket: S3 bucket name mapped to the ANF volume

    Returns:
        File content as bytes
    """
    ep = endpoint or os.getenv("ANF_OBJECT_REST_ENDPOINT", "")
    ak = access_key or os.getenv("ANF_ACCESS_KEY", "")
    sk = secret_key or os.getenv("ANF_SECRET_KEY", "")
    bk = bucket or os.getenv("ANF_BUCKET_NAME", "fsi-dropzone")

    if not ep or not ak or not sk:
        raise ValueError(
            "ANF Object REST API not configured. "
            "Set ANF_OBJECT_REST_ENDPOINT, ANF_ACCESS_KEY, ANF_SECRET_KEY."
        )

    s3_client = boto3.client(
        "s3",
        endpoint_url=ep,
        aws_access_key_id=ak,
        aws_secret_access_key=sk,
        config=BotoConfig(
            signature_version="s3v4",
            s3={"addressing_style": "path"},
        ),
        verify=False,  # Internal VNet traffic
    )

    try:
        response = s3_client.get_object(Bucket=bk, Key=file_key)
        return response["Body"].read()
    except ClientError as e:
        raise FileNotFoundError(f"Failed to read {file_key} from ANF Object REST API: {e}")


def list_buckets_on_anf(
    endpoint: Optional[str] = None,
    access_key: Optional[str] = None,
    secret_key: Optional[str] = None,
) -> List[str]:
    """
    List S3 buckets available on the ANF Object REST API endpoint.
    Proves that the ANF volume is accessible as an S3-compatible store.
    """
    ep = endpoint or os.getenv("ANF_OBJECT_REST_ENDPOINT", "")
    ak = access_key or os.getenv("ANF_ACCESS_KEY", "")
    sk = secret_key or os.getenv("ANF_SECRET_KEY", "")

    if not ep or not ak or not sk:
        return ["(Object REST API not configured — using NFS direct access)"]

    try:
        s3_client = boto3.client(
            "s3",
            endpoint_url=ep,
            aws_access_key_id=ak,
            aws_secret_access_key=sk,
            config=BotoConfig(
                signature_version="s3v4",
                s3={"addressing_style": "path"},
            ),
            verify=False,
        )
        response = s3_client.list_buckets()
        return [b["Name"] for b in response.get("Buckets", [])]
    except (ClientError, NoCredentialsError, Exception) as e:
        return [f"(Error listing buckets: {e})"]


def read_document(
    file_path: str,
    data_root: str = "/mnt/anf/data",
) -> bytes:
    """
    Unified document reader — tries NFS first, falls back to Object REST API.
    This is the primary interface used by the agent.
    """
    # Primary: direct NFS read (fastest, always available)
    full_path = Path(data_root) / file_path if not Path(file_path).is_absolute() else Path(file_path)
    if full_path.exists():
        return full_path.read_bytes()

    # Fallback: try Object REST API
    anf_endpoint = os.getenv("ANF_OBJECT_REST_ENDPOINT", "")
    if anf_endpoint:
        try:
            return read_file_from_object_api(file_key=file_path)
        except Exception:
            pass

    raise FileNotFoundError(f"Document not found: {file_path}")
