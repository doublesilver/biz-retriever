"""add composite indexes for query optimization

Revision ID: c1a2b3d4e5f6
Revises: aaab08a12b55
Create Date: 2026-02-24 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "c1a2b3d4e5f6"
down_revision: Union[str, None] = "aaab08a12b55"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # bid_announcements: status + importance_score (Kanban 필터링)
    op.create_index(
        "ix_bid_announcements_status_importance",
        "bid_announcements",
        ["status", "importance_score"],
    )

    # bid_announcements: source + posted_at (출처별 시간순 조회)
    op.create_index(
        "ix_bid_announcements_source_posted",
        "bid_announcements",
        ["source", "posted_at"],
    )

    # bid_announcements: deadline (마감일 임박 공고 조회 최적화)
    # deadline은 이미 단일 인덱스가 있으므로 status와 복합 인덱스 추가
    op.create_index(
        "ix_bid_announcements_status_deadline",
        "bid_announcements",
        ["status", "deadline"],
    )

    # bid_results: source + bid_open_date (ML 학습 데이터 조회)
    op.create_index(
        "ix_bid_results_source_open_date",
        "bid_results",
        ["source", "bid_open_date"],
    )

    # crawler_logs: source + status (모니터링 대시보드 조회)
    op.create_index(
        "ix_crawler_logs_source_status",
        "crawler_logs",
        ["source", "status"],
    )

    # user_keywords: user_id + is_active (사용자별 활성 키워드 조회)
    op.create_index(
        "ix_user_keywords_user_active",
        "user_keywords",
        ["user_id", "is_active"],
    )


def downgrade() -> None:
    op.drop_index("ix_user_keywords_user_active", table_name="user_keywords")
    op.drop_index("ix_crawler_logs_source_status", table_name="crawler_logs")
    op.drop_index("ix_bid_results_source_open_date", table_name="bid_results")
    op.drop_index("ix_bid_announcements_status_deadline", table_name="bid_announcements")
    op.drop_index("ix_bid_announcements_source_posted", table_name="bid_announcements")
    op.drop_index("ix_bid_announcements_status_importance", table_name="bid_announcements")
