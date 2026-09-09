"""Add feedback table

Backs the product Feedback form on the landing page (anonymous) and in Settings
(attributed to the signed-in account): an optional 1-5 rating plus a message.

Revision ID: f1c7d9a02e63
Revises: e7b2c4a91d55
Create Date: 2026-09-09 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'f1c7d9a02e63'
down_revision: Union[str, None] = 'e7b2c4a91d55'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'feedback',
        sa.Column('owner_id', sa.UUID(), nullable=True),
        sa.Column('rating', sa.Integer(), nullable=True),
        sa.Column('message', sa.String(), nullable=False),
        sa.Column('email', sa.String(), nullable=True),
        sa.Column('source', sa.String(), nullable=True),
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.Column('is_deleted', sa.Boolean(), nullable=True),
        sa.ForeignKeyConstraint(['owner_id'], ['users.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_feedback_id'), 'feedback', ['id'], unique=False)
    op.create_index(op.f('ix_feedback_owner_id'), 'feedback', ['owner_id'], unique=False)
    op.create_index(op.f('ix_feedback_created_at'), 'feedback', ['created_at'], unique=False)
    op.create_index(op.f('ix_feedback_is_deleted'), 'feedback', ['is_deleted'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_feedback_is_deleted'), table_name='feedback')
    op.drop_index(op.f('ix_feedback_created_at'), table_name='feedback')
    op.drop_index(op.f('ix_feedback_owner_id'), table_name='feedback')
    op.drop_index(op.f('ix_feedback_id'), table_name='feedback')
    op.drop_table('feedback')
