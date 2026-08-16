"""Add profile target_role and per-user notification settings

The settings page needs a place to store an aspirational target role and each
user's notification preferences. target_role lives on `users` alongside the
other profile identity fields; notification toggles get a dedicated 1:1 table so
they can grow without widening the auth-critical row.

Revision ID: d5f8a3c96b21
Revises: c3a9e5b71f42
Create Date: 2026-08-15 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'd5f8a3c96b21'
down_revision: Union[str, None] = 'c3a9e5b71f42'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('users', sa.Column('target_role', sa.String(), nullable=True))

    op.create_table(
        'notification_settings',
        sa.Column('user_id', sa.UUID(), nullable=False),
        sa.Column('email_alerts_on_new_matches', sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column('weekly_career_readiness_report', sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.Column('is_deleted', sa.Boolean(), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('user_id'),
    )
    op.create_index(op.f('ix_notification_settings_id'), 'notification_settings', ['id'], unique=False)
    op.create_index(op.f('ix_notification_settings_user_id'), 'notification_settings', ['user_id'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_notification_settings_user_id'), table_name='notification_settings')
    op.drop_index(op.f('ix_notification_settings_id'), table_name='notification_settings')
    op.drop_table('notification_settings')
    op.drop_column('users', 'target_role')
