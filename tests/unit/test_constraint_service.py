"""
ConstraintService 단위 테스트
- Gemini 미설정 시 빈 dict 반환
- 정상 추출 시 JSON 파싱 및 validation
- 예외 처리 (파싱 실패)
"""

import sys
from unittest.mock import MagicMock, patch

import pytest

from app.db.models import BidAnnouncement


def _get_constraint_service():
    """google.generativeai를 mock하고 ConstraintService import"""
    # google.generativeai가 없을 수 있으므로 mock
    if "google.generativeai" not in sys.modules:
        mock_genai = MagicMock()
        sys.modules["google"] = MagicMock()
        sys.modules["google.generativeai"] = mock_genai

    from app.services.constraint_service import ConstraintService
    return ConstraintService


class TestConstraintServiceNoApiKey:
    """Gemini API 키 미설정 시"""

    async def test_no_model_returns_empty(self):
        ConstraintService = _get_constraint_service()
        service = ConstraintService.__new__(ConstraintService)
        service.model = None

        bid = MagicMock(spec=BidAnnouncement)
        bid.title = "테스트 공고"
        bid.agency = "테스트 기관"
        bid.content = "본문"
        bid.attachment_content = None
        bid.id = 1

        result = await service.extract_constraints(bid)
        assert result == {}


class TestConstraintServiceWithModel:
    """Gemini 모델이 존재할 때"""

    async def test_extract_success_json_block(self):
        ConstraintService = _get_constraint_service()
        service = ConstraintService.__new__(ConstraintService)

        mock_response = MagicMock()
        mock_response.text = '```json\n{"region_code": "11", "license_requirements": ["정보통신공사업"], "min_performance": 100000000.0}\n```'
        service.model = MagicMock()

        bid = MagicMock(spec=BidAnnouncement)
        bid.title = "서울시 정보통신 공사"
        bid.agency = "서울시청"
        bid.content = "정보통신공사업 면허 필수"
        bid.attachment_content = None
        bid.id = 1

        with patch("asyncio.to_thread", return_value=mock_response):
            result = await service.extract_constraints(bid)

        assert result["region_code"] == "11"
        assert "정보통신공사업" in result["license_requirements"]
        assert result["min_performance"] == 100000000.0

    async def test_extract_success_raw_json(self):
        ConstraintService = _get_constraint_service()
        service = ConstraintService.__new__(ConstraintService)

        mock_response = MagicMock()
        mock_response.text = '{"region_code": "41", "license_requirements": [], "min_performance": 0.0}'
        service.model = MagicMock()

        bid = MagicMock(spec=BidAnnouncement)
        bid.title = "경기도 조경 공사"
        bid.agency = "경기도청"
        bid.content = "조경 관련"
        bid.attachment_content = None
        bid.id = 2

        with patch("asyncio.to_thread", return_value=mock_response):
            result = await service.extract_constraints(bid)

        assert result["region_code"] == "41"
        assert result["license_requirements"] == []
        assert result["min_performance"] == 0.0

    async def test_extract_with_attachment(self):
        ConstraintService = _get_constraint_service()
        service = ConstraintService.__new__(ConstraintService)

        mock_response = MagicMock()
        mock_response.text = '```json\n{"region_code": "00", "license_requirements": ["건축공사업"], "min_performance": 50000000.0}\n```'
        service.model = MagicMock()

        bid = MagicMock(spec=BidAnnouncement)
        bid.title = "건축 공사"
        bid.agency = "한국도로공사"
        bid.content = "건축 관련 공사"
        bid.attachment_content = "첨부파일 내용: 건축공사업 면허 보유사 제한" * 100
        bid.id = 3

        with patch("asyncio.to_thread", return_value=mock_response):
            result = await service.extract_constraints(bid)

        assert "건축공사업" in result["license_requirements"]

    async def test_extract_failure_returns_empty(self):
        ConstraintService = _get_constraint_service()
        service = ConstraintService.__new__(ConstraintService)
        service.model = MagicMock()

        bid = MagicMock(spec=BidAnnouncement)
        bid.title = "테스트"
        bid.agency = "기관"
        bid.content = "내용"
        bid.attachment_content = None
        bid.id = 4

        with patch("asyncio.to_thread", side_effect=Exception("API Error")):
            result = await service.extract_constraints(bid)

        assert result == {}

    async def test_extract_code_block_no_json_label(self):
        """```만 있고 json 라벨이 없는 경우"""
        ConstraintService = _get_constraint_service()
        service = ConstraintService.__new__(ConstraintService)

        mock_response = MagicMock()
        mock_response.text = '```\n{"region_code": "26", "license_requirements": ["조경공사업"], "min_performance": 0.0}\n```'
        service.model = MagicMock()

        bid = MagicMock(spec=BidAnnouncement)
        bid.title = "부산 조경"
        bid.agency = "부산시"
        bid.content = "조경"
        bid.attachment_content = None
        bid.id = 5

        with patch("asyncio.to_thread", return_value=mock_response):
            result = await service.extract_constraints(bid)

        assert result["region_code"] == "26"
