"""
Prometheus 메트릭 설정
애플리케이션 성능 및 비즈니스 메트릭 수집
"""
from prometheus_client import Counter, Histogram, Gauge, Info
from functools import wraps
import time
from typing import Callable


# ============================================
# 애플리케이션 정보
# ============================================
APP_INFO = Info(
    "biz_retriever",
    "Biz-Retriever 애플리케이션 정보"
)

# ============================================
# HTTP 요청 메트릭
# ============================================
HTTP_REQUESTS_TOTAL = Counter(
    "http_requests_total",
    "총 HTTP 요청 수",
    ["method", "endpoint", "status_code"]
)

HTTP_REQUEST_DURATION_SECONDS = Histogram(
    "http_request_duration_seconds",
    "HTTP 요청 처리 시간 (초)",
    ["method", "endpoint"],
    buckets=[0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0]
)

HTTP_REQUESTS_IN_PROGRESS = Gauge(
    "http_requests_in_progress",
    "현재 처리 중인 HTTP 요청 수",
    ["method", "endpoint"]
)

# ============================================
# 데이터베이스 메트릭
# ============================================
DB_QUERIES_TOTAL = Counter(
    "db_queries_total",
    "총 데이터베이스 쿼리 수",
    ["operation", "table"]
)

DB_QUERY_DURATION_SECONDS = Histogram(
    "db_query_duration_seconds",
    "데이터베이스 쿼리 실행 시간 (초)",
    ["operation", "table"],
    buckets=[0.001, 0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0]
)

DB_CONNECTIONS_ACTIVE = Gauge(
    "db_connections_active",
    "활성 데이터베이스 연결 수"
)

# ============================================
# 크롤링 메트릭
# ============================================
CRAWLER_RUNS_TOTAL = Counter(
    "crawler_runs_total",
    "크롤링 실행 횟수",
    ["source", "status"]  # source: G2B, Onbid / status: success, failure
)

CRAWLER_ANNOUNCEMENTS_COLLECTED = Counter(
    "crawler_announcements_collected_total",
    "수집된 공고 수",
    ["source", "importance_score"]
)

CRAWLER_DURATION_SECONDS = Histogram(
    "crawler_duration_seconds",
    "크롤링 소요 시간 (초)",
    ["source"],
    buckets=[1.0, 5.0, 10.0, 30.0, 60.0, 120.0, 300.0]
)

CRAWLER_LAST_RUN_TIMESTAMP = Gauge(
    "crawler_last_run_timestamp",
    "마지막 크롤링 실행 시간 (Unix timestamp)",
    ["source"]
)

# ============================================
# AI 분석 메트릭
# ============================================
AI_ANALYSIS_TOTAL = Counter(
    "ai_analysis_total",
    "AI 분석 실행 횟수",
    ["provider", "status"]  # provider: gemini, openai / status: success, failure
)

AI_ANALYSIS_DURATION_SECONDS = Histogram(
    "ai_analysis_duration_seconds",
    "AI 분석 소요 시간 (초)",
    ["provider"],
    buckets=[0.5, 1.0, 2.0, 5.0, 10.0, 30.0]
)

AI_TOKENS_USED = Counter(
    "ai_tokens_used_total",
    "사용된 AI 토큰 수",
    ["provider", "type"]  # type: input, output
)

# ============================================
# 알림 메트릭
# ============================================
NOTIFICATIONS_SENT_TOTAL = Counter(
    "notifications_sent_total",
    "발송된 알림 수",
    ["channel", "type", "status"]  # channel: slack / type: important, morning_briefing
)

NOTIFICATION_DURATION_SECONDS = Histogram(
    "notification_duration_seconds",
    "알림 발송 소요 시간 (초)",
    ["channel"],
    buckets=[0.1, 0.25, 0.5, 1.0, 2.0, 5.0]
)

# ============================================
# 캐시 메트릭
# ============================================
CACHE_HITS_TOTAL = Counter(
    "cache_hits_total",
    "캐시 히트 수",
    ["cache_type"]  # redis, local
)

CACHE_MISSES_TOTAL = Counter(
    "cache_misses_total",
    "캐시 미스 수",
    ["cache_type"]
)

CACHE_SIZE_BYTES = Gauge(
    "cache_size_bytes",
    "캐시 크기 (bytes)",
    ["cache_type"]
)

# ============================================
# Celery 작업 메트릭
# ============================================
CELERY_TASKS_TOTAL = Counter(
    "celery_tasks_total",
    "Celery 작업 실행 횟수",
    ["task_name", "status"]  # status: success, failure, retry
)

CELERY_TASK_DURATION_SECONDS = Histogram(
    "celery_task_duration_seconds",
    "Celery 작업 실행 시간 (초)",
    ["task_name"],
    buckets=[0.1, 0.5, 1.0, 5.0, 10.0, 30.0, 60.0, 300.0]
)

CELERY_QUEUE_LENGTH = Gauge(
    "celery_queue_length",
    "Celery 큐 대기 작업 수",
    ["queue_name"]
)

# ============================================
# 비즈니스 메트릭
# ============================================
BIDS_TOTAL = Gauge(
    "bids_total",
    "전체 공고 수",
    ["status"]  # new, reviewing, bidding, completed
)

BIDS_BY_SOURCE = Gauge(
    "bids_by_source",
    "소스별 공고 수",
    ["source"]  # G2B, Onbid
)

BIDS_BY_IMPORTANCE = Gauge(
    "bids_by_importance",
    "중요도별 공고 수",
    ["importance_score"]
)

USERS_TOTAL = Gauge(
    "users_total",
    "전체 사용자 수",
    ["is_active"]
)

# ============================================
# 헬퍼 함수 & 데코레이터
# ============================================

def track_request_metrics(method: str, endpoint: str):
    """
    HTTP 요청 메트릭 추적 데코레이터

    사용법:
        @track_request_metrics("GET", "/api/v1/bids")
        async def get_bids():
            ...
    """
    def decorator(func: Callable):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            HTTP_REQUESTS_IN_PROGRESS.labels(method=method, endpoint=endpoint).inc()
            start_time = time.time()

            try:
                result = await func(*args, **kwargs)
                HTTP_REQUESTS_TOTAL.labels(
                    method=method,
                    endpoint=endpoint,
                    status_code="200"
                ).inc()
                return result
            except Exception as e:
                HTTP_REQUESTS_TOTAL.labels(
                    method=method,
                    endpoint=endpoint,
                    status_code="500"
                ).inc()
                raise
            finally:
                duration = time.time() - start_time
                HTTP_REQUEST_DURATION_SECONDS.labels(
                    method=method,
                    endpoint=endpoint
                ).observe(duration)
                HTTP_REQUESTS_IN_PROGRESS.labels(method=method, endpoint=endpoint).dec()

        return wrapper
    return decorator


def track_db_query(operation: str, table: str):
    """
    데이터베이스 쿼리 메트릭 추적 데코레이터

    사용법:
        @track_db_query("SELECT", "bid_announcements")
        async def get_bids():
            ...
    """
    def decorator(func: Callable):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            start_time = time.time()
            try:
                result = await func(*args, **kwargs)
                DB_QUERIES_TOTAL.labels(operation=operation, table=table).inc()
                return result
            finally:
                duration = time.time() - start_time
                DB_QUERY_DURATION_SECONDS.labels(
                    operation=operation,
                    table=table
                ).observe(duration)

        return wrapper
    return decorator


def track_crawler_run(source: str):
    """
    크롤링 실행 메트릭 추적 데코레이터

    사용법:
        @track_crawler_run("G2B")
        async def crawl_g2b():
            ...
    """
    def decorator(func: Callable):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            start_time = time.time()
            try:
                result = await func(*args, **kwargs)
                CRAWLER_RUNS_TOTAL.labels(source=source, status="success").inc()
                CRAWLER_LAST_RUN_TIMESTAMP.labels(source=source).set(time.time())
                return result
            except Exception as e:
                CRAWLER_RUNS_TOTAL.labels(source=source, status="failure").inc()
                raise
            finally:
                duration = time.time() - start_time
                CRAWLER_DURATION_SECONDS.labels(source=source).observe(duration)

        return wrapper
    return decorator


def track_ai_analysis(provider: str):
    """
    AI 분석 메트릭 추적 데코레이터

    사용법:
        @track_ai_analysis("gemini")
        async def analyze_with_gemini():
            ...
    """
    def decorator(func: Callable):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            start_time = time.time()
            try:
                result = await func(*args, **kwargs)
                AI_ANALYSIS_TOTAL.labels(provider=provider, status="success").inc()
                return result
            except Exception as e:
                AI_ANALYSIS_TOTAL.labels(provider=provider, status="failure").inc()
                raise
            finally:
                duration = time.time() - start_time
                AI_ANALYSIS_DURATION_SECONDS.labels(provider=provider).observe(duration)

        return wrapper
    return decorator


def record_cache_hit(cache_type: str = "redis"):
    """캐시 히트 기록"""
    CACHE_HITS_TOTAL.labels(cache_type=cache_type).inc()


def record_cache_miss(cache_type: str = "redis"):
    """캐시 미스 기록"""
    CACHE_MISSES_TOTAL.labels(cache_type=cache_type).inc()


def record_notification_sent(channel: str, notification_type: str, success: bool = True):
    """알림 발송 기록"""
    status = "success" if success else "failure"
    NOTIFICATIONS_SENT_TOTAL.labels(
        channel=channel,
        type=notification_type,
        status=status
    ).inc()


def record_celery_task(task_name: str, status: str, duration: float):
    """Celery 작업 실행 기록"""
    CELERY_TASKS_TOTAL.labels(task_name=task_name, status=status).inc()
    CELERY_TASK_DURATION_SECONDS.labels(task_name=task_name).observe(duration)


def record_announcement_collected(source: str, importance_score: int):
    """공고 수집 기록"""
    CRAWLER_ANNOUNCEMENTS_COLLECTED.labels(
        source=source,
        importance_score=str(importance_score)
    ).inc()


# 앱 정보 초기화
def init_app_info(version: str = "1.0.0"):
    """애플리케이션 정보 초기화"""
    APP_INFO.info({
        "version": version,
        "name": "Biz-Retriever",
        "description": "입찰 공고 자동 수집 및 AI 분석 시스템"
    })
