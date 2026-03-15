"""
docmind/library/providers/__init__.py

Re-exports for convenient access to VLM provider types and factory.
"""
from .protocol import VLMProvider, VLMResponse
from .factory import get_vlm_provider
