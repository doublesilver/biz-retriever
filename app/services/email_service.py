"""
Email Notification Service using SendGrid
Phase 8: Email notification system for bid alerts
"""

import os

try:
    from sendgrid import SendGridAPIClient
    from sendgrid.helpers.mail import Content, Email, Mail, Personalization, To

    SENDGRID_AVAILABLE = True
except ImportError:
    SENDGRID_AVAILABLE = False
    SendGridAPIClient = None
    Mail = None

from app.core.config import settings
from app.core.logging import logger


class EmailService:
    """
    SendGrid email service for sending notifications
    """

    def __init__(self):
        if not SENDGRID_AVAILABLE:
            self.client = None
            logger.warning("EmailService: SendGrid package not installed. Email notifications disabled.")
            return

        self.api_key = os.getenv(
            "SENDGRID_API_KEY",
            (settings.SENDGRID_API_KEY if hasattr(settings, "SENDGRID_API_KEY") else None),
        )
        self.from_email = os.getenv("SENDGRID_FROM_EMAIL", "noreply@biz-retriever.com")
        self.from_name = os.getenv("SENDGRID_FROM_NAME", "Biz-Retriever")

        if self.api_key and self.api_key.startswith("SG."):
            self.client = SendGridAPIClient(self.api_key)
            logger.info("EmailService: SendGrid API initialized")
        else:
            self.client = None
            logger.warning("EmailService: SendGrid API key not configured. Email notifications disabled.")

    def is_configured(self) -> bool:
        """Check if SendGrid is properly configured"""
        return self.client is not None

    async def send_email(
        self,
        to_email: str,
        subject: str,
        html_content: str,
        plain_content: str | None = None,
    ) -> bool:
        """
        Send a single email

        Args:
            to_email: Recipient email address
            subject: Email subject
            html_content: HTML email body
            plain_content: Plain text fallback (optional)

        Returns:
            bool: True if sent successfully, False otherwise
        """
        if not self.is_configured():
            logger.error("SendGrid not configured. Cannot send email.")
            return False

        try:
            message = Mail(
                from_email=Email(self.from_email, self.from_name),
                to_emails=To(to_email),
                subject=subject,
                html_content=Content("text/html", html_content),
            )

            # Add plain text content if provided
            if plain_content:
                message.content = [
                    Content("text/plain", plain_content),
                    Content("text/html", html_content),
                ]

            response = self.client.send(message)

            if response.status_code in [200, 202]:
                logger.info(f"Email sent successfully to {to_email}: {subject}")
                return True
            else:
                logger.error(f"Failed to send email. Status: {response.status_code}, Body: {response.body}")
                return False

        except Exception as e:
            logger.error(f"Error sending email to {to_email}: {str(e)}", exc_info=True)
            return False

    async def send_bulk_email(
        self,
        recipients: list[str],
        subject: str,
        html_content: str,
        plain_content: str | None = None,
    ) -> int:
        """
        Send email to multiple recipients

        Args:
            recipients: List of email addresses
            subject: Email subject
            html_content: HTML email body
            plain_content: Plain text fallback (optional)

        Returns:
            int: Number of successfully sent emails
        """
        if not self.is_configured():
            logger.error("SendGrid not configured. Cannot send bulk email.")
            return 0

        success_count = 0

        for recipient in recipients:
            if await self.send_email(recipient, subject, html_content, plain_content):
                success_count += 1

        logger.info(f"Bulk email: {success_count}/{len(recipients)} sent successfully")
        return success_count

    def render_bid_alert_email(
        self,
        user_name: str,
        bid_title: str,
        bid_agency: str,
        bid_deadline: str,
        bid_price: str,
        bid_url: str,
        bid_summary: str | None = None,
        keywords: list[str] | None = None,
    ) -> tuple[str, str]:
        """
        Render bid alert email template

        Returns:
            tuple: (html_content, plain_content)
        """
        # Plain text version
        plain_text = f"""
안녕하세요 {user_name}님,

새로운 맞춤 공고가 등록되었습니다!

📋 공고 제목: {bid_title}
🏢 발주기관: {bid_agency}
📅 마감일: {bid_deadline}
💰 추정가: {bid_price}
"""

        if bid_summary:
            plain_text += f"\n🤖 AI 요약:\n{bid_summary}\n"

        if keywords:
            plain_text += f"\n🏷️ 매칭 키워드: {', '.join(keywords)}\n"

        plain_text += f"\n🔗 자세히 보기: {bid_url}\n\n감사합니다.\nBiz-Retriever 팀"

        # HTML version
        html_content = f"""
<!DOCTYPE html>
<html lang="ko">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>새로운 맞춤 공고 알림</title>
</head>
<body style="margin: 0; padding: 0; font-family: 'Malgun Gothic', '맑은 고딕', Arial, sans-serif; background-color: #f5f5f5;">
    <table role="presentation" cellspacing="0" cellpadding="0" border="0" width="100%" style="background-color: #f5f5f5;">
        <tr>
            <td style="padding: 40px 20px;">
                <table role="presentation" cellspacing="0" cellpadding="0" border="0" width="100%" style="max-width: 600px; margin: 0 auto; background-color: #ffffff; border-radius: 8px; box-shadow: 0 2px 8px rgba(0,0,0,0.1);">
                    
                    <!-- Header -->
                    <tr>
                        <td style="padding: 30px 30px 20px; text-align: center; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); border-radius: 8px 8px 0 0;">
                            <h1 style="margin: 0; color: #ffffff; font-size: 24px; font-weight: 600;">
                                🐕 Biz-Retriever
                            </h1>
                            <p style="margin: 10px 0 0; color: #ffffff; font-size: 14px;">새로운 맞춤 공고 알림</p>
                        </td>
                    </tr>
                    
                    <!-- Greeting -->
                    <tr>
                        <td style="padding: 30px 30px 20px;">
                            <p style="margin: 0; font-size: 16px; color: #333333;">안녕하세요 <strong>{user_name}</strong>님,</p>
                            <p style="margin: 10px 0 0; font-size: 14px; color: #666666;">새로운 맞춤 공고가 등록되었습니다!</p>
                        </td>
                    </tr>
                    
                    <!-- Bid Info Card -->
                    <tr>
                        <td style="padding: 0 30px 20px;">
                            <table role="presentation" cellspacing="0" cellpadding="0" border="0" width="100%" style="background-color: #f8f9fa; border-radius: 8px; border-left: 4px solid #667eea;">
                                <tr>
                                    <td style="padding: 20px;">
                                        <h2 style="margin: 0 0 15px; font-size: 18px; color: #333333; font-weight: 600;">
                                            📋 {bid_title}
                                        </h2>
                                        
                                        <table role="presentation" cellspacing="0" cellpadding="0" border="0" width="100%">
                                            <tr>
                                                <td style="padding: 5px 0; font-size: 14px; color: #666666;">
                                                    <strong>🏢 발주기관:</strong> {bid_agency}
                                                </td>
                                            </tr>
                                            <tr>
                                                <td style="padding: 5px 0; font-size: 14px; color: #666666;">
                                                    <strong>📅 마감일:</strong> <span style="color: #dc3545; font-weight: 600;">{bid_deadline}</span>
                                                </td>
                                            </tr>
                                            <tr>
                                                <td style="padding: 5px 0; font-size: 14px; color: #666666;">
                                                    <strong>💰 추정가:</strong> <span style="color: #28a745; font-weight: 600;">{bid_price}</span>
                                                </td>
                                            </tr>
                                        </table>
        """

        # AI Summary section
        if bid_summary:
            html_content += f"""
                                        <div style="margin-top: 15px; padding: 15px; background-color: #e7f3ff; border-radius: 6px; border-left: 3px solid #0066cc;">
                                            <p style="margin: 0; font-size: 13px; color: #0066cc; font-weight: 600;">🤖 AI 요약</p>
                                            <p style="margin: 8px 0 0; font-size: 14px; color: #333333; line-height: 1.6;">{bid_summary}</p>
                                        </div>
            """

        # Keywords section
        if keywords:
            keyword_badges = " ".join(
                [
                    f'<span style="display: inline-block; padding: 4px 10px; margin: 2px; background-color: #667eea; color: #ffffff; border-radius: 12px; font-size: 12px;">{kw}</span>'
                    for kw in keywords
                ]
            )
            html_content += f"""
                                        <div style="margin-top: 15px;">
                                            <p style="margin: 0 0 8px; font-size: 13px; color: #666666; font-weight: 600;">🏷️ 매칭 키워드</p>
                                            <div>{keyword_badges}</div>
                                        </div>
            """

        html_content += f"""
                                    </td>
                                </tr>
                            </table>
                        </td>
                    </tr>
                    
                    <!-- CTA Button -->
                    <tr>
                        <td style="padding: 0 30px 30px; text-align: center;">
                            <a href="{bid_url}" style="display: inline-block; padding: 14px 32px; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: #ffffff; text-decoration: none; border-radius: 6px; font-size: 16px; font-weight: 600; box-shadow: 0 4px 12px rgba(102, 126, 234, 0.3);">
                                🔗 자세히 보기
                            </a>
                        </td>
                    </tr>
                    
                    <!-- Footer -->
                    <tr>
                        <td style="padding: 20px 30px; background-color: #f8f9fa; border-radius: 0 0 8px 8px; text-align: center;">
                            <p style="margin: 0; font-size: 12px; color: #999999;">
                                이 메일은 Biz-Retriever에서 자동으로 발송되었습니다.<br>
                                알림 설정을 변경하려면 <a href="{settings.FRONTEND_URL}/profile.html" style="color: #667eea; text-decoration: none;">프로필 페이지</a>에서 관리하세요.
                            </p>
                            <p style="margin: 15px 0 0; font-size: 12px; color: #999999;">
                                © 2026 Biz-Retriever. All rights reserved.
                            </p>
                        </td>
                    </tr>
                    
                </table>
            </td>
        </tr>
    </table>
</body>
</html>
"""

        return html_content, plain_text

    async def send_bid_alert(self, to_email: str, user_name: str, bid_data: dict) -> bool:
        """
        Send bid alert email to user

        Args:
            to_email: User email address
            user_name: User name for personalization
            bid_data: Dictionary containing bid information

        Returns:
            bool: True if sent successfully
        """
        html_content, plain_content = self.render_bid_alert_email(
            user_name=user_name,
            bid_title=bid_data.get("title", "제목 없음"),
            bid_agency=bid_data.get("agency", "기관 미정"),
            bid_deadline=bid_data.get("deadline", "미정"),
            bid_price=bid_data.get("estimated_price", "미정"),
            bid_url=bid_data.get("url", settings.FRONTEND_URL),
            bid_summary=bid_data.get("ai_summary"),
            keywords=bid_data.get("keywords_matched"),
        )

        subject = f"🔔 새로운 맞춤 공고: {bid_data.get('title', '공고')}"

        return await self.send_email(to_email, subject, html_content, plain_content)

    async def send_subscription_notification(
        self,
        to_email: str,
        subject: str,
        html_content: str,
    ) -> bool:
        """
        구독 관련 이메일 전송 (갱신, 결제 실패, 만료 임박, 해지 확인).

        Args:
            to_email: 수신자 이메일
            subject: 제목
            html_content: HTML 본문

        Returns:
            전송 성공 여부
        """
        return await self.send_email(to_email, subject, html_content)

    async def send_invoice_receipt(
        self,
        to_email: str,
        user_name: str,
        invoice_number: str,
        plan_name: str,
        amount: int,
        billing_period: str,
    ) -> bool:
        """
        인보이스 영수증 이메일 전송.

        Args:
            to_email: 수신자 이메일
            user_name: 사용자 이름
            invoice_number: 인보이스 번호
            plan_name: 플랜 이름
            amount: 결제 금액
            billing_period: 결제 기간 (예: "2026.02.24 ~ 2026.03.26")
        """
        subject = f"Biz-Retriever 결제 영수증 ({invoice_number})"

        html_content = f"""
<!DOCTYPE html>
<html lang="ko">
<head><meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0"></head>
<body style="margin:0;padding:0;font-family:'Malgun Gothic',Arial,sans-serif;background:#f5f5f5;">
<table role="presentation" width="100%" style="background:#f5f5f5;">
<tr><td style="padding:40px 20px;">
<table role="presentation" width="100%" style="max-width:600px;margin:0 auto;background:#fff;border-radius:8px;box-shadow:0 2px 8px rgba(0,0,0,0.1);">
<tr><td style="padding:30px;text-align:center;background:linear-gradient(135deg,#667eea 0%,#764ba2 100%);border-radius:8px 8px 0 0;">
<h1 style="margin:0;color:#fff;font-size:22px;">Biz-Retriever</h1>
<p style="margin:8px 0 0;color:#fff;font-size:14px;">결제 영수증</p>
</td></tr>
<tr><td style="padding:30px;">
<p style="font-size:16px;color:#333;">안녕하세요 <strong>{user_name}</strong>님,</p>
<p style="font-size:14px;color:#666;">결제가 정상적으로 처리되었습니다.</p>

<table style="width:100%;background:#f8f9fa;border-radius:8px;margin:20px 0;border-collapse:collapse;">
<tr><td style="padding:12px 15px;font-size:14px;color:#666;border-bottom:1px solid #e9ecef;">인보이스 번호</td>
<td style="padding:12px 15px;font-size:14px;color:#333;font-weight:600;text-align:right;border-bottom:1px solid #e9ecef;">{invoice_number}</td></tr>
<tr><td style="padding:12px 15px;font-size:14px;color:#666;border-bottom:1px solid #e9ecef;">플랜</td>
<td style="padding:12px 15px;font-size:14px;color:#333;font-weight:600;text-align:right;border-bottom:1px solid #e9ecef;">{plan_name.upper()}</td></tr>
<tr><td style="padding:12px 15px;font-size:14px;color:#666;border-bottom:1px solid #e9ecef;">결제 기간</td>
<td style="padding:12px 15px;font-size:14px;color:#333;text-align:right;border-bottom:1px solid #e9ecef;">{billing_period}</td></tr>
<tr><td style="padding:12px 15px;font-size:14px;color:#666;">결제 금액</td>
<td style="padding:12px 15px;font-size:18px;color:#28a745;font-weight:700;text-align:right;">{amount:,}원</td></tr>
</table>

<p style="font-size:13px;color:#999;">이 영수증은 세금 계산서를 대체하지 않습니다. 세금 계산서가 필요하시면 고객센터로 문의해 주세요.</p>
</td></tr>
<tr><td style="padding:20px 30px;background:#f8f9fa;border-radius:0 0 8px 8px;text-align:center;">
<p style="margin:0;font-size:12px;color:#999;">
Biz-Retriever | <a href="{settings.FRONTEND_URL}" style="color:#667eea;">biz-retriever.vercel.app</a>
</p></td></tr>
</table>
</td></tr></table>
</body></html>"""

        return await self.send_email(to_email, subject, html_content)


# Singleton instance
email_service = EmailService()
