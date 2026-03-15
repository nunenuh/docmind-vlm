"""
Shared test fixtures for DocMind-VLM backend tests.
"""
import pytest


@pytest.fixture
def sample_document_data() -> dict:
    """Sample document creation data."""
    return {
        "filename": "test_invoice.pdf",
        "file_type": "pdf",
        "file_size": 1024,
        "storage_path": "test-user/test-doc/test_invoice.pdf",
    }


@pytest.fixture
def mock_user() -> dict:
    """Mock authenticated user payload."""
    return {
        "id": "test-user-id",
        "email": "test@example.com",
    }
