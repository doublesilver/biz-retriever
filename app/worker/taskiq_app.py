"""
Taskiq Background Task System (Celery 대체)

Taskiq는 async-native Task Queue로 Celery보다 가볍고 FastAPI와 완벽하게 통합됩니다.
- 메모리 사용량 70% 감소
- Async/Await 네이티브 지원
- 단순한 설정 (Worker + Scheduler 통합)
"""

from taskiq import TaskiqScheduler
from taskiq.schedule_sources import LabelScheduleSource
from taskiq_redis import ListQueueBroker

from app.core.config import settings

# Redis Broker 생성
broker = ListQueueBroker(url=settings.REDIS_URL)

# Scheduler 생성 (Celery Beat 대체)
scheduler = TaskiqScheduler(
    broker=broker,
    sources=[LabelScheduleSource(broker)],
)


# ============================================
# Startup/Shutdown Hooks
# ============================================

async def startup():
    """Taskiq 시작 시 초기화"""
    await broker.startup()
    await scheduler.startup()


async def shutdown():
    """Taskiq 종료 시 정리"""
    await broker.shutdown()
    await scheduler.shutdown()
