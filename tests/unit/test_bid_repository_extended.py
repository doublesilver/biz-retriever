"""
BidRepository 확장 테스트
- get_by_url
- get_multi_with_filters (keyword, agency)
- get_hard_matches (region, performance, license)
- update_processing_status
"""

from datetime import datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import BidAnnouncement
from app.db.repositories.bid_repository import BidRepository


class TestGetByUrl:
    """get_by_url 테스트"""

    async def test_found(self, test_db: AsyncSession):
        bid = BidAnnouncement(
            title="URL 테스트",
            content="내용",
            agency="기관",
            url="https://unique-url.com/1",
            source="G2B",
            posted_at=datetime.utcnow(),
        )
        test_db.add(bid)
        await test_db.commit()

        repo = BidRepository(test_db)
        result = await repo.get_by_url("https://unique-url.com/1")
        assert result is not None
        assert result.title == "URL 테스트"

    async def test_not_found(self, test_db: AsyncSession):
        repo = BidRepository(test_db)
        result = await repo.get_by_url("https://nonexistent.com")
        assert result is None


class TestGetMultiWithFilters:
    """get_multi_with_filters 테스트"""

    async def test_no_filters(self, test_db: AsyncSession):
        for i in range(3):
            test_db.add(
                BidAnnouncement(
                    title=f"공고 {i}",
                    content=f"내용 {i}",
                    agency=f"기관 {i}",
                    url=f"https://example.com/{i}",
                    source="G2B",
                    posted_at=datetime.utcnow(),
                )
            )
        await test_db.commit()

        repo = BidRepository(test_db)
        result = await repo.get_multi_with_filters()
        assert len(result) == 3

    async def test_keyword_filter(self, test_db: AsyncSession):
        test_db.add(
            BidAnnouncement(
                title="구내식당 위탁운영",
                content="식당 운영",
                agency="서울시",
                url="https://example.com/a",
                source="G2B",
                posted_at=datetime.utcnow(),
            )
        )
        test_db.add(
            BidAnnouncement(
                title="건축 공사",
                content="건설",
                agency="경기도",
                url="https://example.com/b",
                source="G2B",
                posted_at=datetime.utcnow(),
            )
        )
        await test_db.commit()

        repo = BidRepository(test_db)
        result = await repo.get_multi_with_filters(keyword="구내식당")
        assert len(result) == 1
        assert result[0].title == "구내식당 위탁운영"

    async def test_agency_filter(self, test_db: AsyncSession):
        test_db.add(
            BidAnnouncement(
                title="공고1",
                content="내용",
                agency="서울대병원",
                url="https://example.com/c",
                source="G2B",
                posted_at=datetime.utcnow(),
            )
        )
        test_db.add(
            BidAnnouncement(
                title="공고2",
                content="내용",
                agency="경기도청",
                url="https://example.com/d",
                source="G2B",
                posted_at=datetime.utcnow(),
            )
        )
        await test_db.commit()

        repo = BidRepository(test_db)
        result = await repo.get_multi_with_filters(agency="서울대병원")
        assert len(result) == 1

    async def test_pagination(self, test_db: AsyncSession):
        for i in range(10):
            test_db.add(
                BidAnnouncement(
                    title=f"공고 {i}",
                    content=f"내용 {i}",
                    agency="기관",
                    url=f"https://example.com/page/{i}",
                    source="G2B",
                    posted_at=datetime.utcnow(),
                )
            )
        await test_db.commit()

        repo = BidRepository(test_db)
        result = await repo.get_multi_with_filters(skip=0, limit=3)
        assert len(result) == 3


class TestGetHardMatches:
    """get_hard_matches 테스트"""

    async def test_no_filters(self, test_db: AsyncSession):
        test_db.add(
            BidAnnouncement(
                title="공고",
                content="내용",
                agency="기관",
                url="https://example.com/hard/1",
                source="G2B",
                posted_at=datetime.utcnow(),
                min_performance=0,
            )
        )
        await test_db.commit()

        repo = BidRepository(test_db)
        result = await repo.get_hard_matches()
        # user has no licenses, bid has no license_requirements -> match
        assert len(result) >= 1

    async def test_performance_filter(self, test_db: AsyncSession):
        test_db.add(
            BidAnnouncement(
                title="높은 실적 요구",
                content="내용",
                agency="기관",
                url="https://example.com/hard/2",
                source="G2B",
                posted_at=datetime.utcnow(),
                min_performance=1000000,
            )
        )
        test_db.add(
            BidAnnouncement(
                title="낮은 실적 요구",
                content="내용",
                agency="기관",
                url="https://example.com/hard/3",
                source="G2B",
                posted_at=datetime.utcnow(),
                min_performance=100,
            )
        )
        await test_db.commit()

        repo = BidRepository(test_db)
        # user_performance = 500 -> 100 통과, 1000000 실패
        result = await repo.get_hard_matches(user_performance_amount=500)
        titles = [b.title for b in result]
        assert "낮은 실적 요구" in titles
        assert "높은 실적 요구" not in titles

    async def test_license_filter(self, test_db: AsyncSession):
        bid_with_reqs = BidAnnouncement(
            title="면허 필요",
            content="내용",
            agency="기관",
            url="https://example.com/hard/4",
            source="G2B",
            posted_at=datetime.utcnow(),
            min_performance=0,
            license_requirements=["조경공사업", "건축공사업"],
        )
        bid_no_reqs = BidAnnouncement(
            title="면허 불필요",
            content="내용",
            agency="기관",
            url="https://example.com/hard/5",
            source="G2B",
            posted_at=datetime.utcnow(),
            min_performance=0,
            license_requirements=[],
        )
        test_db.add(bid_with_reqs)
        test_db.add(bid_no_reqs)
        await test_db.commit()

        repo = BidRepository(test_db)

        # 면허 보유: 조경공사업만 -> bid_with_reqs 불매칭
        result = await repo.get_hard_matches(
            user_licenses=["조경공사업"],
            user_performance_amount=9999999,
        )
        titles = [b.title for b in result]
        assert "면허 불필요" in titles
        assert "면허 필요" not in titles

        # 면허 보유: 둘 다 -> bid_with_reqs 매칭
        result2 = await repo.get_hard_matches(
            user_licenses=["조경공사업", "건축공사업"],
            user_performance_amount=9999999,
        )
        titles2 = [b.title for b in result2]
        assert "면허 필요" in titles2
        assert "면허 불필요" in titles2

    async def test_no_licenses_user(self, test_db: AsyncSession):
        """면허 없는 사용자 -> 면허 요건 없는 공고만"""
        bid_with_reqs = BidAnnouncement(
            title="면허 필요",
            content="내용",
            agency="기관",
            url="https://example.com/hard/6",
            source="G2B",
            posted_at=datetime.utcnow(),
            min_performance=0,
            license_requirements=["조경공사업"],
        )
        bid_no_reqs = BidAnnouncement(
            title="누구나 가능",
            content="내용",
            agency="기관",
            url="https://example.com/hard/7",
            source="G2B",
            posted_at=datetime.utcnow(),
            min_performance=0,
            license_requirements=[],
        )
        test_db.add(bid_with_reqs)
        test_db.add(bid_no_reqs)
        await test_db.commit()

        repo = BidRepository(test_db)
        result = await repo.get_hard_matches(user_licenses=[], user_performance_amount=9999999)
        titles = [b.title for b in result]
        assert "누구나 가능" in titles
        assert "면허 필요" not in titles


class TestUpdateProcessingStatus:
    """update_processing_status 테스트"""

    async def test_update_existing(self, test_db: AsyncSession):
        bid = BidAnnouncement(
            title="처리 테스트",
            content="내용",
            agency="기관",
            url="https://example.com/proc/1",
            source="G2B",
            posted_at=datetime.utcnow(),
            processed=False,
        )
        test_db.add(bid)
        await test_db.commit()
        await test_db.refresh(bid)

        repo = BidRepository(test_db)
        result = await repo.update_processing_status(bid.id, True)
        assert result is not None
        assert result.processed is True

    async def test_update_nonexistent(self, test_db: AsyncSession):
        repo = BidRepository(test_db)
        result = await repo.update_processing_status(99999, True)
        assert result is None
