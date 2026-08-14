"""Add the LLM result cache and a JD content hash

Free-tier model quotas are metered per day, so repeating a call for input
already seen is expensive. Both changes exist to avoid spending the budget
twice on the same text.

Revision ID: c3a9e5b71f42
Revises: b7d2f1a4c803
Create Date: 2026-08-13 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'c3a9e5b71f42'
down_revision: Union[str, None] = 'b7d2f1a4c803'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('job_descriptions', sa.Column('content_hash', sa.String(), nullable=True))
    op.create_index(op.f('ix_job_descriptions_content_hash'), 'job_descriptions', ['content_hash'], unique=False)

    op.create_table(
        'llm_cache',
        sa.Column('cache_key', sa.String(), nullable=False),
        sa.Column('feature', sa.String(), nullable=False),
        sa.Column('payload', sa.JSON(), nullable=False),
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.Column('is_deleted', sa.Boolean(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_llm_cache_id'), 'llm_cache', ['id'], unique=False)
    op.create_index(op.f('ix_llm_cache_created_at'), 'llm_cache', ['created_at'], unique=False)
    op.create_index(op.f('ix_llm_cache_is_deleted'), 'llm_cache', ['is_deleted'], unique=False)
    op.create_index(op.f('ix_llm_cache_feature'), 'llm_cache', ['feature'], unique=False)
    op.create_index(op.f('ix_llm_cache_cache_key'), 'llm_cache', ['cache_key'], unique=True)


def downgrade() -> None:
    op.drop_table('llm_cache')
    op.drop_index(op.f('ix_job_descriptions_content_hash'), table_name='job_descriptions')
    op.drop_column('job_descriptions', 'content_hash')
