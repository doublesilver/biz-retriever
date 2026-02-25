"""
Sentry Error Tracking 설정

--- 학습 노트 ---

# 개념 설명

## Sentry란?
Sentry는 "에러 추적 서비스"입니다. 앱에서 에러가 발생하면 자동으로 Sentry 대시보드에
기록되어, 어디서 어떤 에러가 얼마나 자주 발생하는지 한눈에 볼 수 있습니다.
비유하면 CCTV가 "도둑"을 자동으로 감지하고 녹화하는 것처럼,
Sentry는 "버그"를 자동으로 감지하고 기록합니다.

## 왜 필요한가?
- 프로덕션에서 사용자가 겪는 에러를 실시간으로 파악
- 에러 발생 시 스택트레이스, 요청 정보, 사용자 정보 자동 수집
- 같은 에러를 그룹핑하여 중복 알림 방지
- 배포 후 에러율 변화 추적 (Release Health)

## 동작 원리
1. sentry_sdk.init()으로 DSN(Data Source Name) 설정
2. FastAPI 미들웨어가 자동으로 에러를 Sentry에 전송
3. traces_sample_rate로 성능 모니터링 비율 조절
4. before_send 콜백으로 민감한 정보 필터링

# 결과 정리
- 변경 전: 에러 발생 시 로그 파일을 직접 뒤져야 함
- 변경 후: Sentry 대시보드에서 실시간 에러 모니터링, Slack 자동 알림
"""

import logging
import os

import sentry_sdk
from sentry_sdk.integrations.fastapi import FastApiIntegration
from sentry_sdk.integrations.logging import LoggingIntegration
from sentry_sdk.integrations.sqlalchemy import SqlalchemyIntegration


def _before_send(event: dict, hint: dict) -> dict | None:
    """민감한 정보를 Sentry로 전송하기 전에 필터링"""
    # 특정 에러 무시 (노이즈 제거)
    if "exc_info" in hint:
        exc_type, exc_value, _ = hint["exc_info"]
        # 404, 429 등 일상적 에러는 전송하지 않음
        if hasattr(exc_value, "status_code") and exc_value.status_code in (404, 429):
            return None

    # 요청 데이터에서 민감 정보 제거
    if "request" in event:
        request_data = event["request"]
        if "headers" in request_data:
            headers = request_data["headers"]
            for sensitive_key in ("Authorization", "Cookie", "X-API-Key"):
                if sensitive_key in headers:
                    headers[sensitive_key] = "[Filtered]"
        if "data" in request_data and isinstance(request_data["data"], dict):
            for sensitive_field in ("password", "secret_key", "api_key", "token"):
                if sensitive_field in request_data["data"]:
                    request_data["data"][sensitive_field] = "[Filtered]"

    return event


def init_sentry() -> None:
    """
    Sentry SDK 초기화

    SENTRY_DSN 환경변수가 설정된 경우에만 활성화됩니다.
    개발 환경에서는 비활성화되어 불필요한 이벤트 전송을 방지합니다.
    """
    sentry_dsn = os.getenv("SENTRY_DSN")
    if not sentry_dsn:
        return

    environment = os.getenv("RAILWAY_ENVIRONMENT", os.getenv("ENVIRONMENT", "development"))

    sentry_sdk.init(
        dsn=sentry_dsn,
        environment=environment,
        release=f"biz-retriever@{os.getenv('RAILWAY_GIT_COMMIT_SHA', '1.1.0')}",
        # 성능 모니터링: 프로덕션 10%, 개발 100%
        traces_sample_rate=0.1 if environment == "production" else 1.0,
        # 프로파일링: 프로덕션에서만 10%
        profiles_sample_rate=0.1 if environment == "production" else 0.0,
        # 민감 정보 필터링
        before_send=_before_send,
        # FastAPI, SQLAlchemy 자동 계측
        integrations=[
            FastApiIntegration(transaction_style="endpoint"),
            SqlalchemyIntegration(),
            LoggingIntegration(
                level=logging.INFO,
                event_level=logging.ERROR,
            ),
        ],
        # PII(개인식별정보) 전송 비활성화
        send_default_pii=False,
        # 이벤트 전송 전 서버 검증
        server_name=os.getenv("RAILWAY_SERVICE_NAME", "biz-retriever"),
    )
