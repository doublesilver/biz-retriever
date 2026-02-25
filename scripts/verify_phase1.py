"""
Phase 1 크롤러 검증 스크립트
G2B 크롤러와 Slack 알림이 정상 작동하는지 테스트합니다.
"""
import asyncio
from app.services.crawler_service import g2b_crawler
from app.services.notification_service import slack_notification
from app.db.models import BidAnnouncement
from datetime import datetime


async def test_crawler():
    """크롤러 기능 테스트"""
    print("=" * 50)
    print("1. G2B 크롤러 테스트")
    print("=" * 50)
    
    try:
        announcements = await g2b_crawler.fetch_new_announcements()
        print(f"✅ 크롤링 성공: {len(announcements)}건 수집")
        
        if announcements:
            print("\n📋 샘플 공고:")
            for i, announcement in enumerate(announcements[:3], 1):
                print(f"\n{i}. {announcement['title']}")
                print(f"   기관: {announcement.get('agency', '미확인')}")
                print(f"   매칭 키워드: {announcement.get('keywords_matched', [])}")
                print(f"   첨부파일 추출 여부: {'✅ 성공' if announcement.get('attachment_content') else '❌ 실패/없음'}")
                if announcement.get('attachment_content'):
                    cleaned_text = announcement['attachment_content'][:50].replace('\n', ' ')
                    print(f"   추출 텍스트 (앞 50자): {cleaned_text}...")
                print(f"   중요도: {g2b_crawler.calculate_importance_score(announcement)}/3")
        else:
            print("⚠️  필터링 조건에 맞는 공고가 없습니다.")
    
    except Exception as e:
        print(f"❌ 크롤러 에러: {e}")
    
    finally:
        await g2b_crawler.close()


async def test_slack_notification():
    """Slack 알림 기능 테스트"""
    print("\n" + "=" * 50)
    print("2. Slack 알림 테스트")
    print("=" * 50)
    
    # 테스트용 더미 공고 생성
    test_announcement = BidAnnouncement(
        id=999,
        title="[테스트] 서울대병원 구내식당 위탁운영",
        content="테스트 공고입니다.",
        agency="서울대학교병원",
        posted_at=datetime.now(),
        url="https://test.com/announcement/999",
        source="G2B",
        deadline=datetime(2026, 2, 15, 17, 0),
        estimated_price=150000000,
        importance_score=3,
        keywords_matched=["구내식당", "위탁운영"],
        is_notified=False,
        crawled_at=datetime.now()
    )
    
    try:
        success = await slack_notification.send_bid_notification(test_announcement)
        if success:
            print("✅ Slack 알림 전송 성공")
            print("   Slack 채널을 확인해주세요!")
        else:
            print("❌ Slack 알림 전송 실패")
            print("   SLACK_WEBHOOK_URL을 확인해주세요.")
    
    except Exception as e:
        print(f"❌ Slack 에러: {e}")


async def main():
    """메인 실행 함수"""
    print("\n🐕 Biz-Retriever Phase 1 검증 스크립트\n")
    
    # 1. 크롤러 테스트
    await test_crawler()
    
    # 2. Slack 알림 테스트
    await test_slack_notification()
    
    print("\n" + "=" * 50)
    print("검증 완료")
    print("=" * 50)
    print("\n다음 단계:")
    print("1. G2B API 키 발급: https://www.data.go.kr/")
    print("2. Slack Webhook URL 생성: Slack App > Incoming Webhooks")
    print("3. .env 파일에 실제 키 입력")
    print("4. Celery Worker 실행: celery -A app.worker.celery_app worker --loglevel=info")
    print("5. Celery Beat 실행: celery -A app.worker.celery_app beat --loglevel=info")


if __name__ == "__main__":
    asyncio.run(main())
