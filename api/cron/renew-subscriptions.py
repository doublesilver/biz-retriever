"""
Vercel Cron Job: Subscription Renewal
Daily at 02:00 UTC (11:00 KST)

Automatically renews expired subscriptions using saved billing keys.
Max 3 retry attempts, then auto-cancel with email notification.
"""
import asyncio
import os
import sys
import time
from datetime import datetime, timedelta

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../.."))

from fastapi import Header, Request
from fastapi.responses import JSONResponse
from sqlalchemy import select

from app.core.logging import logger
from app.db.models import Subscription, User
from app.db.session import AsyncSessionLocal
from app.services.email_service import email_service
from app.services.payment_service import payment_service

# Vercel Cron Secret (보안)
CRON_SECRET = os.getenv("CRON_SECRET", "default-secret-change-me")

# Vercel timeout safety margin (50s of 60s max)
TIMEOUT_SECONDS = 50


async def handler(request: Request, authorization: str = Header(None)):
    """
    구독 갱신 Cron Job
    
    Vercel Cron에서 호출됨:
    - Schedule: "0 2 * * *" (02:00 UTC = 11:00 KST)
    - Authorization: Bearer <CRON_SECRET>
    
    Logic:
    1. Find expired subscriptions with billing_key (auto-renewal enabled)
    2. Attempt renewal charge
    3. Success: Extend expires_at by 30 days, reset retry_count
    4. Failure: Increment retry_count
    5. If retry_count >= 3: Cancel subscription, send email
    6. Send email notifications for all outcomes
    """
    # Verify Cron Secret
    if not authorization or authorization != f"Bearer {CRON_SECRET}":
        return JSONResponse(status_code=401, content={"detail": "Unauthorized"})

    start_time = time.time()
    stats = {
        "processed": 0,
        "renewed": 0,
        "failed": 0,
        "canceled": 0,
        "errors": [],
    }

    try:
        async with AsyncSessionLocal() as session:
            # ============================================
            # 1. Find expired subscriptions with billing_key
            # ============================================
            # NOTE: This query assumes billing_key, expires_at, and retry_count fields exist
            # If they don't exist yet, a migration is needed to add:
            # - billing_key: String (Tosspayments billing key for auto-renewal)
            # - expires_at: DateTime (subscription expiration date)
            # - retry_count: Integer (number of failed renewal attempts, default 0)
            
            try:
                stmt = (
                    select(Subscription)
                    .where(
                        Subscription.expires_at < datetime.utcnow(),
                        Subscription.billing_key.isnot(None),
                        Subscription.is_active == True,
                    )
                    .limit(100)  # Process max 100 per run (safety)
                )
                result = await session.execute(stmt)
                expired_subscriptions = result.scalars().all()
                
                logger.info(
                    f"Found {len(expired_subscriptions)} expired subscriptions to renew"
                )
                
            except Exception as e:
                # Graceful fallback if billing_key/expires_at/retry_count don't exist yet
                logger.error(f"Query failed - billing fields may not exist yet: {e}")
                return JSONResponse(
                    status_code=500,
                    content={
                        "success": False,
                        "error": "Subscription billing fields not configured. Migration needed.",
                        "message": str(e),
                        "stats": stats,
                    },
                )

            if not expired_subscriptions:
                return JSONResponse(
                    status_code=200,
                    content={
                        "success": True,
                        "message": "No expired subscriptions to renew",
                        "stats": stats,
                    },
                )

            # ============================================
            # 2. Process each expired subscription
            # ============================================
            for subscription in expired_subscriptions:
                # Check timeout (safety margin)
                elapsed = time.time() - start_time
                if elapsed > TIMEOUT_SECONDS:
                    logger.warning(
                        f"Timeout approaching ({elapsed:.1f}s), stopping processing"
                    )
                    stats["errors"].append(
                        f"Timeout after processing {stats['processed']} subscriptions"
                    )
                    break

                stats["processed"] += 1

                try:
                    # Get user info for email
                    user_stmt = select(User).where(User.id == subscription.user_id)
                    user_result = await session.execute(user_stmt)
                    user = user_result.scalar_one_or_none()

                    if not user:
                        logger.error(
                            f"User not found for subscription {subscription.id}"
                        )
                        continue

                    # ============================================
                    # 3. Attempt renewal charge
                    # ============================================
                    amount = payment_service.get_plan_amount(subscription.plan_name)
                    order_id = payment_service.generate_order_id(
                        user.id, subscription.plan_name
                    )

                    try:
                        # Charge billing key
                        # NOTE: charge_billing_key() needs to be implemented in payment_service
                        # For now, using a mock implementation
                        charge_result = await charge_billing_key_mock(
                            billing_key=subscription.billing_key,
                            amount=amount,
                            order_id=order_id,
                            customer_name=user.email,
                            plan_name=subscription.plan_name,
                        )

                        # ============================================
                        # 4. Success: Extend subscription
                        # ============================================
                        subscription.expires_at = datetime.utcnow() + timedelta(days=30)
                        subscription.next_billing_date = subscription.expires_at
                        subscription.retry_count = 0  # Reset retry counter
                        await session.commit()

                        stats["renewed"] += 1
                        logger.info(
                            f"Subscription renewed: user={user.id}, "
                            f"plan={subscription.plan_name}, amount={amount}원"
                        )

                        # Send success email
                        if email_service.is_configured():
                            await send_renewal_success_email(
                                user=user,
                                subscription=subscription,
                                amount=amount,
                                next_billing_date=subscription.expires_at,
                            )

                    except Exception as charge_error:
                        # ============================================
                        # 5. Failure: Increment retry_count
                        # ============================================
                        subscription.retry_count = (
                            getattr(subscription, "retry_count", 0) + 1
                        )
                        await session.commit()

                        stats["failed"] += 1
                        logger.error(
                            f"Renewal failed for subscription {subscription.id}: "
                            f"{charge_error}, retry_count={subscription.retry_count}"
                        )

                        # ============================================
                        # 6. Max retries: Cancel subscription
                        # ============================================
                        if subscription.retry_count >= 3:
                            subscription.is_active = False
                            await session.commit()

                            stats["canceled"] += 1
                            logger.warning(
                                f"Subscription canceled after 3 failures: "
                                f"user={user.id}, plan={subscription.plan_name}"
                            )

                            # Send cancellation email
                            if email_service.is_configured():
                                await send_renewal_canceled_email(
                                    user=user, subscription=subscription
                                )
                        else:
                            # Send failure email (retry pending)
                            if email_service.is_configured():
                                await send_renewal_failure_email(
                                    user=user,
                                    subscription=subscription,
                                    retry_count=subscription.retry_count,
                                )

                except Exception as e:
                    logger.error(
                        f"Error processing subscription {subscription.id}: {e}",
                        exc_info=True,
                    )
                    stats["errors"].append(f"Subscription {subscription.id}: {str(e)[:50]}")
                    continue

        elapsed_total = time.time() - start_time
        logger.info(
            f"Subscription renewal completed: "
            f"{stats['renewed']} renewed, {stats['failed']} failed, "
            f"{stats['canceled']} canceled, {elapsed_total:.1f}초 소요"
        )

        return JSONResponse(
            status_code=200,
            content={
                "success": True,
                "message": "Subscription renewal completed",
                "stats": stats,
                "elapsed_seconds": round(elapsed_total, 2),
            },
        )

    except Exception as e:
        logger.error(f"Subscription renewal job failed: {e}", exc_info=True)
        return JSONResponse(
            status_code=500,
            content={
                "success": False,
                "error": str(e),
                "stats": stats,
            },
        )


# ============================================
# Helper Functions
# ============================================


async def charge_billing_key_mock(
    billing_key: str,
    amount: int,
    order_id: str,
    customer_name: str,
    plan_name: str,
) -> dict:
    """
    Mock implementation of billing key charge
    
    TODO: This should be moved to app/services/payment_service.py as a proper method:
    async def charge_billing_key(self, billing_key: str, amount: int, order_id: str, ...) -> dict
    
    Tosspayments Billing Key API:
    POST https://api.tosspayments.com/v1/billing/{billingKey}
    Authorization: Basic {base64(secret_key:)}
    Body: {
        "amount": 10000,
        "orderId": "BIZ-123-BASIC-20260203",
        "orderName": "Biz-Retriever Basic 구독",
        "customerEmail": "user@example.com",
        "customerName": "홍길동"
    }
    """
    if not payment_service.is_configured():
        raise ValueError("Tosspayments not configured")

    import base64
    import httpx

    url = f"https://api.tosspayments.com/v1/billing/{billing_key}"
    headers = {
        "Authorization": payment_service.auth_header,
        "Content-Type": "application/json",
    }
    payload = {
        "amount": amount,
        "orderId": order_id,
        "orderName": f"Biz-Retriever {plan_name.capitalize()} 구독",
        "customerEmail": customer_name,
        "customerName": customer_name,
    }

    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                url, headers=headers, json=payload, timeout=10.0
            )

            if response.status_code == 200:
                result = response.json()
                logger.info(
                    f"Billing key charged: order_id={order_id}, amount={amount}원"
                )
                return result
            else:
                error_data = response.json()
                logger.error(f"Billing key charge failed: {error_data}")
                raise Exception(
                    f"Charge failed: {error_data.get('message', 'Unknown error')}"
                )

    except httpx.TimeoutException:
        logger.error("Billing key charge timeout")
        raise Exception("결제 요청 시간 초과")
    except Exception as e:
        logger.error(f"Billing key charge error: {str(e)}", exc_info=True)
        raise


async def send_renewal_success_email(
    user, subscription, amount: int, next_billing_date: datetime
):
    """Send email notification for successful renewal"""
    subject = "✅ 구독이 갱신되었습니다 - Biz-Retriever"
    
    html_content = f"""
<!DOCTYPE html>
<html lang="ko">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>구독 갱신 완료</title>
</head>
<body style="margin: 0; padding: 0; font-family: 'Malgun Gothic', Arial, sans-serif; background-color: #f5f5f5;">
    <table role="presentation" cellspacing="0" cellpadding="0" border="0" width="100%">
        <tr>
            <td style="padding: 40px 20px;">
                <table role="presentation" cellspacing="0" cellpadding="0" border="0" width="100%" style="max-width: 600px; margin: 0 auto; background-color: #ffffff; border-radius: 8px;">
                    <tr>
                        <td style="padding: 30px; text-align: center; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); border-radius: 8px 8px 0 0;">
                            <h1 style="margin: 0; color: #ffffff; font-size: 24px;">✅ 구독 갱신 완료</h1>
                        </td>
                    </tr>
                    <tr>
                        <td style="padding: 30px;">
                            <p style="margin: 0; font-size: 16px; color: #333333;">안녕하세요,</p>
                            <p style="margin: 15px 0; font-size: 14px; color: #666666; line-height: 1.6;">
                                Biz-Retriever <strong>{subscription.plan_name.capitalize()}</strong> 플랜 구독이 성공적으로 갱신되었습니다.
                            </p>
                            <div style="margin: 20px 0; padding: 20px; background-color: #f8f9fa; border-radius: 6px;">
                                <p style="margin: 0 0 10px; font-size: 14px; color: #666666;">
                                    <strong>결제 금액:</strong> <span style="color: #28a745; font-weight: 600;">{amount:,}원</span>
                                </p>
                                <p style="margin: 0; font-size: 14px; color: #666666;">
                                    <strong>다음 결제일:</strong> {next_billing_date.strftime('%Y년 %m월 %d일')}
                                </p>
                            </div>
                            <p style="margin: 15px 0 0; font-size: 14px; color: #666666;">
                                계속해서 Biz-Retriever를 이용해주셔서 감사합니다!
                            </p>
                        </td>
                    </tr>
                    <tr>
                        <td style="padding: 20px 30px; background-color: #f8f9fa; border-radius: 0 0 8px 8px; text-align: center;">
                            <p style="margin: 0; font-size: 12px; color: #999999;">© 2026 Biz-Retriever. All rights reserved.</p>
                        </td>
                    </tr>
                </table>
            </td>
        </tr>
    </table>
</body>
</html>
"""

    plain_content = f"""
안녕하세요,

Biz-Retriever {subscription.plan_name.capitalize()} 플랜 구독이 성공적으로 갱신되었습니다.

결제 금액: {amount:,}원
다음 결제일: {next_billing_date.strftime('%Y년 %m월 %d일')}

계속해서 Biz-Retriever를 이용해주셔서 감사합니다!

© 2026 Biz-Retriever
"""

    try:
        await email_service.send_email(
            to_email=user.email,
            subject=subject,
            html_content=html_content,
            plain_content=plain_content,
        )
        logger.info(f"Renewal success email sent to {user.email}")
    except Exception as e:
        logger.error(f"Failed to send renewal success email: {e}")


async def send_renewal_failure_email(user, subscription, retry_count: int):
    """Send email notification for failed renewal (retry pending)"""
    subject = "⚠️ 구독 결제 실패 - 카드를 확인해주세요"
    
    html_content = f"""
<!DOCTYPE html>
<html lang="ko">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0;">
    <title>구독 결제 실패</title>
</head>
<body style="margin: 0; padding: 0; font-family: 'Malgun Gothic', Arial, sans-serif; background-color: #f5f5f5;">
    <table role="presentation" cellspacing="0" cellpadding="0" border="0" width="100%">
        <tr>
            <td style="padding: 40px 20px;">
                <table role="presentation" cellspacing="0" cellpadding="0" border="0" width="100%" style="max-width: 600px; margin: 0 auto; background-color: #ffffff; border-radius: 8px;">
                    <tr>
                        <td style="padding: 30px; text-align: center; background: linear-gradient(135deg, #ff6b6b 0%, #ee5a6f 100%); border-radius: 8px 8px 0 0;">
                            <h1 style="margin: 0; color: #ffffff; font-size: 24px;">⚠️ 구독 결제 실패</h1>
                        </td>
                    </tr>
                    <tr>
                        <td style="padding: 30px;">
                            <p style="margin: 0; font-size: 16px; color: #333333;">안녕하세요,</p>
                            <p style="margin: 15px 0; font-size: 14px; color: #666666; line-height: 1.6;">
                                Biz-Retriever <strong>{subscription.plan_name.capitalize()}</strong> 플랜 구독 결제에 실패했습니다.
                            </p>
                            <div style="margin: 20px 0; padding: 20px; background-color: #fff3cd; border-left: 4px solid #ffc107; border-radius: 6px;">
                                <p style="margin: 0 0 10px; font-size: 14px; color: #856404;">
                                    <strong>시도 횟수:</strong> {retry_count} / 3
                                </p>
                                <p style="margin: 0; font-size: 13px; color: #856404;">
                                    3회 실패 시 구독이 자동으로 취소됩니다.
                                </p>
                            </div>
                            <p style="margin: 15px 0; font-size: 14px; color: #666666;">
                                결제 수단을 확인하시고, 필요 시 새로운 카드를 등록해주세요.
                            </p>
                            <div style="text-align: center; margin: 25px 0;">
                                <a href="{os.getenv('FRONTEND_URL', 'https://biz-retriever.vercel.app')}/profile.html" 
                                   style="display: inline-block; padding: 12px 30px; background-color: #667eea; color: #ffffff; text-decoration: none; border-radius: 6px; font-size: 14px; font-weight: 600;">
                                    결제 수단 관리
                                </a>
                            </div>
                        </td>
                    </tr>
                    <tr>
                        <td style="padding: 20px 30px; background-color: #f8f9fa; border-radius: 0 0 8px 8px; text-align: center;">
                            <p style="margin: 0; font-size: 12px; color: #999999;">© 2026 Biz-Retriever. All rights reserved.</p>
                        </td>
                    </tr>
                </table>
            </td>
        </tr>
    </table>
</body>
</html>
"""

    plain_content = f"""
안녕하세요,

Biz-Retriever {subscription.plan_name.capitalize()} 플랜 구독 결제에 실패했습니다.

시도 횟수: {retry_count} / 3
⚠️ 3회 실패 시 구독이 자동으로 취소됩니다.

결제 수단을 확인하시고, 필요 시 새로운 카드를 등록해주세요.

결제 수단 관리: {os.getenv('FRONTEND_URL', 'https://biz-retriever.vercel.app')}/profile.html

© 2026 Biz-Retriever
"""

    try:
        await email_service.send_email(
            to_email=user.email,
            subject=subject,
            html_content=html_content,
            plain_content=plain_content,
        )
        logger.info(f"Renewal failure email sent to {user.email}")
    except Exception as e:
        logger.error(f"Failed to send renewal failure email: {e}")


async def send_renewal_canceled_email(user, subscription):
    """Send email notification for canceled subscription (after 3 failures)"""
    subject = "❌ 구독이 취소되었습니다 - Biz-Retriever"
    
    html_content = f"""
<!DOCTYPE html>
<html lang="ko">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>구독 취소</title>
</head>
<body style="margin: 0; padding: 0; font-family: 'Malgun Gothic', Arial, sans-serif; background-color: #f5f5f5;">
    <table role="presentation" cellspacing="0" cellpadding="0" border="0" width="100%">
        <tr>
            <td style="padding: 40px 20px;">
                <table role="presentation" cellspacing="0" cellpadding="0" border="0" width="100%" style="max-width: 600px; margin: 0 auto; background-color: #ffffff; border-radius: 8px;">
                    <tr>
                        <td style="padding: 30px; text-align: center; background: linear-gradient(135deg, #6c757d 0%, #495057 100%); border-radius: 8px 8px 0 0;">
                            <h1 style="margin: 0; color: #ffffff; font-size: 24px;">❌ 구독 취소</h1>
                        </td>
                    </tr>
                    <tr>
                        <td style="padding: 30px;">
                            <p style="margin: 0; font-size: 16px; color: #333333;">안녕하세요,</p>
                            <p style="margin: 15px 0; font-size: 14px; color: #666666; line-height: 1.6;">
                                결제 실패가 3회 연속 발생하여 Biz-Retriever <strong>{subscription.plan_name.capitalize()}</strong> 플랜 구독이 자동으로 취소되었습니다.
                            </p>
                            <div style="margin: 20px 0; padding: 20px; background-color: #f8f9fa; border-radius: 6px;">
                                <p style="margin: 0; font-size: 14px; color: #666666;">
                                    <strong>취소 사유:</strong> 결제 실패 (3회)
                                </p>
                            </div>
                            <p style="margin: 15px 0; font-size: 14px; color: #666666;">
                                서비스를 다시 이용하시려면 결제 수단을 업데이트하고 구독을 재개해주세요.
                            </p>
                            <div style="text-align: center; margin: 25px 0;">
                                <a href="{os.getenv('FRONTEND_URL', 'https://biz-retriever.vercel.app')}/profile.html" 
                                   style="display: inline-block; padding: 12px 30px; background-color: #667eea; color: #ffffff; text-decoration: none; border-radius: 6px; font-size: 14px; font-weight: 600;">
                                    구독 재개하기
                                </a>
                            </div>
                        </td>
                    </tr>
                    <tr>
                        <td style="padding: 20px 30px; background-color: #f8f9fa; border-radius: 0 0 8px 8px; text-align: center;">
                            <p style="margin: 0; font-size: 12px; color: #999999;">© 2026 Biz-Retriever. All rights reserved.</p>
                        </td>
                    </tr>
                </table>
            </td>
        </tr>
    </table>
</body>
</html>
"""

    plain_content = f"""
안녕하세요,

결제 실패가 3회 연속 발생하여 Biz-Retriever {subscription.plan_name.capitalize()} 플랜 구독이 자동으로 취소되었습니다.

취소 사유: 결제 실패 (3회)

서비스를 다시 이용하시려면 결제 수단을 업데이트하고 구독을 재개해주세요.

구독 재개: {os.getenv('FRONTEND_URL', 'https://biz-retriever.vercel.app')}/profile.html

© 2026 Biz-Retriever
"""

    try:
        await email_service.send_email(
            to_email=user.email,
            subject=subject,
            html_content=html_content,
            plain_content=plain_content,
        )
        logger.info(f"Renewal canceled email sent to {user.email}")
    except Exception as e:
        logger.error(f"Failed to send renewal canceled email: {e}")
