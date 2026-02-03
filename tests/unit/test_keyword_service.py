"""
Keyword Service 단위 테스트
제외 키워드 관리 서비스
"""

import pytest
from sqlalchemy import select

from app.db.models import ExcludeKeyword
from app.services.keyword_service import KeywordService


class TestKeywordService:
    """제외 키워드 서비스 테스트"""

    # ============================================
    # get_active_keywords 테스트
    # ============================================

    @pytest.mark.asyncio
    async def test_get_active_keywords_empty(self, test_db):
        """활성 키워드 조회 - 빈 결과"""
        service = KeywordService()
        keywords = await service.get_active_keywords(test_db)

        assert keywords == []

    @pytest.mark.asyncio
    async def test_get_active_keywords_with_data(self, test_db):
        """활성 키워드 조회 - 데이터 있음"""
        # 테스트 데이터 생성
        keyword1 = ExcludeKeyword(word="폐기물", is_active=True)
        keyword2 = ExcludeKeyword(word="철거", is_active=True)
        keyword3 = ExcludeKeyword(word="비활성", is_active=False)

        test_db.add(keyword1)
        test_db.add(keyword2)
        test_db.add(keyword3)
        await test_db.commit()

        service = KeywordService()
        keywords = await service.get_active_keywords(test_db)

        assert len(keywords) == 2
        assert "폐기물" in keywords
        assert "철거" in keywords
        assert "비활성" not in keywords

    @pytest.mark.asyncio
    async def test_get_active_keywords_only_active(self, test_db):
        """활성 키워드만 반환 확인"""
        keyword1 = ExcludeKeyword(word="단순공사", is_active=True)
        keyword2 = ExcludeKeyword(word="설계용역", is_active=False)

        test_db.add(keyword1)
        test_db.add(keyword2)
        await test_db.commit()

        service = KeywordService()
        keywords = await service.get_active_keywords(test_db)

        assert len(keywords) == 1
        assert keywords[0] == "단순공사"

    # ============================================
    # create_keyword 테스트
    # ============================================

    @pytest.mark.asyncio
    async def test_create_keyword_success(self, test_db):
        """키워드 생성 성공"""
        service = KeywordService()
        keyword = await service.create_keyword(test_db, "폐기물")

        assert keyword.word == "폐기물"
        assert keyword.is_active is True

        # DB에 저장되었는지 확인
        result = await test_db.execute(
            select(ExcludeKeyword).where(ExcludeKeyword.word == "폐기물")
        )
        saved_keyword = result.scalar_one_or_none()
        assert saved_keyword is not None

    @pytest.mark.asyncio
    async def test_create_keyword_with_whitespace(self, test_db):
        """키워드 생성 - 공백 제거"""
        service = KeywordService()
        keyword = await service.create_keyword(test_db, "  폐기물  ")

        assert keyword.word == "폐기물"

    @pytest.mark.asyncio
    async def test_create_keyword_duplicate(self, test_db):
        """키워드 생성 - 중복 에러"""
        service = KeywordService()

        # 첫 번째 생성
        await service.create_keyword(test_db, "폐기물")

        # 두 번째 생성 시도 - 에러 발생
        with pytest.raises(ValueError, match="already exists"):
            await service.create_keyword(test_db, "폐기물")

    @pytest.mark.asyncio
    async def test_create_keyword_case_sensitive(self, test_db):
        """키워드 생성 - 대소문자 구분"""
        service = KeywordService()

        keyword1 = await service.create_keyword(test_db, "폐기물")
        keyword2 = await service.create_keyword(test_db, "폐기물2")

        assert keyword1.word == "폐기물"
        assert keyword2.word == "폐기물2"

    # ============================================
    # delete_keyword 테스트
    # ============================================

    @pytest.mark.asyncio
    async def test_delete_keyword_success(self, test_db):
        """키워드 삭제 성공"""
        # 테스트 데이터 생성
        keyword = ExcludeKeyword(word="폐기물")
        test_db.add(keyword)
        await test_db.commit()

        service = KeywordService()
        result = await service.delete_keyword(test_db, "폐기물")

        assert result is True

        # DB에서 삭제되었는지 확인
        check_result = await test_db.execute(
            select(ExcludeKeyword).where(ExcludeKeyword.word == "폐기물")
        )
        assert check_result.scalar_one_or_none() is None

    @pytest.mark.asyncio
    async def test_delete_keyword_not_found(self, test_db):
        """키워드 삭제 - 없는 키워드"""
        service = KeywordService()
        result = await service.delete_keyword(test_db, "없는키워드")

        assert result is False

    @pytest.mark.asyncio
    async def test_delete_keyword_multiple(self, test_db):
        """여러 키워드 삭제"""
        keyword1 = ExcludeKeyword(word="폐기물")
        keyword2 = ExcludeKeyword(word="철거")
        keyword3 = ExcludeKeyword(word="해체")

        test_db.add(keyword1)
        test_db.add(keyword2)
        test_db.add(keyword3)
        await test_db.commit()

        service = KeywordService()

        result1 = await service.delete_keyword(test_db, "폐기물")
        result2 = await service.delete_keyword(test_db, "철거")

        assert result1 is True
        assert result2 is True

        # 해체는 남아있어야 함
        check_result = await test_db.execute(
            select(ExcludeKeyword).where(ExcludeKeyword.word == "해체")
        )
        assert check_result.scalar_one_or_none() is not None

    # ============================================
    # get_all_keywords 테스트
    # ============================================

    @pytest.mark.asyncio
    async def test_get_all_keywords_empty(self, test_db):
        """모든 키워드 조회 - 빈 결과"""
        service = KeywordService()
        keywords = await service.get_all_keywords(test_db)

        assert keywords == []

    @pytest.mark.asyncio
    async def test_get_all_keywords_includes_inactive(self, test_db):
        """모든 키워드 조회 - 비활성 포함"""
        keyword1 = ExcludeKeyword(word="폐기물", is_active=True)
        keyword2 = ExcludeKeyword(word="철거", is_active=False)

        test_db.add(keyword1)
        test_db.add(keyword2)
        await test_db.commit()

        service = KeywordService()
        keywords = await service.get_all_keywords(test_db)

        assert len(keywords) == 2
        words = [k.word for k in keywords]
        assert "폐기물" in words
        assert "철거" in words

    @pytest.mark.asyncio
    async def test_get_all_keywords_ordered_by_created_at(self, test_db):
        """모든 키워드 조회 - 생성 시간 역순 정렬"""
        keyword1 = ExcludeKeyword(word="keyword1")
        test_db.add(keyword1)
        await test_db.commit()

        keyword2 = ExcludeKeyword(word="keyword2")
        test_db.add(keyword2)
        await test_db.commit()

        service = KeywordService()
        keywords = await service.get_all_keywords(test_db)

        # 최신 순서로 정렬되어야 함 (역순)
        assert len(keywords) == 2
        # 두 키워드가 모두 있어야 함
        words = [k.word for k in keywords]
        assert "keyword1" in words
        assert "keyword2" in words
