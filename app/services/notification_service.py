
import httpx
import logging
from typing import Optional, List
from app.db.models import User, BidAnnouncement, UserProfile
from app.services.email_service import email_service
from app.core.logging import logger as app_logger

logger = logging.getLogger(__name__)

class NotificationService:
    @staticmethod
    async def send_slack_message(webhook_url: str, message: str) -> bool:
        """
        Send a message to a Slack Webhook URL.
        """
        if not webhook_url:
            return False

        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(webhook_url, json={"text": message})
                if response.status_code == 200:
                    return True
                else:
                    logger.error(f"Slack Notification Failed: {response.text}")
                    return False
        except Exception as e:
            logger.error(f"Slack Notification Error: {e}")
            return False

    @classmethod
    async def notify_bid_match(cls, user: User, bid: BidAnnouncement, matched_keywords: List[str]):
        """
        Notify user about a matched bid.
        """
        if not user.full_profile:
            return

        profile: UserProfile = user.full_profile

        # Slack Notification
        if profile.is_slack_enabled and profile.slack_webhook_url:
            keywords_str = ", ".join(matched_keywords)
            message = (
                f"🔔 *키워드 매칭 알림*\n"
                f"*공고명:* {bid.title}\n"
                f"*키워드:* `{keywords_str}`\n"
                f"*마감일:* {bid.deadline}\n"
                f"*추정가:* {bid.estimated_price:,.0f}원\n"
                f"<{bid.url}|공고 보기>"
            )
            await cls.send_slack_message(profile.slack_webhook_url, message)

        # Email Notification
        if profile.is_email_enabled and user.email:
            try:
                # Format bid data for email template
                bid_data = {
                    "title": bid.title,
                    "agency": bid.agency,
                    "deadline": bid.deadline.strftime("%Y-%m-%d %H:%M") if bid.deadline else "미정",
                    "estimated_price": f"{bid.estimated_price:,.0f}원" if bid.estimated_price else "미정",
                    "url": bid.url,
                    "ai_summary": bid.ai_summary,
                    "keywords_matched": matched_keywords
                }
                
                # Get user name from profile or email
                user_name = profile.company_name or user.email.split('@')[0]
                
                # Send email alert
                success = await email_service.send_bid_alert(
                    to_email=user.email,
                    user_name=user_name,
                    bid_data=bid_data
                )
                
                if success:
                    app_logger.info(f"Email notification sent to {user.email} for bid {bid.id}")
                else:
                    app_logger.warning(f"Failed to send email notification to {user.email}")
                    
            except Exception as e:
                app_logger.error(f"Error sending email notification: {str(e)}", exc_info=True)
