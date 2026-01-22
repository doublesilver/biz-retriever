from celery import Celery
from celery.schedules import crontab
from app.core.config import settings

celery_app = Celery(
    "worker",
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_RESULT_BACKEND
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="Asia/Seoul",
    enable_utc=True,
)

celery_app.conf.task_routes = {
    "app.worker.tasks.*": {"queue": "main-queue"}
}

# Phase 1: Celery Beat 스케줄 설정
celery_app.conf.beat_schedule = {
    'crawl-g2b-morning': {
        'task': 'app.worker.tasks.crawl_g2b_bids',
        'schedule': crontab(hour=8, minute=0),  # 매일 08:00
    },
    'crawl-g2b-noon': {
        'task': 'app.worker.tasks.crawl_g2b_bids',
        'schedule': crontab(hour=12, minute=0),  # 매일 12:00
    },
    'crawl-g2b-evening': {
        'task': 'app.worker.tasks.crawl_g2b_bids',
        'schedule': crontab(hour=18, minute=0),  # 매일 18:00
    },
    'morning-digest': {
        'task': 'app.worker.tasks.send_morning_digest',
        'schedule': crontab(hour=8, minute=30),  # 매일 08:30
    },
}
