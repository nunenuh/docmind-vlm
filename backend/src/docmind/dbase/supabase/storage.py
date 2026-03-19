"""
docmind/dbase/supabase/storage.py

File upload/download/signed-URL helpers using Supabase Storage.
"""

from docmind.core.config import get_settings
from docmind.core.logging import get_logger
from docmind.dbase.supabase.client import get_supabase_client

logger = get_logger(__name__)


def _get_bucket_name() -> str:
    return get_settings().STORAGE_BUCKET


def get_file_bytes(storage_path: str) -> bytes:
    """Download file bytes from Supabase storage."""
    client = get_supabase_client()
    return client.storage.from_(_get_bucket_name()).download(storage_path)


def delete_file(storage_path: str) -> None:
    """Delete a file from Supabase storage."""
    client = get_supabase_client()
    client.storage.from_(_get_bucket_name()).remove([storage_path])


def upload_file(storage_path: str, file_bytes: bytes, content_type: str) -> None:
    """Upload file bytes to Supabase storage."""
    client = get_supabase_client()
    client.storage.from_(_get_bucket_name()).upload(
        storage_path, file_bytes, {"content-type": content_type}
    )


def get_signed_url(storage_path: str, expires_in: int = 3600) -> str:
    """Generate a signed URL for file download."""
    client = get_supabase_client()
    result = client.storage.from_(_get_bucket_name()).create_signed_url(
        storage_path, expires_in
    )
    return result["signedURL"]
