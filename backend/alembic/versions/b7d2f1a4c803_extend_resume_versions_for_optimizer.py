"""Extend resume_versions for the optimizer

Adds the optimized payload, both export paths, and per-version scores so a
tailored variant can be re-scored or re-exported without rerunning optimization.

Revision ID: b7d2f1a4c803
Revises: a1c4e7d92b30
Create Date: 2026-08-11 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'b7d2f1a4c803'
down_revision: Union[str, None] = 'a1c4e7d92b30'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('resume_versions', sa.Column('label', sa.String(), nullable=True))
    op.add_column('resume_versions', sa.Column('pdf_path', sa.String(), nullable=True))
    op.add_column('resume_versions', sa.Column('optimized_data', sa.JSON(), nullable=True))
    op.add_column('resume_versions', sa.Column('ats_score', sa.Float(), nullable=True))
    op.add_column('resume_versions', sa.Column('alignment_score', sa.Float(), nullable=True))
    op.add_column('resume_versions', sa.Column('baseline_ats_score', sa.Float(), nullable=True))
    op.add_column('resume_versions', sa.Column('baseline_alignment_score', sa.Float(), nullable=True))


def downgrade() -> None:
    op.drop_column('resume_versions', 'baseline_alignment_score')
    op.drop_column('resume_versions', 'baseline_ats_score')
    op.drop_column('resume_versions', 'alignment_score')
    op.drop_column('resume_versions', 'ats_score')
    op.drop_column('resume_versions', 'optimized_data')
    op.drop_column('resume_versions', 'pdf_path')
    op.drop_column('resume_versions', 'label')
