"""Initial schema - BidAnnouncement and User tables

Revision ID: 001_initial
Revises:
Create Date: 2024-01-01 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '001_initial'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create initial tables."""
    # Users 테이블
    op.create_table(
        'users',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('email', sa.String(length=255), nullable=False),
        sa.Column('hashed_password', sa.String(length=255), nullable=False),
        sa.Column('is_active', sa.Boolean(), nullable=False, default=True),
        sa.Column('is_superuser', sa.Boolean(), nullable=False, default=False),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('email')
    )
    op.create_index('ix_users_email', 'users', ['email'])

    # BidAnnouncement 테이블
    op.create_table(
        'bid_announcements',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('title', sa.String(length=500), nullable=False),
        sa.Column('content', sa.Text(), nullable=True),
        sa.Column('agency', sa.String(length=200), nullable=True),
        sa.Column('posted_at', sa.DateTime(), nullable=True),
        sa.Column('url', sa.String(length=1000), nullable=False),
        sa.Column('processed', sa.Boolean(), nullable=False, default=False),

        # Phase 1 필드
        sa.Column('source', sa.String(length=50), nullable=False, default='G2B'),
        sa.Column('deadline', sa.DateTime(), nullable=True),
        sa.Column('estimated_price', sa.Float(), nullable=True),
        sa.Column('importance_score', sa.Integer(), nullable=False, default=1),
        sa.Column('keywords_matched', sa.JSON(), nullable=True),
        sa.Column('is_notified', sa.Boolean(), nullable=False, default=False),
        sa.Column('crawled_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),

        # Phase 2 필드 (Kanban)
        sa.Column('status', sa.String(length=50), nullable=False, default='new'),
        sa.Column('assigned_to', sa.Integer(), sa.ForeignKey('users.id', ondelete='SET NULL'), nullable=True),
        sa.Column('notes', sa.Text(), nullable=True),

        # 타임스탬프
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),

        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('url')
    )

    # 인덱스 생성
    op.create_index('ix_bid_announcements_source', 'bid_announcements', ['source'])
    op.create_index('ix_bid_announcements_deadline', 'bid_announcements', ['deadline'])
    op.create_index('ix_bid_announcements_importance_score', 'bid_announcements', ['importance_score'])
    op.create_index('ix_bid_announcements_status', 'bid_announcements', ['status'])
    op.create_index('ix_bid_announcements_title', 'bid_announcements', ['title'])


def downgrade() -> None:
    """Drop all tables."""
    op.drop_index('ix_bid_announcements_title', table_name='bid_announcements')
    op.drop_index('ix_bid_announcements_status', table_name='bid_announcements')
    op.drop_index('ix_bid_announcements_importance_score', table_name='bid_announcements')
    op.drop_index('ix_bid_announcements_deadline', table_name='bid_announcements')
    op.drop_index('ix_bid_announcements_source', table_name='bid_announcements')
    op.drop_table('bid_announcements')

    op.drop_index('ix_users_email', table_name='users')
    op.drop_table('users')
