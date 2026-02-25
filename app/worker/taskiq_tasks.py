"""
Taskiq Background Tasks (Async-Native)

Celery tasks를 Taskiq로 변환 - async/await 네이티브 지원으로 더 간결하고 효율적
"""

import json
from datetime import datetime, timedelta

from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.core.logging import logger
from app.core.websocket import manager
from app.db.models import (
    BidAnnouncement,
    ExcludeKeyword,
    PaymentHistory,
    Subscription,
    User,
    UserKeyword,
)
from app.db.session import AsyncSessionLocal
from app.services.crawler_service import G2BCrawlerService
from app.services.email_service import email_service
from app.services.invoice_service import invoice_service
from app.services.notification_service import NotificationService
from app.services.payment_service import payment_service
from app.services.rag_service import RAGService
from app.services.subscription_service import subscription_service
from app.worker.taskiq_app import broker

# ============================================
# G2B 크롤링 작업 (하루 3회)
# ============================================


@broker.task(
    task_name="crawl_g2b_bids",
    schedule=[
        {"cron": "0 8 * * *"},  # 매일 08:00
        {"cron": "0 12 * * *"},  # 매일 12:00
        {"cron": "0 18 * * *"},  # 매일 18:00
    ],
)
async def crawl_g2b_bids():
    """
    G2B 나라장터 크롤링 작업

    하루 3회 실행 (08:00, 12:00, 18:00)
    """
    logger.info("G2B 크롤링 작업 시작")

    async with AsyncSessionLocal() as session:
        # 1. 동적 키워드 조회
        stmt_exclude = select(ExcludeKeyword.word).where(
            ExcludeKeyword.is_active == True
        )
        result = await session.execute(stmt_exclude)
        dynamic_excludes = result.scalars().all()

        stmt_include = (
            select(UserKeyword.keyword)
            .where(UserKeyword.is_active == True, UserKeyword.category == "include")
            .distinct()
        )
        result = await session.execute(stmt_include)
        dynamic_includes = result.scalars().all()

        # 2. 크롤러 서비스 초기화
        crawler = G2BCrawlerService()

        exclude_keywords = list(
            set(crawler.DEFAULT_EXCLUDE_KEYWORDS + list(dynamic_excludes))
        )
        include_keywords = list(dynamic_includes) or (
            crawler.INCLUDE_KEYWORDS_CONCESSION + crawler.INCLUDE_KEYWORDS_FLOWER
        )

        # 3. 크롤링 실행 (Async)
        announcements = await crawler.fetch_new_announcements(
            exclude_keywords=exclude_keywords, include_keywords=include_keywords
        )

        logger.info(f"G2B 크롤링 완료: {len(announcements)}건")

        if not announcements:
            return

        # 4. 활성 사용자 조회 (알림용)
        stmt = (
            select(User)
            .where(User.is_active == True)
            .options(selectinload(User.full_profile), selectinload(User.keywords))
        )
        result = await session.execute(stmt)
        active_users = result.scalars().all()

        # 5. 중복 체크를 위한 기존 URL 일괄 조회 (N+1 쿼리 방지)
        announcement_urls = [a["url"] for a in announcements]
        stmt = select(BidAnnouncement.url).where(
            BidAnnouncement.url.in_(announcement_urls)
        )
        result = await session.execute(stmt)
        existing_urls = set(result.scalars().all())

        # 6. 공고 저장 및 알림
        for announcement_data in announcements:
            # 중복 체크 (메모리에서 조회)
            if announcement_data["url"] in existing_urls:
                continue

            # 중요도 계산
            importance_score = crawler.calculate_importance_score(announcement_data)
            announcement_data["importance_score"] = importance_score

            # DB 저장
            new_announcement = BidAnnouncement(**announcement_data)
            session.add(new_announcement)
            await session.commit()
            await session.refresh(new_announcement)

            # AI 분석 요청 (중요 공고만)
            if importance_score >= 2:
                await process_bid_analysis.kiq(new_announcement.id)

            # 사용자별 키워드 매칭 알림
            for user in active_users:
                if not user.keywords:
                    continue

                user_keywords = [
                    k.keyword
                    for k in user.keywords
                    if k.is_active and k.category == "include"
                ]

                if not user_keywords:
                    continue

                # 키워드 매칭 확인
                title = new_announcement.title
                content = new_announcement.content or ""
                full_text = f"{title} {content}"

                matched = [k for k in user_keywords if k in full_text]

                if matched:
                    await NotificationService.notify_bid_match(
                        user, new_announcement, matched
                    )
                    logger.info(
                        f"알림 발송: User {user.id} -> Bid {new_announcement.id} "
                        f"(키워드: {matched})"
                    )

            logger.info(
                f"새 공고 저장: {new_announcement.title} "
                f"(중요도: {importance_score})"
            )

            # WebSocket 브로드캐스트
            try:
                message = json.dumps(
                    {
                        "type": "new_bid",
                        "bid_id": new_announcement.id,
                        "title": new_announcement.title,
                        "agency": new_announcement.agency,
                    }
                )
                await manager.broadcast(message)
            except Exception as e:
                logger.error(f"WebSocket 브로드캐스트 실패: {e}")


# ============================================
# 모닝 브리핑 작업
# ============================================


@broker.task(
    task_name="send_morning_digest",
    schedule=[
        {"cron": "30 8 * * *"},  # 매일 08:30
    ],
)
async def send_morning_digest():
    """
    모닝 브리핑 전송

    밤사이(지난 12시간) 수집된 공고 요약
    """
    logger.info("모닝 브리핑 작업 시작")

    async with AsyncSessionLocal() as session:
        # 지난 12시간 공고 조회
        since = datetime.utcnow() - timedelta(hours=12)

        stmt = (
            select(BidAnnouncement)
            .where(BidAnnouncement.crawled_at >= since)
            .order_by(BidAnnouncement.importance_score.desc())
        )

        result = await session.execute(stmt)
        announcements = result.scalars().all()

        if announcements:
            # TODO: Slack 모닝 브리핑 전송
            # await NotificationService.send_digest(announcements)
            logger.info(f"모닝 브리핑 전송 완료: {len(announcements)}건")
        else:
            logger.info("모닝 브리핑: 새 공고 없음")


# ============================================
# AI 분석 작업
# ============================================


@broker.task(task_name="process_bid_analysis")
async def process_bid_analysis(bid_id: int):
    """
    공고 AI 분석 및 키워드 추출

    Args:
        bid_id: 분석할 공고 ID
    """
    logger.info(f"AI 분석 시작: Bid {bid_id}")

    async with AsyncSessionLocal() as session:
        # 1. 공고 조회
        stmt = select(BidAnnouncement).where(BidAnnouncement.id == bid_id)
        result = await session.execute(stmt)
        bid = result.scalar_one_or_none()

        if not bid:
            logger.error(f"분석 대상 공고 없음: {bid_id}")
            return

        # 2. AI 분석 (RAG Service)
        full_text = f"{bid.title} {bid.content}"

        rag = RAGService()
        analysis_result = await rag.analyze_bid(full_text)

        # 3. 결과 저장
        bid.ai_summary = analysis_result.get("summary")
        bid.ai_keywords = analysis_result.get("keywords")
        bid.region_code = analysis_result.get("region_code")
        bid.license_requirements = analysis_result.get("license_requirements")
        bid.min_performance = analysis_result.get("min_performance")
        bid.processed = True

        await session.commit()

        logger.info(f"AI 분석 완료: {bid.title}")


# ============================================
# 구독 갱신 배치 (매일 03:00)
# ============================================


@broker.task(
    task_name="process_subscription_renewals",
    schedule=[
        {"cron": "0 3 * * *"},  # 매일 03:00
    ],
)
async def process_subscription_renewals():
    """
    자동 갱신 결제 배치.

    next_billing_date가 오늘 이전인 활성 구독을 찾아
    빌링키로 자동 결제 후 구독을 갱신.
    """
    logger.info("구독 갱신 배치 시작")

    now = datetime.utcnow()
    renewed_count = 0
    failed_count = 0

    async with AsyncSessionLocal() as session:
        # 갱신 대상 조회: 활성 상태이고 next_billing_date가 지난 구독
        stmt = (
            select(Subscription)
            .where(
                Subscription.is_active == True,
                Subscription.status == "active",
                Subscription.next_billing_date <= now,
                Subscription.billing_key.isnot(None),
            )
            .options(selectinload(Subscription.user))
        )
        result = await session.execute(stmt)
        subscriptions = result.scalars().all()

        logger.info(f"갱신 대상 구독: {len(subscriptions)}건")

        for sub in subscriptions:
            try:
                amount = payment_service.get_plan_amount(sub.plan_name)
                if amount == 0:
                    continue

                order_id = payment_service.generate_order_id(
                    sub.user_id, sub.plan_name
                )
                idempotency_key = payment_service.generate_idempotency_key()

                # 빌링키 자동 결제
                charge_result = await payment_service.charge_billing_key(
                    billing_key=sub.billing_key,
                    amount=amount,
                    order_id=order_id,
                    order_name=f"Biz-Retriever {sub.plan_name.upper()} 플랜 갱신",
                    customer_email=sub.user.email if sub.user else "",
                    customer_name=(
                        sub.user.email.split("@")[0] if sub.user else ""
                    ),
                    idempotency_key=idempotency_key,
                )

                payment_key = charge_result.get("paymentKey", "")

                # 결제 이력
                history = PaymentHistory(
                    user_id=sub.user_id,
                    amount=amount,
                    currency="KRW",
                    status="paid",
                    payment_method="card",
                    transaction_id=payment_key,
                    idempotency_key=idempotency_key,
                    order_id=order_id,
                    payment_type="subscription_renew",
                )
                session.add(history)

                # 구독 갱신
                await subscription_service.handle_payment_success(sub, session)

                # 인보이스 생성
                invoice = await invoice_service.create_invoice(
                    subscription=sub,
                    amount=amount,
                    plan_name=sub.plan_name,
                    payment_key=payment_key,
                    description=f"{sub.plan_name.upper()} 플랜 자동 갱신",
                    db=session,
                )
                await invoice_service.mark_paid(invoice, payment_key)

                await session.commit()
                renewed_count += 1

                logger.info(
                    f"구독 갱신 성공: user={sub.user_id}, "
                    f"plan={sub.plan_name}, amount={amount}원"
                )

                # 갱신 완료 이메일
                if sub.user and email_service.is_configured():
                    await send_subscription_email.kiq(
                        sub.user_id,
                        "renewal_success",
                        sub.plan_name,
                        amount,
                    )

            except Exception as e:
                logger.error(
                    f"구독 갱신 실패: user={sub.user_id}, error={type(e).__name__}"
                )
                await session.rollback()

                # 결제 실패 처리
                await subscription_service.handle_payment_failure(sub, session)
                await session.commit()
                failed_count += 1

                # 결제 실패 알림 이메일
                if sub.user and email_service.is_configured():
                    await send_subscription_email.kiq(
                        sub.user_id,
                        "payment_failed",
                        sub.plan_name,
                        amount,
                    )

    logger.info(
        f"구독 갱신 배치 완료: 성공={renewed_count}, 실패={failed_count}"
    )


# ============================================
# 구독 만료 처리 배치 (매일 04:00)
# ============================================


@broker.task(
    task_name="process_subscription_expirations",
    schedule=[
        {"cron": "0 4 * * *"},  # 매일 04:00
    ],
)
async def process_subscription_expirations():
    """
    만료 대상 구독 처리 배치.

    - cancelled 상태이고 end_date가 지난 구독 → expired
    - past_due 상태이고 3회 이상 실패한 구독 → expired
    """
    logger.info("구독 만료 배치 시작")

    now = datetime.utcnow()
    expired_count = 0

    async with AsyncSessionLocal() as session:
        # 1. 해지 예약 후 기간 만료
        stmt = select(Subscription).where(
            Subscription.status == "cancelled",
            Subscription.end_date <= now,
        )
        result = await session.execute(stmt)
        cancelled_subs = result.scalars().all()

        for sub in cancelled_subs:
            await subscription_service.expire_subscription(sub, session)
            expired_count += 1
            logger.info(f"구독 만료 (해지): user={sub.user_id}")

        # 2. 결제 실패 3회 이상
        stmt = select(Subscription).where(
            Subscription.status == "past_due",
            Subscription.failed_payment_count >= 3,
        )
        result = await session.execute(stmt)
        past_due_subs = result.scalars().all()

        for sub in past_due_subs:
            await subscription_service.expire_subscription(sub, session)
            expired_count += 1
            logger.info(f"구독 만료 (결제 실패): user={sub.user_id}")

        await session.commit()

    logger.info(f"구독 만료 배치 완료: {expired_count}건 처리")


# ============================================
# 구독 알림 이메일 발송
# ============================================


@broker.task(task_name="send_subscription_email")
async def send_subscription_email(
    user_id: int,
    email_type: str,
    plan_name: str,
    amount: int = 0,
):
    """
    구독 관련 이메일 발송.

    email_type:
    - renewal_success: 자동 갱신 완료
    - payment_failed: 결제 실패
    - subscription_expiring: 만료 임박 알림
    - subscription_cancelled: 해지 확인
    """
    if not email_service.is_configured():
        return

    async with AsyncSessionLocal() as session:
        stmt = select(User).where(User.id == user_id)
        result = await session.execute(stmt)
        user = result.scalar_one_or_none()

        if not user:
            return

        user_name = user.email.split("@")[0]
        subject = ""
        html_content = ""

        if email_type == "renewal_success":
            subject = f"Biz-Retriever {plan_name.upper()} 플랜 갱신 완료"
            html_content = _render_renewal_email(user_name, plan_name, amount)

        elif email_type == "payment_failed":
            subject = "Biz-Retriever 결제 실패 알림"
            html_content = _render_payment_failed_email(
                user_name, plan_name, amount
            )

        elif email_type == "subscription_expiring":
            subject = "Biz-Retriever 구독 만료 임박"
            html_content = _render_expiring_email(user_name, plan_name)

        elif email_type == "subscription_cancelled":
            subject = "Biz-Retriever 구독 해지 확인"
            html_content = _render_cancelled_email(user_name, plan_name)

        else:
            logger.warning(f"Unknown email_type: {email_type}")
            return

        success = await email_service.send_email(
            to_email=user.email,
            subject=subject,
            html_content=html_content,
        )

        if success:
            logger.info(
                f"Subscription email sent: user={user_id}, type={email_type}"
            )
        else:
            logger.warning(
                f"Failed to send subscription email: user={user_id}, type={email_type}"
            )


# ============================================
# 이메일 템플릿 렌더링 헬퍼
# ============================================


def _base_email_wrapper(title: str, body_html: str) -> str:
    """이메일 기본 레이아웃 래퍼."""
    from app.core.config import settings

    return f"""
<!DOCTYPE html>
<html lang="ko">
<head><meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0"></head>
<body style="margin:0;padding:0;font-family:'Malgun Gothic',Arial,sans-serif;background:#f5f5f5;">
<table role="presentation" width="100%" style="background:#f5f5f5;">
<tr><td style="padding:40px 20px;">
<table role="presentation" width="100%" style="max-width:600px;margin:0 auto;background:#fff;border-radius:8px;box-shadow:0 2px 8px rgba(0,0,0,0.1);">
<tr><td style="padding:30px;text-align:center;background:linear-gradient(135deg,#667eea 0%,#764ba2 100%);border-radius:8px 8px 0 0;">
<h1 style="margin:0;color:#fff;font-size:22px;">Biz-Retriever</h1>
<p style="margin:8px 0 0;color:#fff;font-size:14px;">{title}</p>
</td></tr>
<tr><td style="padding:30px;">{body_html}</td></tr>
<tr><td style="padding:20px 30px;background:#f8f9fa;border-radius:0 0 8px 8px;text-align:center;">
<p style="margin:0;font-size:12px;color:#999;">
이 메일은 Biz-Retriever에서 자동 발송되었습니다.<br>
<a href="{settings.FRONTEND_URL}/profile.html" style="color:#667eea;">알림 설정 관리</a>
</p>
</td></tr>
</table>
</td></tr>
</table>
</body></html>"""


def _render_renewal_email(user_name: str, plan_name: str, amount: int) -> str:
    body = f"""
<p style="font-size:16px;color:#333;">안녕하세요 <strong>{user_name}</strong>님,</p>
<p style="font-size:14px;color:#666;">
{plan_name.upper()} 플랜이 자동 갱신되었습니다.
</p>
<table style="width:100%;background:#f8f9fa;border-radius:8px;margin:20px 0;">
<tr><td style="padding:15px;">
<p style="margin:0;font-size:14px;color:#666;"><strong>플랜:</strong> {plan_name.upper()}</p>
<p style="margin:8px 0 0;font-size:14px;color:#666;"><strong>결제 금액:</strong> {amount:,}원</p>
</td></tr>
</table>
<p style="font-size:13px;color:#999;">결제 내역은 마이페이지에서 확인하실 수 있습니다.</p>
"""
    return _base_email_wrapper("구독 갱신 완료", body)


def _render_payment_failed_email(
    user_name: str, plan_name: str, amount: int
) -> str:
    body = f"""
<p style="font-size:16px;color:#333;">안녕하세요 <strong>{user_name}</strong>님,</p>
<p style="font-size:14px;color:#dc3545;font-weight:600;">
{plan_name.upper()} 플랜 자동 결제에 실패했습니다.
</p>
<table style="width:100%;background:#fff5f5;border-left:4px solid #dc3545;border-radius:4px;margin:20px 0;">
<tr><td style="padding:15px;">
<p style="margin:0;font-size:14px;color:#666;">
결제 수단을 확인해 주세요. 3회 연속 실패 시 구독이 자동 해지됩니다.
</p>
</td></tr>
</table>
<p style="font-size:13px;color:#999;">
결제 수단 변경은 마이페이지 &gt; 구독 관리에서 가능합니다.
</p>
"""
    return _base_email_wrapper("결제 실패 알림", body)


def _render_expiring_email(user_name: str, plan_name: str) -> str:
    body = f"""
<p style="font-size:16px;color:#333;">안녕하세요 <strong>{user_name}</strong>님,</p>
<p style="font-size:14px;color:#666;">
{plan_name.upper()} 플랜 구독이 곧 만료됩니다.
</p>
<p style="font-size:14px;color:#666;">
만료 후에는 무료 플랜으로 전환되어 일부 기능이 제한됩니다.
계속 이용하시려면 결제 수단을 확인해 주세요.
</p>
"""
    return _base_email_wrapper("구독 만료 임박", body)


def _render_cancelled_email(user_name: str, plan_name: str) -> str:
    body = f"""
<p style="font-size:16px;color:#333;">안녕하세요 <strong>{user_name}</strong>님,</p>
<p style="font-size:14px;color:#666;">
{plan_name.upper()} 플랜 해지가 예약되었습니다.
</p>
<p style="font-size:14px;color:#666;">
현재 결제 기간이 끝날 때까지 모든 기능을 계속 이용하실 수 있습니다.
언제든 재구독하실 수 있습니다.
</p>
"""
    return _base_email_wrapper("구독 해지 확인", body)
