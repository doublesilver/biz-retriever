"""
EmailService __init__ 분기 커버리지 테스트
- SENDGRID_AVAILABLE=True, 유효한 API 키 (SG.)
- SENDGRID_AVAILABLE=True, 유효하지 않은 API 키
"""

from unittest.mock import MagicMock, patch

import app.services.email_service as email_mod


class TestEmailServiceInitWithSendGrid:
    """SendGrid 설치된 환경에서 __init__ 분기"""

    def test_valid_api_key(self):
        """SG. 으로 시작하는 유효한 API 키 -> client 생성"""
        mock_sg_client = MagicMock()

        with patch.object(email_mod, "SENDGRID_AVAILABLE", True):
            with patch.object(email_mod, "SendGridAPIClient", return_value=mock_sg_client):
                with patch.dict("os.environ", {"SENDGRID_API_KEY": "SG.test-key-123"}):
                    svc = email_mod.EmailService()

        assert svc.client is mock_sg_client
        assert svc.api_key == "SG.test-key-123"
        assert svc.from_email is not None

    def test_invalid_api_key(self):
        """SG. 으로 시작하지 않는 키 -> client=None"""
        with patch.object(email_mod, "SENDGRID_AVAILABLE", True):
            with patch.dict("os.environ", {"SENDGRID_API_KEY": "invalid-key"}):
                svc = email_mod.EmailService()

        assert svc.client is None

    def test_empty_api_key(self):
        """빈 API 키 -> client=None"""
        with patch.object(email_mod, "SENDGRID_AVAILABLE", True):
            with patch.dict("os.environ", {"SENDGRID_API_KEY": ""}):
                svc = email_mod.EmailService()

        assert svc.client is None

    def test_api_key_from_settings(self):
        """환경변수 없고 settings에서 가져오기"""
        mock_sg_client = MagicMock()
        mock_settings = MagicMock()
        mock_settings.SENDGRID_API_KEY = "SG.from-settings"

        with patch.object(email_mod, "SENDGRID_AVAILABLE", True):
            with patch.object(email_mod, "SendGridAPIClient", return_value=mock_sg_client):
                with patch.dict("os.environ", {}, clear=False):
                    # Remove SENDGRID_API_KEY from env if present
                    import os
                    env_val = os.environ.pop("SENDGRID_API_KEY", None)
                    try:
                        with patch.object(email_mod, "settings", mock_settings):
                            svc = email_mod.EmailService()
                    finally:
                        if env_val is not None:
                            os.environ["SENDGRID_API_KEY"] = env_val

        assert svc.client is mock_sg_client
