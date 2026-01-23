"""Add exclude_keywords table

Revision ID: 34c3d8934e91
Revises: 002_bid_result
Create Date: 2026-01-23 13:21:30.291439

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '34c3d8934e91'
down_revision: Union[str, None] = '002_bid_result'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade database schema."""
    op.create_table(
        'exclude_keywords',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('word', sa.String(length=100), nullable=False),
        sa.Column('is_active', sa.Boolean(), nullable=False, default=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('word')
    )
    op.create_index('ix_exclude_keywords_word', 'exclude_keywords', ['word'])
    op.create_index('ix_exclude_keywords_is_active', 'exclude_keywords', ['is_active'])


def downgrade() -> None:
    """Downgrade database schema."""
    op.drop_index('ix_exclude_keywords_is_active', table_name='exclude_keywords')
    op.drop_index('ix_exclude_keywords_word', table_name='exclude_keywords')
    op.drop_table('exclude_keywords')
