"""
docmind/dbase/supabase/storage.py

File upload/download/signed-URL helpers using Supabase Storage.
"""
from docmind.core.logging import get_logger
from docmind.dbase.supabase.client import get_supabase_client

logger = get_logger(__name__)

BUCKET_NAME = "documents"


def get_file_bytes(storage_path: str) -> bytes:
    """Download file bytes from Supabase storage."""
    client = get_supabase_client()
    return client.storage.from_(BUCKET_NAME).download(storage_path)


def delete_file(storage_path: str) -> None:
    """Delete a file from Supabase storage."""
    client = get_supabase_client()
    client.storage.from_(BUCKET_NAME).remove([storage_path])


def get_signed_url(storage_path: str, expires_in: int = 3600) -> str:
    """Generate a signed URL for file download."""
    client = get_supabase_client()
    result = client.storage.from_(BUCKET_NAME).create_signed_url(
        storage_path, expires_in
    )
    return result["signedURL"]
