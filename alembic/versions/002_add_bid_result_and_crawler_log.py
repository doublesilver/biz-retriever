"""Add BidResult and CrawlerLog tables

Revision ID: 002_bid_result
Revises: 001_initial
Create Date: 2026-01-23 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '002_bid_result'
down_revision: Union[str, None] = '001_initial'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create bid_results and crawler_logs tables."""

    # BidResult 테이블 - 낙찰 결과 저장
    op.create_table(
        'bid_results',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('bid_announcement_id', sa.Integer(), nullable=True),
        sa.Column('bid_number', sa.String(length=100), nullable=False),
        sa.Column('title', sa.String(length=500), nullable=False),
        sa.Column('agency', sa.String(length=200), nullable=True),
        sa.Column('source', sa.String(length=50), nullable=False, default='G2B'),
        sa.Column('winning_company', sa.String(length=200), nullable=False),
        sa.Column('winning_price', sa.Float(), nullable=False),
        sa.Column('base_price', sa.Float(), nullable=True),
        sa.Column('estimated_price', sa.Float(), nullable=True),
        sa.Column('winning_rate', sa.Float(), nullable=True),
        sa.Column('participant_count', sa.Integer(), nullable=True),
        sa.Column('bid_method', sa.String(length=100), nullable=True),
        sa.Column('bid_open_date', sa.DateTime(), nullable=True),
        sa.Column('contract_date', sa.DateTime(), nullable=True),
        sa.Column('category', sa.String(length=100), nullable=True),
        sa.Column('sub_category', sa.String(length=100), nullable=True),
        sa.Column('keywords', sa.JSON(), nullable=True),
        sa.Column('raw_data', sa.JSON(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['bid_announcement_id'], ['bid_announcements.id'], ondelete='SET NULL'),
        sa.UniqueConstraint('bid_number')
    )

    # BidResult 인덱스
    op.create_index('ix_bid_results_bid_announcement_id', 'bid_results', ['bid_announcement_id'])
    op.create_index('ix_bid_results_bid_number', 'bid_results', ['bid_number'])
    op.create_index('ix_bid_results_title', 'bid_results', ['title'])
    op.create_index('ix_bid_results_agency', 'bid_results', ['agency'])
    op.create_index('ix_bid_results_source', 'bid_results', ['source'])
    op.create_index('ix_bid_results_winning_company', 'bid_results', ['winning_company'])
    op.create_index('ix_bid_results_winning_price', 'bid_results', ['winning_price'])
    op.create_index('ix_bid_results_bid_open_date', 'bid_results', ['bid_open_date'])
    op.create_index('ix_bid_results_category', 'bid_results', ['category'])

    # CrawlerLog 테이블 - 크롤러 실행 로그
    op.create_table(
        'crawler_logs',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('source', sa.String(length=50), nullable=False),
        sa.Column('task_id', sa.String(length=100), nullable=True),
        sa.Column('status', sa.String(length=50), nullable=False),
        sa.Column('started_at', sa.DateTime(), nullable=False),
        sa.Column('completed_at', sa.DateTime(), nullable=True),
        sa.Column('duration_seconds', sa.Float(), nullable=True),
        sa.Column('total_fetched', sa.Integer(), nullable=False, default=0),
        sa.Column('total_filtered', sa.Integer(), nullable=False, default=0),
        sa.Column('total_new', sa.Integer(), nullable=False, default=0),
        sa.Column('total_duplicate', sa.Integer(), nullable=False, default=0),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('error_traceback', sa.Text(), nullable=True),
        sa.Column('search_params', sa.JSON(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('task_id')
    )

    # CrawlerLog 인덱스
    op.create_index('ix_crawler_logs_source', 'crawler_logs', ['source'])
    op.create_index('ix_crawler_logs_status', 'crawler_logs', ['status'])
    op.create_index('ix_crawler_logs_started_at', 'crawler_logs', ['started_at'])


def downgrade() -> None:
    """Drop bid_results and crawler_logs tables."""

    # CrawlerLog 인덱스 삭제
    op.drop_index('ix_crawler_logs_started_at', table_name='crawler_logs')
    op.drop_index('ix_crawler_logs_status', table_name='crawler_logs')
    op.drop_index('ix_crawler_logs_source', table_name='crawler_logs')
    op.drop_table('crawler_logs')

    # BidResult 인덱스 삭제
    op.drop_index('ix_bid_results_category', table_name='bid_results')
    op.drop_index('ix_bid_results_bid_open_date', table_name='bid_results')
    op.drop_index('ix_bid_results_winning_price', table_name='bid_results')
    op.drop_index('ix_bid_results_winning_company', table_name='bid_results')
    op.drop_index('ix_bid_results_source', table_name='bid_results')
    op.drop_index('ix_bid_results_agency', table_name='bid_results')
    op.drop_index('ix_bid_results_title', table_name='bid_results')
    op.drop_index('ix_bid_results_bid_number', table_name='bid_results')
    op.drop_index('ix_bid_results_bid_announcement_id', table_name='bid_results')
    op.drop_table('bid_results')
