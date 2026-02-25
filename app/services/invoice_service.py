"""
Invoice Service — 인보이스(영수증) 생성 및 관리

구독 결제마다 인보이스를 자동 생성하여 과금 이력을 추적.
프로레이션(일할 계산), 부가세 계산, 인보이스 번호 채번 포함.
"""

import uuid
from datetime import datetime, timedelta

from sqlalchemy import desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import InvoiceNotFoundError
from app.core.logging import logger
from app.db.models import Invoice, Subscription


class InvoiceService:
    """인보이스 생성/조회/관리 서비스."""

    TAX_RATE = 0.10  # 부가세 10%

    @staticmethod
    def generate_invoice_number() -> str:
        """
        인보이스 번호 채번.
        형식: INV-YYYYMMDD-XXXXXXXX
        """
        date_part = datetime.utcnow().strftime("%Y%m%d")
        unique_part = uuid.uuid4().hex[:8].upper()
        return f"INV-{date_part}-{unique_part}"

    def calculate_tax(self, subtotal: float) -> float:
        """부가세 계산 (내세 방식 — 총액에 포함)."""
        return round(subtotal * self.TAX_RATE / (1 + self.TAX_RATE))

    async def create_invoice(
        self,
        subscription: Subscription,
        amount: float,
        plan_name: str,
        payment_key: str | None = None,
        proration_amount: float = 0.0,
        description: str | None = None,
        db: AsyncSession | None = None,
    ) -> Invoice:
        """
        인보이스 생성.

        Args:
            subscription: 관련 구독
            amount: 최종 청구 금액
            plan_name: 플랜 이름
            payment_key: 결제키
            proration_amount: 프로레이션 차액
            description: 설명
            db: DB 세션

        Returns:
            생성된 Invoice 객체
        """
        now = datetime.utcnow()
        subtotal = amount - proration_amount
        tax = self.calculate_tax(amount)

        invoice = Invoice(
            invoice_number=self.generate_invoice_number(),
            subscription_id=subscription.id,
            user_id=subscription.user_id,
            amount=amount,
            subtotal=subtotal,
            proration_amount=proration_amount,
            tax_amount=tax,
            currency="KRW",
            status="pending",
            billing_period_start=now,
            billing_period_end=now + timedelta(days=30),
            payment_key=payment_key,
            plan_name=plan_name,
            description=description or f"{plan_name.upper()} 플랜 구독료",
        )

        if db:
            db.add(invoice)

        logger.info(f"Invoice created: {invoice.invoice_number}, " f"user={subscription.user_id}, amount={amount}원")
        return invoice

    async def mark_paid(self, invoice: Invoice, payment_key: str) -> Invoice:
        """인보이스를 결제 완료 상태로 변경."""
        invoice.status = "paid"
        invoice.paid_at = datetime.utcnow()
        invoice.payment_key = payment_key
        return invoice

    async def mark_failed(self, invoice: Invoice) -> Invoice:
        """인보이스를 결제 실패 상태로 변경."""
        invoice.status = "failed"
        return invoice

    async def void_invoice(self, invoice: Invoice) -> Invoice:
        """인보이스 무효화."""
        invoice.status = "void"
        return invoice

    async def refund_invoice(self, invoice: Invoice) -> Invoice:
        """인보이스 환불 처리."""
        invoice.status = "refunded"
        return invoice

    async def get_user_invoices(
        self,
        user_id: int,
        db: AsyncSession,
        skip: int = 0,
        limit: int = 20,
    ) -> list[Invoice]:
        """사용자의 인보이스 목록 조회."""
        stmt = (
            select(Invoice)
            .where(Invoice.user_id == user_id)
            .order_by(desc(Invoice.created_at))
            .offset(skip)
            .limit(limit)
        )
        result = await db.execute(stmt)
        return list(result.scalars().all())

    async def get_invoice_by_number(
        self,
        invoice_number: str,
        db: AsyncSession,
    ) -> Invoice:
        """인보이스 번호로 조회."""
        stmt = select(Invoice).where(Invoice.invoice_number == invoice_number)
        result = await db.execute(stmt)
        invoice = result.scalar_one_or_none()
        if not invoice:
            raise InvoiceNotFoundError(invoice_number)
        return invoice

    async def get_user_invoice_count(self, user_id: int, db: AsyncSession) -> int:
        """사용자 인보이스 총 개수."""
        stmt = select(func.count(Invoice.id)).where(Invoice.user_id == user_id)
        result = await db.execute(stmt)
        return result.scalar() or 0


invoice_service = InvoiceService()
