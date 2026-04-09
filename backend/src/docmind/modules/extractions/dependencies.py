"""DI factory functions for extractions module — used via FastAPI Depends()."""

from .usecases import ExtractionProcessUseCase, ExtractionResultsUseCase


def get_extraction_process_usecase() -> ExtractionProcessUseCase:
    return ExtractionProcessUseCase()


def get_extraction_results_usecase() -> ExtractionResultsUseCase:
    return ExtractionResultsUseCase()
