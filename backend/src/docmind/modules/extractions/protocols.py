"""Protocols for the extractions module — structural contracts for DI."""

from __future__ import annotations

from typing import TYPE_CHECKING, AsyncGenerator, Protocol

if TYPE_CHECKING:
    from docmind.core.database import AuditEntry, ExtractedField, Extraction


class ExtractionRepositoryProtocol(Protocol):
    """Contract for extraction data persistence."""

    async def get_latest_extraction(
        self, document_id: str
    ) -> Extraction | None: ...

    async def get_fields(
        self, extraction_id: str
    ) -> list[ExtractedField]: ...

    async def get_audit_trail(
        self, extraction_id: str
    ) -> list[AuditEntry]: ...


class PipelineServiceProtocol(Protocol):
    """Contract for running the extraction pipeline."""

    async def run_pipeline(
        self,
        document_id: str,
        user_id: str,
        file_bytes: bytes,
        file_type: str,
        filename: str,
        template_config: dict | None = None,
    ) -> AsyncGenerator[str, None]: ...


class ClassificationServiceProtocol(Protocol):
    """Contract for document type classification."""

    async def classify(
        self,
        file_bytes: bytes,
        file_type: str,
    ) -> dict: ...


class ConfidenceServiceProtocol(Protocol):
    """Contract for confidence score analysis."""

    def calculate_overall_confidence(
        self, fields: list[ExtractedField]
    ) -> float: ...

    def get_low_confidence_fields(
        self, fields: list[ExtractedField], threshold: float = 0.7
    ) -> list[ExtractedField]: ...
