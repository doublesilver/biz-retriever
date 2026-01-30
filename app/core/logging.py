"""
Structured Logging 설정
개선사항: print() → logging 모듈
"""

import json
import logging
import sys
import threading
from pathlib import Path
from urllib.error import URLError
from urllib.request import Request, urlopen

from app.core.config import settings

# 로그 디렉토리
LOG_DIR = Path("logs")
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

            # 비동기 전송 (Fire-and-forget)
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
            # 슬랙 전송 실패는 콘솔에만 출력 (재귀 방지)
            print(f"Failed to send Slack notification: {e}", file=sys.stderr)


def setup_logger(name: str = "biz_retriever") -> logging.Logger:
    """
    구조화된 로거 설정 (Slack 알림 포함)
    """
    logger = logging.getLogger(name)
    logger.setLevel(logging.INFO)

    # 이미 핸들러가 있으면 추가하지 않음 (중복 방지)
    if logger.handlers:
        return logger

    # 포맷 설정
    formatter = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    # 1. 콘솔 핸들러
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    # 2. 파일 핸들러 (전체 로그)
    file_handler = logging.FileHandler(LOG_DIR / "biz_retriever.log", encoding="utf-8")
    file_handler.setLevel(logging.INFO)
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)

    # 3. 에러 전용 파일 핸들러
    error_handler = logging.FileHandler(LOG_DIR / "errors.log", encoding="utf-8")
    error_handler.setLevel(logging.ERROR)
    error_handler.setFormatter(formatter)
    logger.addHandler(error_handler)

    # 4. Slack 알림 핸들러 (본격 적용)
    if settings.SLACK_WEBHOOK_URL:
        slack_handler = SlackHandler(settings.SLACK_WEBHOOK_URL)
        slack_handler.setLevel(logging.ERROR)  # ERROR 이상만 전송
        slack_handler.setFormatter(formatter)
        logger.addHandler(slack_handler)

    return logger


# 싱글톤 로거
logger = setup_logger()
