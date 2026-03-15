"""
docmind/dbase/sqlalchemy/base.py

SQLAlchemy declarative base. All ORM models inherit from Base.
"""
from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    pass
