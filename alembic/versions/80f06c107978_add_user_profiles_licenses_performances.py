"""add_user_profiles_licenses_performances

Revision ID: 80f06c107978
Revises: 04795226d50e
Create Date: 2026-01-30 11:32:03.243067

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '80f06c107978'
down_revision: Union[str, None] = '04795226d50e'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade database schema."""
    # Create user_profiles table
    op.create_table(
        'user_profiles',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        
        # Basic company info
        sa.Column('company_name', sa.String(), nullable=True),
        sa.Column('brn', sa.String(), nullable=True),  # Business Registration Number
        sa.Column('representative', sa.String(), nullable=True),
        sa.Column('address', sa.String(), nullable=True),
        sa.Column('location_code', sa.String(), nullable=True),
        sa.Column('company_type', sa.String(), nullable=True),
        sa.Column('keywords', sa.JSON(), nullable=True),
        
        # Phase 6.1: Detailed Profile
        sa.Column('credit_rating', sa.String(), nullable=True),
        sa.Column('employee_count', sa.Integer(), nullable=True),
        sa.Column('founding_year', sa.Integer(), nullable=True),
        sa.Column('main_bank', sa.String(), nullable=True),
        sa.Column('standard_industry_codes', sa.JSON(), nullable=True),
        
        # Phase 8: Notification Settings
        sa.Column('slack_webhook_url', sa.String(), nullable=True),
        sa.Column('is_email_enabled', sa.Boolean(), nullable=False, server_default=sa.text('false')),
        sa.Column('is_slack_enabled', sa.Boolean(), nullable=False, server_default=sa.text('false')),
        
        # Timestamps
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
        
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.UniqueConstraint('user_id')
    )
    
    # Create indexes for user_profiles
    op.create_index(op.f('ix_user_profiles_id'), 'user_profiles', ['id'], unique=False)
    op.create_index(op.f('ix_user_profiles_company_name'), 'user_profiles', ['company_name'], unique=False)
    op.create_index(op.f('ix_user_profiles_brn'), 'user_profiles', ['brn'], unique=True)
    op.create_index(op.f('ix_user_profiles_location_code'), 'user_profiles', ['location_code'], unique=False)
    
    # Create user_licenses table
    op.create_table(
        'user_licenses',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('profile_id', sa.Integer(), nullable=False),
        sa.Column('license_name', sa.String(), nullable=False),
        sa.Column('license_number', sa.String(), nullable=True),
        sa.Column('issue_date', sa.DateTime(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
        
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['profile_id'], ['user_profiles.id'], ondelete='CASCADE')
    )
    
    # Create indexes for user_licenses
    op.create_index(op.f('ix_user_licenses_id'), 'user_licenses', ['id'], unique=False)
    op.create_index(op.f('ix_user_licenses_license_name'), 'user_licenses', ['license_name'], unique=False)
    
    # Create user_performances table
    op.create_table(
        'user_performances',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('profile_id', sa.Integer(), nullable=False),
        sa.Column('project_name', sa.String(), nullable=False),
        sa.Column('amount', sa.Float(), nullable=False, server_default=sa.text('0.0')),
        sa.Column('completion_date', sa.DateTime(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
        
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['profile_id'], ['user_profiles.id'], ondelete='CASCADE')
    )
    
    # Create indexes for user_performances
    op.create_index(op.f('ix_user_performances_id'), 'user_performances', ['id'], unique=False)


def downgrade() -> None:
    """Downgrade database schema."""
    # Drop user_performances table and indexes
    op.drop_index(op.f('ix_user_performances_id'), table_name='user_performances')
    op.drop_table('user_performances')
    
    # Drop user_licenses table and indexes
    op.drop_index(op.f('ix_user_licenses_license_name'), table_name='user_licenses')
    op.drop_index(op.f('ix_user_licenses_id'), table_name='user_licenses')
    op.drop_table('user_licenses')
    
    # Drop user_profiles table and indexes
    op.drop_index(op.f('ix_user_profiles_location_code'), table_name='user_profiles')
    op.drop_index(op.f('ix_user_profiles_brn'), table_name='user_profiles')
    op.drop_index(op.f('ix_user_profiles_company_name'), table_name='user_profiles')
    op.drop_index(op.f('ix_user_profiles_id'), table_name='user_profiles')
    op.drop_table('user_profiles')
