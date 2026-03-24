"""
docmind/library/pipeline/__init__.py

Re-exports for convenient access to pipeline entry points.
"""

from .extraction import run_extraction_pipeline

# Backward compat alias
run_processing_pipeline = run_extraction_pipeline

__all__ = ["run_extraction_pipeline", "run_processing_pipeline"]
