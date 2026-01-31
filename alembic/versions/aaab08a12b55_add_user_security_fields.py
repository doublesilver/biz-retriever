"""add_user_security_fields

Revision ID: aaab08a12b55
Revises: 80f06c107978
Create Date: 2026-01-31 14:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'aaab08a12b55'
down_revision: Union[str, None] = '80f06c107978'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add security fields to users table for enhanced authentication."""
    # Add failed login tracking
    op.add_column('users', sa.Column('failed_login_attempts', sa.Integer(), nullable=False, server_default='0'))
    
    # Add account lockout field
    op.add_column('users', sa.Column('locked_until', sa.DateTime(), nullable=True))
    
    # Add last login timestamp
    op.add_column('users', sa.Column('last_login_at', sa.DateTime(), nullable=True))


def downgrade() -> None:
    """Remove security fields from users table."""
    op.drop_column('users', 'last_login_at')
    op.drop_column('users', 'locked_until')
    op.drop_column('users', 'failed_login_attempts')
