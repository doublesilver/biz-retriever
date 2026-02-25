"""add password reset and email verification fields

Revision ID: d2e3f4a5b6c7
Revises: c1a2b3d4e5f6
Create Date: 2026-02-24 18:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "d2e3f4a5b6c7"
down_revision: Union[str, None] = "c1a2b3d4e5f6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add password reset and email verification fields to users table."""
    # Password Reset fields
    op.add_column(
        "users",
        sa.Column("password_reset_token", sa.String(), nullable=True),
    )
    op.add_column(
        "users",
        sa.Column("password_reset_expires", sa.DateTime(), nullable=True),
    )
    op.create_index(
        "ix_users_password_reset_token",
        "users",
        ["password_reset_token"],
    )

    # Email Verification fields
    op.add_column(
        "users",
        sa.Column(
            "is_email_verified",
            sa.Boolean(),
            nullable=False,
            server_default="false",
        ),
    )
    op.add_column(
        "users",
        sa.Column("email_verification_token", sa.String(), nullable=True),
    )
    op.add_column(
        "users",
        sa.Column("email_verification_expires", sa.DateTime(), nullable=True),
    )
    op.create_index(
        "ix_users_email_verification_token",
        "users",
        ["email_verification_token"],
    )


def downgrade() -> None:
    """Remove password reset and email verification fields."""
    op.drop_index("ix_users_email_verification_token", table_name="users")
    op.drop_column("users", "email_verification_expires")
    op.drop_column("users", "email_verification_token")
    op.drop_column("users", "is_email_verified")
    op.drop_index("ix_users_password_reset_token", table_name="users")
    op.drop_column("users", "password_reset_expires")
    op.drop_column("users", "password_reset_token")
