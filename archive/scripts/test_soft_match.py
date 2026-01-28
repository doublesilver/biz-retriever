import asyncio
import sys
import os

# Add project root to path
sys.path.append(os.getcwd())

from app.services.matching_service import matching_service
from app.db.models import BidAnnouncement, UserProfile, UserLicense, UserPerformance
from app.core.logging import logger
from datetime import datetime

async def test_soft_match_logic():
    logger.info("Soft Match Logic Test Started")
    
    # 1. User Profile Setup (Phase 3 Spec)
    # User likes "CCTV", "Parking" in Seoul
    mock_profile = UserProfile(
        id=999,
        location_code="11", # Seoul
        company_name="Smart Enc",
        keywords=["CCTV", "주차장", "관제"]
    )
    
    # 2. Test Cases
    
    # Case A: Perfect Match (Seoul + Title Keyword)
    # Expected: 20 (Title) + 10 (Region) + 5 (Importance 1) = 35
    bid_a = BidAnnouncement(
        id=1,
        title="서울시 CCTV 설치 공사",
        content="본 공사는...",
        region_code="11",
        importance_score=1
    )
    
    # Case B: Content Match + Region Mismatch
    # Expected: 5 (Content) + 0 (Region) + 15 (Importance 3) = 20
    bid_b = BidAnnouncement(
        id=2,
        title="부산 통합 관제 시스템",
        content="주차장 관제 설비 포함", # '주차장', '관제' match? -> '관제' match, '주차장' match. 
        # Logic: 5 points per keyword in content.
        # keywords: CCTV, 주차장, 관제
        # content: ...주차장...관제... => 2 matches?
        region_code="26", # Busan
        importance_score=3
    )
    
    # Case C: No Match
    # Expected: 5 (Importance 1) = 5
    bid_c = BidAnnouncement(
        id=3,
        title="대전 도로 포장 공사",
        content="아스팔트 포장",
        region_code="30",
        importance_score=1
    )
    
    logger.info("--- Test Case A (Perfect Match) ---")
    result_a = matching_service.calculate_soft_match(mock_profile, bid_a)
    logger.info(f"Score: {result_a['score']}")
    logger.info(f"Breakdown: {result_a['breakdown']}")
    
    logger.info("\n--- Test Case B (Content Match) ---")
    result_b = matching_service.calculate_soft_match(mock_profile, bid_b)
    logger.info(f"Score: {result_b['score']}")
    logger.info(f"Breakdown: {result_b['breakdown']}")

    logger.info("\n--- Test Case C (No Match) ---")
    result_c = matching_service.calculate_soft_match(mock_profile, bid_c)
    logger.info(f"Score: {result_c['score']}")
    logger.info(f"Breakdown: {result_c['breakdown']}")

    # Verification Logic
    assert result_a['score'] >= 30, "Case A score too low"
    assert result_b['score'] >= 15, "Case B score too low"
    assert result_c['score'] < 10, "Case C score too high"
    
    print("\n[SUCCESS] Soft Match Logic Verification Passed!")

if __name__ == "__main__":
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
        
    asyncio.run(test_soft_match_logic())
