"""add project, persona, conversation, and page_chunk tables

Revision ID: 0381657a47c7
Revises: 46b462437e09
Create Date: 2026-03-20 21:04:10.974073

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '0381657a47c7'
down_revision: Union[str, None] = '46b462437e09'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # --- personas (must exist before projects due to FK) ---
    op.create_table(
        'personas',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('user_id', sa.String(length=36), nullable=True),
        sa.Column('name', sa.String(length=100), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('system_prompt', sa.Text(), nullable=False),
        sa.Column('tone', sa.String(length=50), nullable=False, server_default='professional'),
        sa.Column('rules', sa.Text(), nullable=True),
        sa.Column('boundaries', sa.Text(), nullable=True),
        sa.Column('is_preset', sa.Boolean(), nullable=False, server_default=sa.text('false')),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_personas_user_id'), 'personas', ['user_id'], unique=False)

    # --- projects ---
    op.create_table(
        'projects',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('user_id', sa.String(length=36), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('persona_id', sa.String(length=36), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['persona_id'], ['personas.id']),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_projects_user_id'), 'projects', ['user_id'], unique=False)

    # --- project_conversations ---
    op.create_table(
        'project_conversations',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('project_id', sa.String(length=36), nullable=False),
        sa.Column('user_id', sa.String(length=36), nullable=False),
        sa.Column('title', sa.String(length=255), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['project_id'], ['projects.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_project_conversations_project_id'), 'project_conversations', ['project_id'], unique=False)
    op.create_index(op.f('ix_project_conversations_user_id'), 'project_conversations', ['user_id'], unique=False)

    # --- project_messages ---
    op.create_table(
        'project_messages',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('conversation_id', sa.String(length=36), nullable=False),
        sa.Column('role', sa.String(length=20), nullable=False),
        sa.Column('content', sa.Text(), nullable=False),
        sa.Column('citations', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['conversation_id'], ['project_conversations.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_project_messages_conversation_id'), 'project_messages', ['conversation_id'], unique=False)

    # --- page_chunks ---
    op.create_table(
        'page_chunks',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('document_id', sa.String(length=36), nullable=False),
        sa.Column('project_id', sa.String(length=36), nullable=False),
        sa.Column('page_number', sa.Integer(), nullable=False),
        sa.Column('chunk_index', sa.Integer(), nullable=False),
        sa.Column('content', sa.Text(), nullable=False),
        sa.Column('embedding', sa.Text(), nullable=True),
        sa.Column('metadata_json', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['document_id'], ['documents.id']),
        sa.ForeignKeyConstraint(['project_id'], ['projects.id']),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_page_chunks_document_id'), 'page_chunks', ['document_id'], unique=False)
    op.create_index(op.f('ix_page_chunks_project_id'), 'page_chunks', ['project_id'], unique=False)

    # --- add project_id FK column to documents ---
    op.add_column(
        'documents',
        sa.Column('project_id', sa.String(length=36), nullable=True),
    )
    op.create_index(op.f('ix_documents_project_id'), 'documents', ['project_id'], unique=False)
    op.create_foreign_key(
        'fk_documents_project_id',
        'documents',
        'projects',
        ['project_id'],
        ['id'],
    )


def downgrade() -> None:
    # --- remove project_id from documents ---
    op.drop_constraint('fk_documents_project_id', 'documents', type_='foreignkey')
    op.drop_index(op.f('ix_documents_project_id'), table_name='documents')
    op.drop_column('documents', 'project_id')

    # --- drop tables in reverse dependency order ---
    op.drop_index(op.f('ix_page_chunks_project_id'), table_name='page_chunks')
    op.drop_index(op.f('ix_page_chunks_document_id'), table_name='page_chunks')
    op.drop_table('page_chunks')

    op.drop_index(op.f('ix_project_messages_conversation_id'), table_name='project_messages')
    op.drop_table('project_messages')

    op.drop_index(op.f('ix_project_conversations_user_id'), table_name='project_conversations')
    op.drop_index(op.f('ix_project_conversations_project_id'), table_name='project_conversations')
    op.drop_table('project_conversations')

    op.drop_index(op.f('ix_projects_user_id'), table_name='projects')
    op.drop_table('projects')

    op.drop_index(op.f('ix_personas_user_id'), table_name='personas')
    op.drop_table('personas')
