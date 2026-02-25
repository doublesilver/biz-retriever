"""
InvoiceService 단위 테스트
- 인보이스 번호 채번
- 부가세 계산
- 인보이스 생성/상태 변경
- 조회
"""

from unittest.mock import AsyncMock, MagicMock

import pytest

from app.core.exceptions import InvoiceNotFoundError
from app.services.invoice_service import InvoiceService


class TestGenerateInvoiceNumber:
    """인보이스 번호 채번"""

    def test_format(self):
        service = InvoiceService()
        number = service.generate_invoice_number()
        assert number.startswith("INV-")
        parts = number.split("-")
        assert len(parts) == 3
        assert len(parts[1]) == 8  # YYYYMMDD
        assert len(parts[2]) == 8  # UUID hex

    def test_unique(self):
        service = InvoiceService()
        n1 = service.generate_invoice_number()
        n2 = service.generate_invoice_number()
        assert n1 != n2


class TestCalculateTax:
    """부가세 계산"""

    def test_basic(self):
        service = InvoiceService()
        # 11,000원 (VAT 포함) -> 부가세 1,000원
        tax = service.calculate_tax(11000)
        assert tax == 1000

    def test_zero(self):
        service = InvoiceService()
        assert service.calculate_tax(0) == 0

    def test_10000(self):
        service = InvoiceService()
        # 10,000원 (VAT 포함) -> 부가세 909원 (내세)
        tax = service.calculate_tax(10000)
        assert tax == 909

    def test_30000(self):
        service = InvoiceService()
        tax = service.calculate_tax(30000)
        assert tax == 2727


class TestCreateInvoice:
    """인보이스 생성"""

    async def test_create_with_db(self):
        service = InvoiceService()
        sub = MagicMock()
        sub.id = 1
        sub.user_id = 10
        db = MagicMock()

        invoice = await service.create_invoice(
            subscription=sub,
            amount=10000,
            plan_name="basic",
            payment_key="pay_key_123",
            db=db,
        )

        assert invoice.amount == 10000
        assert invoice.plan_name == "basic"
        assert invoice.user_id == 10
        assert invoice.status == "pending"
        assert invoice.currency == "KRW"
        assert invoice.invoice_number.startswith("INV-")
        db.add.assert_called_once_with(invoice)

    async def test_create_without_db(self):
        service = InvoiceService()
        sub = MagicMock()
        sub.id = 1
        sub.user_id = 10

        invoice = await service.create_invoice(
            subscription=sub,
            amount=30000,
            plan_name="pro",
        )

        assert invoice.amount == 30000
        assert invoice.plan_name == "pro"

    async def test_create_with_proration(self):
        service = InvoiceService()
        sub = MagicMock()
        sub.id = 1
        sub.user_id = 10

        invoice = await service.create_invoice(
            subscription=sub,
            amount=20000,
            plan_name="pro",
            proration_amount=5000,
        )

        assert invoice.amount == 20000
        assert invoice.proration_amount == 5000
        assert invoice.subtotal == 15000  # 20000 - 5000

    async def test_create_custom_description(self):
        service = InvoiceService()
        sub = MagicMock()
        sub.id = 1
        sub.user_id = 10

        invoice = await service.create_invoice(
            subscription=sub,
            amount=10000,
            plan_name="basic",
            description="커스텀 설명",
        )

        assert invoice.description == "커스텀 설명"


class TestInvoiceStatusChanges:
    """인보이스 상태 변경"""

    async def test_mark_paid(self):
        service = InvoiceService()
        invoice = MagicMock()
        result = await service.mark_paid(invoice, "pay_key_456")
        assert result.status == "paid"
        assert result.payment_key == "pay_key_456"
        assert result.paid_at is not None

    async def test_mark_failed(self):
        service = InvoiceService()
        invoice = MagicMock()
        result = await service.mark_failed(invoice)
        assert result.status == "failed"

    async def test_void_invoice(self):
        service = InvoiceService()
        invoice = MagicMock()
        result = await service.void_invoice(invoice)
        assert result.status == "void"

    async def test_refund_invoice(self):
        service = InvoiceService()
        invoice = MagicMock()
        result = await service.refund_invoice(invoice)
        assert result.status == "refunded"


class TestGetInvoices:
    """인보이스 조회"""

    async def test_get_user_invoices(self):
        service = InvoiceService()
        mock_invoices = [MagicMock(), MagicMock()]

        db = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalars().all.return_value = mock_invoices
        db.execute.return_value = mock_result

        invoices = await service.get_user_invoices(1, db)
        assert len(invoices) == 2

    async def test_get_user_invoices_with_pagination(self):
        service = InvoiceService()

        db = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalars().all.return_value = [MagicMock()]
        db.execute.return_value = mock_result

        invoices = await service.get_user_invoices(1, db, skip=5, limit=10)
        assert len(invoices) == 1

    async def test_get_invoice_by_number_found(self):
        service = InvoiceService()
        mock_invoice = MagicMock()

        db = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_invoice
        db.execute.return_value = mock_result

        invoice = await service.get_invoice_by_number("INV-20260224-ABCD1234", db)
        assert invoice is mock_invoice

    async def test_get_invoice_by_number_not_found(self):
        service = InvoiceService()

        db = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        db.execute.return_value = mock_result

        with pytest.raises(InvoiceNotFoundError):
            await service.get_invoice_by_number("INV-INVALID", db)

    async def test_get_user_invoice_count(self):
        service = InvoiceService()

        db = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalar.return_value = 5
        db.execute.return_value = mock_result

        count = await service.get_user_invoice_count(1, db)
        assert count == 5

    async def test_get_user_invoice_count_zero(self):
        service = InvoiceService()

        db = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalar.return_value = None
        db.execute.return_value = mock_result

        count = await service.get_user_invoice_count(1, db)
        assert count == 0
