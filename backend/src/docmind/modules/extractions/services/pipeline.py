"""Extraction pipeline service — runs the LangGraph extraction pipeline."""

from docmind.library.pipeline.extraction import run_extraction_pipeline


class ExtractionPipelineService:
    """Runs the LangGraph extraction pipeline (preprocess → extract → postprocess → store).

    This is a blocking call — should be run in a thread from async context.
    """

    def run_pipeline(self, initial_state: dict) -> dict:
        """Run the full processing pipeline.

        Args:
            initial_state: Pipeline state dict with file_bytes, template_type, etc.

        Returns:
            Pipeline result dict with extraction_id, status, etc.
        """
        return run_extraction_pipeline(initial_state)
