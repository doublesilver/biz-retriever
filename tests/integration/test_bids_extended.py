"""
Bids API 확장 테스트
- POST /bids/upload (PDF/HWP 파일 업로드)

NOTE: GET /bids/matched는 라우트 순서 문제로
/{bid_id} 라우트가 먼저 매칭되어 422를 반환합니다.
(앱 코드의 라우트 정의 순서 이슈 — 테스트 범위 외)
"""

import sys
from datetime import datetime
from types import ModuleType, SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from httpx import AsyncClient

# Pre-inject fake app.worker.tasks module so the lazy import inside
# upload_bid (line 287: from app.worker.tasks import process_bid_analysis)
# does not fail when taskiq is not installed.
_fake_tasks = ModuleType("app.worker.tasks")
_fake_tasks.process_bid_analysis = MagicMock()
_fake_tasks.process_bid_analysis.delay = MagicMock()
sys.modules.setdefault("app.worker.tasks", _fake_tasks)


def _make_bid_mock(**overrides):
    """BidResponse 스키마(from_attributes=True)에 맞는 완전한 mock 생성.

    MagicMock은 정의하지 않은 속성에 자동으로 MagicMock을 반환하므로
    Pydantic string/int validation이 실패한다.
    SimpleNamespace를 사용하여 명시적 속성만 갖는 객체를 만든다.
    """
    now = datetime.utcnow()
    defaults = dict(
        id=999,
        title="테스트 공고",
        content="테스트 내용",
        agency="테스트 기관",
        posted_at=now,
        url="http://uploaded.file/test.pdf-123",
        created_at=now,
        updated_at=now,
        processed=False,
        source="G2B",
        deadline=None,
        estimated_price=None,
        importance_score=1,
        keywords_matched=None,
        is_notified=False,
        ai_summary=None,
        ai_keywords=None,
        status="new",
        assigned_to=None,
        notes=None,
        assignee=None,
    )
    defaults.update(overrides)
    return SimpleNamespace(**defaults)


class TestUploadBid:
    """POST /bids/upload 테스트"""

    @pytest.mark.asyncio
    async def test_upload_pdf_success(self, authenticated_client: AsyncClient):
        """PDF 파일 업로드 성공"""
        pdf_content = b"%PDF-1.4 test content for upload"

        with patch("app.api.endpoints.bids.file_service") as mock_fs:
            mock_fs.get_text_from_file = AsyncMock(return_value="추출된 공고 텍스트 내용입니다.")
            with patch("app.api.endpoints.bids.bid_service") as mock_bs:
                mock_bid = _make_bid_mock(
                    id=999,
                    title="업로드 테스트 공고",
                    content="추출된 공고 텍스트 내용입니다.",
                    agency="테스트 기관",
                )
                mock_bs.create_bid = AsyncMock(return_value=mock_bid)

                response = await authenticated_client.post(
                    "/api/v1/bids/upload",
                    files={"file": ("test.pdf", pdf_content, "application/pdf")},
                    params={"title": "업로드 테스트 공고", "agency": "테스트 기관"},
                )

        assert response.status_code == 201

    @pytest.mark.asyncio
    async def test_upload_unsupported_format(self, authenticated_client: AsyncClient):
        """지원하지 않는 형식 → 400"""
        response = await authenticated_client.post(
            "/api/v1/bids/upload",
            files={"file": ("test.doc", b"word content", "application/msword")},
            params={"title": "테스트"},
        )
        assert response.status_code == 400

    @pytest.mark.asyncio
    async def test_upload_oversized_file(self, authenticated_client: AsyncClient):
        """파일 크기 초과 → 400"""
        large_content = b"0" * (11 * 1024 * 1024)
        response = await authenticated_client.post(
            "/api/v1/bids/upload",
            files={"file": ("large.pdf", large_content, "application/pdf")},
            params={"title": "큰 파일"},
        )
        assert response.status_code == 400

    @pytest.mark.asyncio
    async def test_upload_hwp_file(self, authenticated_client: AsyncClient):
        """HWP 파일 업로드 성공"""
        hwp_content = b"HWP test content"

        with patch("app.api.endpoints.bids.file_service") as mock_fs:
            mock_fs.get_text_from_file = AsyncMock(return_value="HWP 추출 텍스트")
            with patch("app.api.endpoints.bids.bid_service") as mock_bs:
                mock_bid = _make_bid_mock(
                    id=998,
                    title="HWP 공고",
                    content="HWP 추출 텍스트",
                    agency="Unknown",
                )
                mock_bs.create_bid = AsyncMock(return_value=mock_bid)

                response = await authenticated_client.post(
                    "/api/v1/bids/upload",
                    files={"file": ("document.hwp", hwp_content, "application/x-hwp")},
                    params={"title": "HWP 공고"},
                )

        assert response.status_code == 201

    @pytest.mark.asyncio
    async def test_upload_unauthenticated(self, async_client: AsyncClient):
        """미인증 시 401"""
        files = {"file": ("test.pdf", b"fake pdf content", "application/pdf")}
        response = await async_client.post("/api/v1/bids/upload", files=files, params={"title": "테스트"})
        assert response.status_code == 401
