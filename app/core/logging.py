"""
Structured Logging 설정
개선사항: print() → logging 모듈
"""

import json
import logging
import os
import sys
from pathlib import Path

from app.core.config import settings


class JSONFormatter(logging.Formatter):
    """JSON 형식 로거 (Vercel 환경용)"""

    def format(self, record):
        return json.dumps(
            {
                "timestamp": self.formatTime(record),
                "level": record.levelname,
                "message": record.getMessage(),
                "module": record.module,
                "function": record.funcName,
                "line": record.lineno,
            }
        )


class SlackHandler(logging.Handler):
    """
    Slack Webhook을 통해 에러 로그를 전송하는 핸들러
    (Vercel 서버리스 호환: 동기 HTTP 호출, 타임아웃 설정)
    """

    def __init__(self, webhook_url: str):
        super().__init__()
        self.webhook_url = webhook_url

    def emit(self, record):
        if not self.webhook_url:
            return

        try:
            payload = {
                "text": "🚨 *Biz-Retriever Error Detected*",
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
                                "text": f"📍 {record.name} | 🕒 {record.asctime}",
                            }
                        ],
                    },
                ],
            }

            # 동기 HTTP 호출 (Fire-and-forget, 5초 타임아웃)
            self._send_payload_sync(payload)

        except Exception:
            self.handleError(record)

    def _send_payload_sync(self, payload):
        """동기 HTTP POST (Vercel 서버리스 호환)"""
        try:
            import httpx

            with httpx.Client(timeout=5.0) as client:
                client.post(self.webhook_url, json=payload)
        except ImportError:
            # httpx 미설치 시 urllib 사용
            try:
                from urllib.request import Request, urlopen

                req = Request(
                    self.webhook_url,
                    data=json.dumps(payload).encode("utf-8"),
                    headers={"Content-Type": "application/json"},
                )
                urlopen(req, timeout=5)
            except Exception as e:
                # 슬랙 전송 실패는 콘솔에만 출력 (재귀 방지)
                print(f"Failed to send Slack notification: {e}", file=sys.stderr)
        except Exception as e:
            # 슬랙 전송 실패는 콘솔에만 출력 (재귀 방지)
            print(f"Failed to send Slack notification: {e}", file=sys.stderr)


def setup_logger(name: str = "biz_retriever") -> logging.Logger:
    """
    구조화된 로거 설정 (Slack 알림 포함, Vercel 호환)
    """
    logger = logging.getLogger(name)
    logger.setLevel(logging.INFO)

    # 이미 핸들러가 있으면 추가하지 않음 (중복 방지)
    if logger.handlers:
        return logger

    # Vercel 환경 감지
    is_vercel = os.getenv("VERCEL") == "1"

    # 포맷 설정
    if is_vercel:
        # Vercel: JSON 구조화 로깅
        formatter = JSONFormatter()
    else:
        # 로컬: 읽기 쉬운 텍스트 포맷
        formatter = logging.Formatter(
            "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )

    # 1. 콘솔 핸들러 (Vercel stdout/stderr 캡처)
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    # 2. Slack 알림 핸들러
    if settings.SLACK_WEBHOOK_URL:
        slack_handler = SlackHandler(settings.SLACK_WEBHOOK_URL)
        slack_handler.setLevel(logging.ERROR)  # ERROR 이상만 전송
        slack_handler.setFormatter(formatter)
        logger.addHandler(slack_handler)

    return logger


# 싱글톤 로거
logger = setup_logger()
