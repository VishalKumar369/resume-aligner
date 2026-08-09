"""Add resume label, content hash, and extraction metadata

Revision ID: a1c4e7d92b30
Revises: 92f9b5ffe7fc
Create Date: 2026-08-09 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a1c4e7d92b30'
down_revision: Union[str, None] = '92f9b5ffe7fc'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('resumes', sa.Column('label', sa.String(), nullable=True))
    op.add_column('resumes', sa.Column('content_hash', sa.String(), nullable=True))
    op.add_column('resumes', sa.Column('extraction_meta', sa.JSON(), nullable=True))
    op.create_index(op.f('ix_resumes_content_hash'), 'resumes', ['content_hash'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_resumes_content_hash'), table_name='resumes')
    op.drop_column('resumes', 'extraction_meta')
    op.drop_column('resumes', 'content_hash')
    op.drop_column('resumes', 'label')
