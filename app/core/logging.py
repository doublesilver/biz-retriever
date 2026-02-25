"""
JSON Structured Logging with structlog

--- 학습 노트 ---

# 개념 설명

## structlog이란?
structlog은 Python의 로깅을 "구조화된 데이터"로 바꿔주는 라이브러리입니다.
기존 logging 모듈이 "2024-01-01 ERROR: 뭔가 터짐" 같은 텍스트를 남긴다면,
structlog은 {"timestamp": "2024-01-01", "level": "error", "event": "뭔가 터짐", "user_id": 123}
같은 JSON을 남깁니다.

## 왜 필요한가?
- **검색 가능**: JSON이므로 Datadog, ELK, CloudWatch에서 필드 단위 검색 가능
- **컨텍스트 바인딩**: request_id, user_id 같은 정보를 자동으로 모든 로그에 포함
- **Railway 호환**: Railway는 stdout JSON 로그를 자동 파싱하여 구조화 로그 뷰어 제공

## 동작 원리
1. structlog.configure()로 처리 파이프라인 설정
2. 각 로그 이벤트가 파이프라인을 거쳐 JSON으로 변환
3. 개발 환경에서는 사람이 읽기 쉬운 컬러 출력
4. 프로덕션 환경에서는 기계가 파싱하기 쉬운 JSON 출력

# 코드 설명
- configure_logging(): 환경에 따라 개발용/프로덕션용 포매터 선택
- get_logger(): 구조화된 로거 인스턴스 반환
- add_app_context(): 서비스명, 환경 등 공통 컨텍스트 자동 추가

# 결과 정리
- 변경 전: print/logging → 텍스트 로그 → 검색/분석 불가
- 변경 후: structlog → JSON 로그 → Railway/ELK에서 필드 단위 검색, 알림 설정 가능
"""

import json
import logging
import os
import sys
import threading
from pathlib import Path
from typing import Any
from urllib.error import URLError
from urllib.request import Request, urlopen

import structlog

from app.core.config import settings

# Railway 환경 감지
IS_RAILWAY = bool(os.getenv("RAILWAY_ENVIRONMENT"))
IS_PRODUCTION = os.getenv("ENVIRONMENT", "development") == "production" or IS_RAILWAY

# 로그 디렉토리 (Railway가 아닌 경우에만 생성)
LOG_DIR = Path("logs")
if not IS_RAILWAY:
    LOG_DIR.mkdir(exist_ok=True)


class SlackHandler(logging.Handler):
    """
    Slack Webhook을 통해 에러 로그를 전송하는 핸들러
    (메인 스레드 차단 방지를 위해 별도 스레드 사용)
    """

    def __init__(self, webhook_url: str):
        super().__init__()
        self.webhook_url = webhook_url

    def emit(self, record):
        if not self.webhook_url:
            return

        try:
            log_entry = self.format(record)
            payload = {
                "text": "*Biz-Retriever Error Detected*",
                "blocks": [
                    {
                        "type": "section",
                        "text": {
                            "type": "mrkdwn",
                            "text": f"*{record.levelname}*: {record.msg}",
                        },
                    },
                    {
                        "type": "context",
                        "elements": [
                            {
                                "type": "mrkdwn",
                                "text": f"{record.name} | {record.asctime}",
                            }
                        ],
                    },
                ],
            }

            threading.Thread(
                target=self._send_payload, args=(payload,), daemon=True
            ).start()

        except Exception:
            self.handleError(record)

    def _send_payload(self, payload):
        try:
            req = Request(
                self.webhook_url,
                data=json.dumps(payload).encode("utf-8"),
                headers={"Content-Type": "application/json"},
            )
            urlopen(req, timeout=3)
        except Exception as e:
            print(f"Failed to send Slack notification: {e}", file=sys.stderr)


def add_app_context(
    logger: structlog.types.WrappedLogger,
    method_name: str,
    event_dict: dict[str, Any],
) -> dict[str, Any]:
    """모든 로그 이벤트에 서비스 컨텍스트를 자동 추가"""
    event_dict["service"] = "biz-retriever"
    event_dict["environment"] = "production" if IS_PRODUCTION else "development"
    railway_env = os.getenv("RAILWAY_ENVIRONMENT")
    if railway_env:
        event_dict["railway_env"] = railway_env
    return event_dict


def configure_logging() -> None:
    """
    structlog + 표준 logging 통합 설정

    - 프로덕션: JSON 출력 (Railway, ELK 등에서 자동 파싱)
    - 개발: 컬러 콘솔 출력 (사람이 읽기 쉬운 포맷)
    """
    # 공통 프로세서 파이프라인
    shared_processors: list[structlog.types.Processor] = [
        structlog.contextvars.merge_contextvars,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.stdlib.ExtraAdder(),
        add_app_context,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.UnicodeDecoder(),
    ]

    if IS_PRODUCTION:
        # 프로덕션: JSON 포맷
        renderer = structlog.processors.JSONRenderer()
    else:
        # 개발: 컬러 콘솔 포맷
        renderer = structlog.dev.ConsoleRenderer()

    structlog.configure(
        processors=[
            *shared_processors,
            structlog.stdlib.ProcessorFormatter.wrap_for_formatter,
        ],
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )

    # 표준 logging 핸들러 설정
    formatter = structlog.stdlib.ProcessorFormatter(
        processors=[
            structlog.stdlib.ProcessorFormatter.remove_processors_meta,
            renderer,
        ],
        foreign_pre_chain=shared_processors,
    )

    # 콘솔 핸들러
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)

    # 루트 로거 설정
    root_logger = logging.getLogger()
    root_logger.handlers.clear()
    root_logger.addHandler(console_handler)
    root_logger.setLevel(logging.INFO)

    # 파일 핸들러 (Railway 환경에서는 스킵)
    if not IS_RAILWAY:
        file_handler = logging.FileHandler(LOG_DIR / "biz_retriever.log", encoding="utf-8")
        file_handler.setFormatter(formatter)
        root_logger.addHandler(file_handler)

        error_handler = logging.FileHandler(LOG_DIR / "errors.log", encoding="utf-8")
        error_handler.setLevel(logging.ERROR)
        error_handler.setFormatter(formatter)
        root_logger.addHandler(error_handler)

    # Slack 알림 핸들러
    if settings.SLACK_WEBHOOK_URL:
        slack_handler = SlackHandler(settings.SLACK_WEBHOOK_URL)
        slack_handler.setLevel(logging.ERROR)
        text_formatter = logging.Formatter(
            "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )
        slack_handler.setFormatter(text_formatter)
        root_logger.addHandler(slack_handler)

    # 서드파티 라이브러리 로깅 레벨 조정
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    logging.getLogger("sqlalchemy.engine").setLevel(
        logging.INFO if settings.SQL_ECHO else logging.WARNING
    )
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)


def get_logger(name: str | None = None) -> structlog.stdlib.BoundLogger:
    """구조화된 로거 인스턴스 반환"""
    return structlog.get_logger(name or "biz_retriever")


# 초기화 시 로깅 설정 적용
configure_logging()

# 호환성: 기존 코드에서 `from app.core.logging import logger` 사용
logger = get_logger()
