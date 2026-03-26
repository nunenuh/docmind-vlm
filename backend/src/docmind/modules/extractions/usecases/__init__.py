"""Extraction usecases — split by SRP."""

from .process import ExtractionProcessUseCase
from .results import ExtractionResultsUseCase


class ExtractionUseCase:
    """Facade that wraps both process and results usecases.

    Kept for test backward-compat. New code should use the split classes.
    """

    def __init__(
        self,
        repo=None,
        pipeline_service=None,
        classification_service=None,
        confidence_service=None,
    ) -> None:
        self._process = ExtractionProcessUseCase(
            pipeline_service=pipeline_service,
            classification_service=classification_service,
        )
        self._results = ExtractionResultsUseCase(
            repo=repo,
            confidence_service=confidence_service,
        )

    @property
    def repo(self):
        return self._results.repo

    @repo.setter
    def repo(self, value):
        self._results.repo = value

    @property
    def confidence_service(self):
        return self._results.confidence_service

    @confidence_service.setter
    def confidence_service(self, value):
        self._results.confidence_service = value

    @property
    def pipeline_service(self):
        return self._process.pipeline_service

    @pipeline_service.setter
    def pipeline_service(self, value):
        self._process.pipeline_service = value

    @property
    def classification_service(self):
        return self._process.classification_service

    @classification_service.setter
    def classification_service(self, value):
        self._process.classification_service = value

    @property
    def doc_repo(self):
        return self._process.doc_repo

    @doc_repo.setter
    def doc_repo(self, value):
        self._process.doc_repo = value

    @property
    def storage_service(self):
        return self._process.storage_service

    @storage_service.setter
    def storage_service(self, value):
        self._process.storage_service = value

    @property
    def template_repo(self):
        return self._process.template_repo

    @template_repo.setter
    def template_repo(self, value):
        self._process.template_repo = value

    def trigger_processing(self, document_id, user_id, template_type=None):
        return self._process.trigger_processing(document_id, user_id, template_type)

    async def classify_document(self, document_id, user_id):
        return await self._process.classify_document(document_id, user_id)

    def _processing_stream(self, document_id, user_id, template_type):
        return self._process._processing_stream(document_id, user_id, template_type)

    async def get_extraction(self, document_id):
        return await self._results.get_extraction(document_id)

    async def get_audit_trail(self, document_id):
        return await self._results.get_audit_trail(document_id)

    async def get_overlay_data(self, document_id):
        return await self._results.get_overlay_data(document_id)

    async def get_comparison(self, document_id):
        return await self._results.get_comparison(document_id)


__all__ = [
    "ExtractionProcessUseCase",
    "ExtractionResultsUseCase",
    "ExtractionUseCase",
]
