"""
Unit tests for the processing pipeline graph wiring:
should_continue, build_processing_graph, run_processing_pipeline.

Individual nodes are mocked — these tests verify graph structure
and flow control (normal flow + error short-circuit).
"""
from unittest.mock import patch


class TestShouldContinue:
    """Tests for the should_continue conditional edge function."""

    def test_returns_continue_when_no_error(self):
        from docmind.library.pipeline.extraction.pipeline import _should_continue as should_continue

        state = {"status": "processing"}
        assert should_continue(state) == "continue"

    def test_returns_end_when_error(self):
        from docmind.library.pipeline.extraction.pipeline import _should_continue as should_continue

        state = {"status": "error"}
        assert should_continue(state) == "end"

    def test_returns_continue_when_status_missing(self):
        from docmind.library.pipeline.extraction.pipeline import _should_continue as should_continue

        state = {}
        assert should_continue(state) == "continue"

    def test_returns_continue_when_status_ready(self):
        from docmind.library.pipeline.extraction.pipeline import _should_continue as should_continue

        state = {"status": "ready"}
        assert should_continue(state) == "continue"


class TestBuildProcessingGraph:
    """Tests for build_processing_graph structure."""

    def test_graph_compiles_without_error(self):
        from docmind.library.pipeline.extraction.pipeline import build_extraction_graph as build_processing_graph

        graph = build_processing_graph()
        assert graph is not None

    def test_graph_is_invocable(self):
        """The compiled graph has an invoke method."""
        from docmind.library.pipeline.extraction.pipeline import build_extraction_graph as build_processing_graph

        graph = build_processing_graph()
        assert hasattr(graph, "invoke")


class TestRunProcessingPipeline:
    """Tests for run_processing_pipeline entry point."""

    @patch("docmind.library.pipeline.extraction.pipeline._extraction_graph")
    def test_invokes_graph_with_initial_state(self, mock_graph):
        from docmind.library.pipeline.extraction.pipeline import run_extraction_pipeline as run_processing_pipeline

        initial_state = {"document_id": "test", "status": "processing"}
        mock_graph.invoke.return_value = {"status": "ready", "extraction_id": "ext-123"}

        result = run_processing_pipeline(initial_state)

        mock_graph.invoke.assert_called_once_with(initial_state)
        assert result["status"] == "ready"

    @patch("docmind.library.pipeline.extraction.pipeline._extraction_graph")
    def test_returns_graph_result(self, mock_graph):
        from docmind.library.pipeline.extraction.pipeline import run_extraction_pipeline as run_processing_pipeline

        expected = {"status": "ready", "extraction_id": "ext-456"}
        mock_graph.invoke.return_value = expected

        result = run_processing_pipeline({})
        assert result == expected
