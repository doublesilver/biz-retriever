"""
KeywordService 단위 테스트
- 키워드 CRUD
- 활성 키워드 조회
- 중복 키워드 방지
"""

from unittest.mock import AsyncMock, MagicMock

import pytest

from app.services.keyword_service import KeywordService


class TestGetActiveKeywords:
    """활성 키워드 조회"""

    def setup_method(self):
        self.service = KeywordService()

    async def test_returns_active_keywords(self):
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = ["폐기물", "단순공사"]

        session = AsyncMock()
        session.execute.return_value = mock_result

        result = await self.service.get_active_keywords(session)
        assert result == ["폐기물", "단순공사"]

    async def test_returns_empty_list(self):
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = []

        session = AsyncMock()
        session.execute.return_value = mock_result

        result = await self.service.get_active_keywords(session)
        assert result == []


class TestCreateKeyword:
    """키워드 생성"""

    def setup_method(self):
        self.service = KeywordService()

    async def test_create_new_keyword(self):
        mock_existing = MagicMock()
        mock_existing.scalar_one_or_none.return_value = None

        session = AsyncMock()
        session.execute.return_value = mock_existing

        result = await self.service.create_keyword(session, "새키워드")
        session.add.assert_called_once()
        session.commit.assert_called_once()

    async def test_duplicate_keyword_raises(self):
        mock_existing = MagicMock()
        mock_existing.scalar_one_or_none.return_value = MagicMock()

        session = AsyncMock()
        session.execute.return_value = mock_existing

        with pytest.raises(ValueError, match="already exists"):
            await self.service.create_keyword(session, "폐기물")

    async def test_strips_whitespace(self):
        mock_existing = MagicMock()
        mock_existing.scalar_one_or_none.return_value = None

        session = AsyncMock()
        session.execute.return_value = mock_existing

        await self.service.create_keyword(session, "  공백키워드  ")
        session.add.assert_called_once()


class TestDeleteKeyword:
    """키워드 삭제"""

    def setup_method(self):
        self.service = KeywordService()

    async def test_delete_existing(self):
        mock_result = MagicMock()
        mock_result.rowcount = 1

        session = AsyncMock()
        session.execute.return_value = mock_result

        result = await self.service.delete_keyword(session, "폐기물")
        assert result is True

    async def test_delete_nonexistent(self):
        mock_result = MagicMock()
        mock_result.rowcount = 0

        session = AsyncMock()
        session.execute.return_value = mock_result

        result = await self.service.delete_keyword(session, "없는키워드")
        assert result is False


class TestGetAllKeywords:
    """전체 키워드 조회"""

    def setup_method(self):
        self.service = KeywordService()

    async def test_returns_all(self):
        mock_keywords = [MagicMock(), MagicMock()]
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = mock_keywords

        session = AsyncMock()
        session.execute.return_value = mock_result

        result = await self.service.get_all_keywords(session)
        assert len(result) == 2
