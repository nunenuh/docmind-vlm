"""Document extraction pipeline.

Nodes: preprocess → extract → postprocess → store.
"""

from .pipeline import run_extraction_pipeline

__all__ = ["run_extraction_pipeline"]
