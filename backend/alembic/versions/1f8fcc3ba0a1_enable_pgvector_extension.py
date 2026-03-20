"""enable pgvector extension

Revision ID: 1f8fcc3ba0a1
Revises: 0381657a47c7
Create Date: 2026-03-20 21:15:07.202568

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '1f8fcc3ba0a1'
down_revision: Union[str, None] = '0381657a47c7'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")


def downgrade() -> None:
    op.execute("DROP EXTENSION IF EXISTS vector")
