"""Add email verification

Adds users.email_verified (existing accounts backfilled as verified) and a
short-lived OTP table backing the optional signup email-verification flow.

Revision ID: a2b8e4c15d70
Revises: f1c7d9a02e63
Create Date: 2026-09-09 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a2b8e4c15d70'
down_revision: Union[str, None] = 'f1c7d9a02e63'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Existing accounts are treated as verified so enabling the flag never locks
    # anyone out; new signups set the value explicitly.
    op.add_column(
        'users',
        sa.Column('email_verified', sa.Boolean(), nullable=False, server_default=sa.true()),
    )

    op.create_table(
        'email_verification_codes',
        sa.Column('email', sa.String(), nullable=False),
        sa.Column('code_hash', sa.String(), nullable=False),
        sa.Column('expires_at', sa.DateTime(), nullable=False),
        sa.Column('attempts', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.Column('is_deleted', sa.Boolean(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_email_verification_codes_id'), 'email_verification_codes', ['id'], unique=False)
    op.create_index(op.f('ix_email_verification_codes_email'), 'email_verification_codes', ['email'], unique=False)
    op.create_index(op.f('ix_email_verification_codes_created_at'), 'email_verification_codes', ['created_at'], unique=False)
    op.create_index(op.f('ix_email_verification_codes_is_deleted'), 'email_verification_codes', ['is_deleted'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_email_verification_codes_is_deleted'), table_name='email_verification_codes')
    op.drop_index(op.f('ix_email_verification_codes_created_at'), table_name='email_verification_codes')
    op.drop_index(op.f('ix_email_verification_codes_email'), table_name='email_verification_codes')
    op.drop_index(op.f('ix_email_verification_codes_id'), table_name='email_verification_codes')
    op.drop_table('email_verification_codes')
    op.drop_column('users', 'email_verified')
