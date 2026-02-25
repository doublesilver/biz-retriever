import asyncio
import sys
import os

# Add project root to path
sys.path.append(os.getcwd())

from app.db.session import AsyncSessionLocal
from app.services.constraint_service import constraint_service
from app.services.matching_service import matching_service
from app.db.models import BidAnnouncement, UserProfile, UserLicense, UserPerformance
from app.core.logging import logger
from datetime import datetime

async def test_phase3_logic():
    async with AsyncSessionLocal() as session:
        logger.info("Phase 3 Logic Test Started")
        
        # 1. Mock User Profile 생성 (In-Memory or DB)
        # DB에 테스트용 유저가 필요함.
        # 기존 User가 있다고 가정하고 Profile 생성
        # 실제 DB 조작 없이 객체로만 테스트 가능? -> Yes logic test
        
        mock_profile = UserProfile(
            id=999,
            location_code="11", # 서울
            company_name="테스트건설",
            address="서울시 강남구"
        )
        mock_p_license = UserLicense(license_name="정보통신공사업")
        mock_profile.licenses = [mock_p_license]
        
        mock_p_perf = UserPerformance(project_name="A프로젝트", amount=500_000_000) # 5억
        mock_profile.performances = [mock_p_perf]
        
        logger.info(f"Mock Profile Created: {mock_profile.company_name}, Region: {mock_profile.location_code}")

        # 2. Mock Bid Announcement (Constraint Extraction Test)
        # Case A: Match
        bid_match = BidAnnouncement(
            id=1,
            title="서울 정보통신공사 입찰",
            content="본 공사는 서울특별시 관내 공사로서, 정보통신공사업 면허를 보유하고 최근 3억 이상 실적이 있는 업체만 참여 가능합니다.",
            agency="서울특별시",
            posted_at=datetime.now(),
            url="http://test.com/1"
        )
        
        logger.info("--- Test Case A (Should Match) ---")
        extracted_a = await constraint_service.extract_constraints(bid_match)
        logger.info(f"Extracted Constraints A: {extracted_a}")
        
        # Manually apply extraction result to bid object (simulating DB save)
        bid_match.region_code = extracted_a.get("region_code")
        bid_match.license_requirements = extracted_a.get("license_requirements")
        bid_match.min_performance = extracted_a.get("min_performance")
        
        match_result_a = matching_service.check_hard_match(mock_profile, bid_match)
        logger.info(f"Match Result A: {match_result_a}")
        
        # Case B: No Match (Region)
        bid_fail_region = BidAnnouncement(
            id=2,
            title="부산 도로개설공사",
            content="부산광역시 관내 업체만 참여 가능.",
            agency="부산광역시",
            posted_at=datetime.now(),
            url="http://test.com/2"
        )
        
        logger.info("\n--- Test Case B (Fail Region) ---")
        extracted_b = await constraint_service.extract_constraints(bid_fail_region)
        logger.info(f"Extracted Constraints B: {extracted_b}")
        
        bid_fail_region.region_code = extracted_b.get("region_code")
        match_result_b = matching_service.check_hard_match(mock_profile, bid_fail_region)
        logger.info(f"Match Result B: {match_result_b}")

        # Case C: No Match (Performance)
        bid_fail_perf = BidAnnouncement(
            id=3,
            title="대형 소프트웨어 구축",
            content="최근 10억 이상의 단일 실적 필요.",
            agency="조달청",
            posted_at=datetime.now(),
            url="http://test.com/3"
        )
        
        logger.info("\n--- Test Case C (Fail Performance) ---")
        extracted_c = await constraint_service.extract_constraints(bid_fail_perf)
        logger.info(f"Extracted Constraints C: {extracted_c}")
        
        bid_fail_perf.min_performance = extracted_c.get("min_performance")
        match_result_c = matching_service.check_hard_match(mock_profile, bid_fail_perf)
        logger.info(f"Match Result C: {match_result_c}")


if __name__ == "__main__":
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
        
    asyncio.run(test_phase3_logic())
