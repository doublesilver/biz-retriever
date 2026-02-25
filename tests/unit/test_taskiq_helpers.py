"""
Taskiq 이메일 렌더링 헬퍼 테스트
- _base_email_wrapper
- _render_renewal_email
- _render_payment_failed_email
- _render_expiring_email
- _render_cancelled_email

NOTE: taskiq_tasks.py는 broker 데코레이터를 사용하므로 직접 import 시
taskiq_redis 의존성이 필요. 여기서는 broker mock으로 헬퍼 함수만 테스트.
"""

import sys
from unittest.mock import MagicMock, patch


def _import_helpers():
    """taskiq 의존성을 mock하고 헬퍼 함수들만 import"""
    # Mock taskiq dependencies
    mock_broker = MagicMock()
    mock_broker.task = lambda **kw: lambda f: f  # passthrough decorator

    mock_modules = {
        "taskiq": MagicMock(),
        "taskiq.schedule_sources": MagicMock(),
        "taskiq_redis": MagicMock(ListQueueBroker=lambda **kw: mock_broker),
    }

    with patch.dict(sys.modules, mock_modules):
        # Patch the broker in taskiq_app before importing taskiq_tasks
        with patch("app.worker.taskiq_app.broker", mock_broker):
            from app.worker.taskiq_tasks import (
                _base_email_wrapper,
                _render_cancelled_email,
                _render_expiring_email,
                _render_payment_failed_email,
                _render_renewal_email,
            )
            return (
                _base_email_wrapper,
                _render_renewal_email,
                _render_payment_failed_email,
                _render_expiring_email,
                _render_cancelled_email,
            )


class TestBaseEmailWrapper:
    def test_contains_title(self):
        helpers = _import_helpers()
        _base_email_wrapper = helpers[0]
        html = _base_email_wrapper("테스트 제목", "<p>내용</p>")
        assert "테스트 제목" in html
        assert "Biz-Retriever" in html

    def test_contains_body(self):
        helpers = _import_helpers()
        _base_email_wrapper = helpers[0]
        html = _base_email_wrapper("제목", "<p>커스텀 본문</p>")
        assert "커스텀 본문" in html

    def test_is_html(self):
        helpers = _import_helpers()
        _base_email_wrapper = helpers[0]
        html = _base_email_wrapper("제목", "<p>내용</p>")
        assert "<!DOCTYPE html>" in html
        assert "</html>" in html


class TestRenderRenewalEmail:
    def test_contains_user_and_plan(self):
        helpers = _import_helpers()
        _render_renewal_email = helpers[1]
        html = _render_renewal_email("홍길동", "basic", 10000)
        assert "홍길동" in html
        assert "BASIC" in html
        assert "10,000" in html

    def test_is_wrapped_html(self):
        helpers = _import_helpers()
        _render_renewal_email = helpers[1]
        html = _render_renewal_email("사용자", "pro", 30000)
        assert "<!DOCTYPE html>" in html
        assert "구독 갱신 완료" in html


class TestRenderPaymentFailedEmail:
    def test_contains_warning(self):
        helpers = _import_helpers()
        _render_payment_failed_email = helpers[2]
        html = _render_payment_failed_email("홍길동", "basic", 10000)
        assert "홍길동" in html
        assert "실패" in html
        assert "BASIC" in html


class TestRenderExpiringEmail:
    def test_contains_plan(self):
        helpers = _import_helpers()
        _render_expiring_email = helpers[3]
        html = _render_expiring_email("홍길동", "pro")
        assert "PRO" in html
        assert "만료" in html


class TestRenderCancelledEmail:
    def test_contains_plan(self):
        helpers = _import_helpers()
        _render_cancelled_email = helpers[4]
        html = _render_cancelled_email("홍길동", "basic")
        assert "BASIC" in html
        assert "해지" in html
        assert "재구독" in html
