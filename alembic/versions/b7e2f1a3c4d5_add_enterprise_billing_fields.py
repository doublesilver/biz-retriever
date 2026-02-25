"""Add enterprise billing fields (subscription lifecycle, invoices, idempotency)

Revision ID: b7e2f1a3c4d5
Revises: aaab08a12b55
Create Date: 2026-02-24 10:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'b7e2f1a3c4d5'
down_revision: Union[str, None] = 'aaab08a12b55'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade database schema."""

    # 1. Subscription 테이블에 새 컬럼 추가
    op.add_column('subscriptions', sa.Column('end_date', sa.DateTime(), nullable=True))
    op.add_column('subscriptions', sa.Column('status', sa.String(), server_default='active', nullable=False))
    op.add_column('subscriptions', sa.Column('cancelled_at', sa.DateTime(), nullable=True))
    op.add_column('subscriptions', sa.Column('cancel_reason', sa.String(), nullable=True))
    op.add_column('subscriptions', sa.Column('billing_key', sa.String(), nullable=True))
    op.add_column('subscriptions', sa.Column('failed_payment_count', sa.Integer(), server_default='0', nullable=False))
    op.add_column('subscriptions', sa.Column('last_payment_attempt', sa.DateTime(), nullable=True))

    op.create_index(op.f('ix_subscriptions_status'), 'subscriptions', ['status'], unique=False)
    op.create_index(op.f('ix_subscriptions_billing_key'), 'subscriptions', ['billing_key'], unique=False)

    # 2. PaymentHistory 테이블에 새 컬럼 추가
    op.add_column('payment_history', sa.Column('idempotency_key', sa.String(), nullable=True))
    op.add_column('payment_history', sa.Column('order_id', sa.String(), nullable=True))
    op.add_column('payment_history', sa.Column('payment_type', sa.String(), server_default='subscription_create', nullable=False))

    op.create_index(op.f('ix_payment_history_idempotency_key'), 'payment_history', ['idempotency_key'], unique=True)
    op.create_index(op.f('ix_payment_history_order_id'), 'payment_history', ['order_id'], unique=False)

    # 3. Invoice 테이블 생성
    op.create_table('invoices',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('invoice_number', sa.String(), nullable=False),
        sa.Column('subscription_id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=True),
        sa.Column('amount', sa.Float(), nullable=False),
        sa.Column('subtotal', sa.Float(), nullable=False),
        sa.Column('proration_amount', sa.Float(), nullable=False, server_default='0'),
        sa.Column('tax_amount', sa.Float(), nullable=False, server_default='0'),
        sa.Column('currency', sa.String(), nullable=False, server_default='KRW'),
        sa.Column('status', sa.String(), nullable=False, server_default='pending'),
        sa.Column('billing_period_start', sa.DateTime(), nullable=True),
        sa.Column('billing_period_end', sa.DateTime(), nullable=True),
        sa.Column('paid_at', sa.DateTime(), nullable=True),
        sa.Column('payment_key', sa.String(), nullable=True),
        sa.Column('plan_name', sa.String(), nullable=False),
        sa.Column('description', sa.String(), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['subscription_id'], ['subscriptions.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_invoices_id'), 'invoices', ['id'], unique=False)
    op.create_index(op.f('ix_invoices_invoice_number'), 'invoices', ['invoice_number'], unique=True)
    op.create_index(op.f('ix_invoices_subscription_id'), 'invoices', ['subscription_id'], unique=False)
    op.create_index(op.f('ix_invoices_user_id'), 'invoices', ['user_id'], unique=False)
    op.create_index(op.f('ix_invoices_status'), 'invoices', ['status'], unique=False)


def downgrade() -> None:
    """Downgrade database schema."""
    # Drop invoices table
    op.drop_index(op.f('ix_invoices_status'), table_name='invoices')
    op.drop_index(op.f('ix_invoices_user_id'), table_name='invoices')
    op.drop_index(op.f('ix_invoices_subscription_id'), table_name='invoices')
    op.drop_index(op.f('ix_invoices_invoice_number'), table_name='invoices')
    op.drop_index(op.f('ix_invoices_id'), table_name='invoices')
    op.drop_table('invoices')

    # Drop payment_history new columns
    op.drop_index(op.f('ix_payment_history_order_id'), table_name='payment_history')
    op.drop_index(op.f('ix_payment_history_idempotency_key'), table_name='payment_history')
    op.drop_column('payment_history', 'payment_type')
    op.drop_column('payment_history', 'order_id')
    op.drop_column('payment_history', 'idempotency_key')

    # Drop subscription new columns
    op.drop_index(op.f('ix_subscriptions_billing_key'), table_name='subscriptions')
    op.drop_index(op.f('ix_subscriptions_status'), table_name='subscriptions')
    op.drop_column('subscriptions', 'last_payment_attempt')
    op.drop_column('subscriptions', 'failed_payment_count')
    op.drop_column('subscriptions', 'billing_key')
    op.drop_column('subscriptions', 'cancel_reason')
    op.drop_column('subscriptions', 'cancelled_at')
    op.drop_column('subscriptions', 'status')
    op.drop_column('subscriptions', 'end_date')
