"""
docmind/library/pipeline/__init__.py

Re-exports for convenient access to pipeline entry points.
"""

from .chat import run_chat_pipeline
from .processing import run_processing_pipeline

__all__ = ["run_chat_pipeline", "run_processing_pipeline"]
