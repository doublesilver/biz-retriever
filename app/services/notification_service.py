"""
Slack 알림 서비스
입찰 공고를 Slack 채널로 실시간 전송합니다.
"""
from typing import Dict, List
import httpx
from app.core.config import settings
from app.core.logging import logger
from app.db.models import BidAnnouncement


class SlackNotificationService:
    """
    Slack Webhook을 통한 알림 서비스
    """
    
    def __init__(self):
        self.webhook_url = settings.SLACK_WEBHOOK_URL
        self.channel = settings.SLACK_CHANNEL
    
    async def send_bid_notification(self, announcement: BidAnnouncement) -> bool:
        """
        입찰 공고를 Slack으로 전송
        
        Args:
            announcement: BidAnnouncement 모델 인스턴스
        
        Returns:
            성공 여부
        """
        message = self._format_message(announcement)
        
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.post(
                    self.webhook_url,
                    json=message
                )
                response.raise_for_status()
                return True
        except Exception as e:
            logger.error(f"Slack 알림 전송 실패: {e}", exc_info=True)
            return False
    
    def _format_message(self, announcement: BidAnnouncement) -> Dict:
        """
        Slack 메시지 포맷 생성
        
        Args:
            announcement: BidAnnouncement 인스턴스
        
        Returns:
            Slack Webhook 메시지 딕셔너리
        """
        # 중요도 별 표시
        stars = "⭐" * announcement.importance_score
        
        # 마감일 표시
        deadline_text = "미정"
        if announcement.deadline:
            deadline_text = announcement.deadline.strftime("%Y-%m-%d %H:%M")
        
        # 추정가 표시
        price_text = "미공개"
        if announcement.estimated_price:
            price_text = f"{int(announcement.estimated_price):,}원"
        
        # 키워드 표시
        keywords_text = ", ".join(announcement.keywords_matched or [])
        
        # 메시지 본문 구성
        text = f"""
🐕 *[신규 공고 알림]*
━━━━━━━━━━━━━━━━
📌 *제목*: {announcement.title}
🏛 *기관*: {announcement.agency or "미확인"}
📅 *마감*: {deadline_text}
💰 *추정가*: {price_text}
🔗 <{announcement.url}|상세보기>

{stars} *중요도*: {announcement.importance_score}/3
🎯 *매칭 키워드*: {keywords_text}
        """.strip()
        
        return {
            "channel": self.channel,
            "username": "Biz-Retriever Bot",
            "icon_emoji": ":dog:",
            "text": text,
            "mrkdwn": True
        }
    
    async def send_digest(self, announcements: List[BidAnnouncement]) -> bool:
        """
        여러 공고를 한 번에 요약하여 전송 (모닝 브리핑용)
        
        Args:
            announcements: BidAnnouncement 리스트
        
        Returns:
            성공 여부
        """
        if not announcements:
            return False
        
        # 중요도 순으로 정렬
        sorted_announcements = sorted(
            announcements,
            key=lambda x: x.importance_score,
            reverse=True
        )
        
        # 상위 10개만
        top_announcements = sorted_announcements[:10]
        
        text = "🌅 *[모닝 브리핑] 밤사이 새로운 입찰 공고*\n━━━━━━━━━━━━━━━━\n\n"
        
        for i, announcement in enumerate(top_announcements, 1):
            stars = "⭐" * announcement.importance_score
            text += f"{i}. {stars} {announcement.title}\n"
            text += f"   🏛 {announcement.agency or '미확인'} | "
            text += f"📅 {announcement.deadline.strftime('%m/%d') if announcement.deadline else '미정'}\n"
            text += f"   🔗 <{announcement.url}|상세보기>\n\n"
        
        text += f"*총 {len(announcements)}건의 새 공고가 있습니다.*"
        
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.post(
                    self.webhook_url,
                    json={
                        "channel": self.channel,
                        "username": "Biz-Retriever Bot",
                        "icon_emoji": ":sunrise:",
                        "text": text,
                        "mrkdwn": True
                    }
                )
                response.raise_for_status()
                return True
        except Exception as e:
            logger.error(f"Slack 다이제스트 전송 실패: {e}", exc_info=True)
            return False


# 싱글톤 인스턴스
slack_notification = SlackNotificationService()
