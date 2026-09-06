"""Add personal notes table

Backs the Personal → Notes planner: private, per-user notes for goals, plans, and
journal entries, optionally with a target date to work towards.

Revision ID: e7b2c4a91d55
Revises: d5f8a3c96b21
Create Date: 2026-09-06 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'e7b2c4a91d55'
down_revision: Union[str, None] = 'd5f8a3c96b21'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'notes',
        sa.Column('owner_id', sa.UUID(), nullable=False),
        sa.Column('title', sa.String(), nullable=False),
        sa.Column('content', sa.String(), nullable=False, server_default=''),
        sa.Column('category', sa.String(), nullable=False, server_default='Note'),
        sa.Column('color', sa.String(), nullable=False, server_default='primary'),
        sa.Column('target_date', sa.DateTime(), nullable=True),
        sa.Column('is_pinned', sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column('is_completed', sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.Column('is_deleted', sa.Boolean(), nullable=True),
        sa.ForeignKeyConstraint(['owner_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_notes_id'), 'notes', ['id'], unique=False)
    op.create_index(op.f('ix_notes_owner_id'), 'notes', ['owner_id'], unique=False)
    op.create_index(op.f('ix_notes_created_at'), 'notes', ['created_at'], unique=False)
    op.create_index(op.f('ix_notes_is_deleted'), 'notes', ['is_deleted'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_notes_is_deleted'), table_name='notes')
    op.drop_index(op.f('ix_notes_created_at'), table_name='notes')
    op.drop_index(op.f('ix_notes_owner_id'), table_name='notes')
    op.drop_index(op.f('ix_notes_id'), table_name='notes')
    op.drop_table('notes')
