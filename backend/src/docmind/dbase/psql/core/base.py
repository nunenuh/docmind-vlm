"""PostgreSQL Base Model.

Declarative base for all PostgreSQL ORM models.
Separate from Supabase client layer to maintain isolation.
"""

from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    """Base class for PostgreSQL models."""

    pass
