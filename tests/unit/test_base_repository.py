"""
BaseRepository CRUD 테스트
- get, get_multi, create, update, remove
"""

from datetime import datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import BidAnnouncement
from app.db.repositories.bid_repository import BidRepository


class TestBaseRepositoryGet:
    """get 메서드 테스트"""

    async def test_get_existing(self, test_db: AsyncSession):
        bid = BidAnnouncement(
            title="Base get 테스트",
            content="내용",
            agency="기관",
            url="https://base-get.com/1",
            source="G2B",
            posted_at=datetime.utcnow(),
        )
        test_db.add(bid)
        await test_db.commit()
        await test_db.refresh(bid)

        repo = BidRepository(test_db)
        result = await repo.get(bid.id)
        assert result is not None
        assert result.title == "Base get 테스트"

    async def test_get_nonexistent(self, test_db: AsyncSession):
        repo = BidRepository(test_db)
        result = await repo.get(99999)
        assert result is None


class TestBaseRepositoryGetMulti:
    """get_multi 메서드 테스트"""

    async def test_get_multi(self, test_db: AsyncSession):
        for i in range(5):
            test_db.add(
                BidAnnouncement(
                    title=f"Multi {i}",
                    content=f"내용 {i}",
                    agency="기관",
                    url=f"https://base-multi.com/{i}",
                    source="G2B",
                    posted_at=datetime.utcnow(),
                )
            )
        await test_db.commit()

        repo = BidRepository(test_db)
        result = await repo.get_multi(skip=0, limit=3)
        assert len(result) == 3

    async def test_get_multi_skip(self, test_db: AsyncSession):
        for i in range(5):
            test_db.add(
                BidAnnouncement(
                    title=f"Skip {i}",
                    content=f"내용 {i}",
                    agency="기관",
                    url=f"https://base-skip.com/{i}",
                    source="G2B",
                    posted_at=datetime.utcnow(),
                )
            )
        await test_db.commit()

        repo = BidRepository(test_db)
        result = await repo.get_multi(skip=3, limit=100)
        assert len(result) == 2


class TestBaseRepositoryUpdate:
    """update 메서드 테스트"""

    async def test_update_with_dict(self, test_db: AsyncSession):
        bid = BidAnnouncement(
            title="업데이트 전",
            content="내용",
            agency="기관",
            url="https://base-update.com/1",
            source="G2B",
            posted_at=datetime.utcnow(),
        )
        test_db.add(bid)
        await test_db.commit()
        await test_db.refresh(bid)

        repo = BidRepository(test_db)
        result = await repo.update(bid, {"title": "업데이트 후"})
        assert result.title == "업데이트 후"


class TestBaseRepositoryRemove:
    """remove 메서드 테스트"""

    async def test_remove_existing(self, test_db: AsyncSession):
        bid = BidAnnouncement(
            title="삭제 대상",
            content="내용",
            agency="기관",
            url="https://base-remove.com/1",
            source="G2B",
            posted_at=datetime.utcnow(),
        )
        test_db.add(bid)
        await test_db.commit()
        await test_db.refresh(bid)

        repo = BidRepository(test_db)
        removed = await repo.remove(bid.id)
        assert removed is not None

        check = await repo.get(bid.id)
        assert check is None

    async def test_remove_nonexistent(self, test_db: AsyncSession):
        repo = BidRepository(test_db)
        result = await repo.remove(99999)
        assert result is None
