"""PostgreSQL database layer for DocMind-VLM.

Architecture:
- dbase/psql/core/       → Engine, sessions (async), base model, init
- dbase/psql/models/     → Document, Extraction, ExtractedField, AuditEntry, ChatMessage, Citation
- dbase/psql/services/   → Migration runner
- dbase/psql/langgraph/  → LangGraph checkpoint storage (future)
"""

from .core.base import Base
from .core.engine import get_async_engine
from .core.init_db import init_db
from .core.session import AsyncSessionLocal, get_async_db_session

__all__ = [
    "Base",
    "get_async_engine",
    "init_db",
    "AsyncSessionLocal",
    "get_async_db_session",
]
