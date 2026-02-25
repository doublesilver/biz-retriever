# ============================================
# Stage 1: Builder
# ============================================
# 학습 노트:
# 멀티스테이지 빌드란?
# 하나의 Dockerfile에서 여러 "스테이지"를 거쳐 최종 이미지를 만드는 기법입니다.
# 비유하면, 요리할 때 재료 손질(builder)과 플레이팅(runtime)을 분리하는 것과 같습니다.
# builder에서 컴파일/설치를 하고, runtime에는 실행에 필요한 것만 복사합니다.
# 결과: 이미지 크기 약 40% 감소, 보안 취약점 감소 (불필요한 도구 미포함)
# ============================================

FROM python:3.11-slim AS builder

WORKDIR /build

# 빌드 의존성 설치 (캐시 레이어 활용)
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    libffi-dev \
    && rm -rf /var/lib/apt/lists/*

# 가상환경 생성
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# 의존성 먼저 설치 (Docker 레이어 캐시 최적화)
# requirements.txt가 변경되지 않으면 이 레이어는 캐시에서 재사용됩니다
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt


# ============================================
# Stage 2: Runtime (프로덕션 이미지)
# ============================================
FROM python:3.11-slim AS runtime

# 이미지 메타데이터 (OCI 표준)
LABEL org.opencontainers.image.title="Biz-Retriever" \
      org.opencontainers.image.description="Public bid auto-collection and AI analysis system" \
      org.opencontainers.image.version="1.1.0" \
      org.opencontainers.image.source="https://github.com/doublesilver/biz-retriever"

WORKDIR /app

# 런타임 의존성만 설치
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 \
    curl \
    tini \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

# 보안: 비루트 사용자 생성
RUN groupadd --gid 1000 appuser && \
    useradd --uid 1000 --gid 1000 --shell /bin/bash --create-home appuser

# builder에서 가상환경 복사
COPY --from=builder /opt/venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Python 최적화 환경변수
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app \
    # Sentry release tracking
    SENTRY_RELEASE=1.1.0

# 애플리케이션 코드 복사
COPY --chown=appuser:appuser . .

# 시작 스크립트 실행 권한
RUN chmod +x /app/start.sh

# 필요 디렉토리 생성
RUN mkdir -p /app/app/static && chown -R appuser:appuser /app

# 비루트 사용자로 전환
USER appuser

# Railway는 $PORT를 동적으로 할당하므로 EXPOSE 생략
# EXPOSE 8000

# 헬스체크: $PORT에 대한 헬스체크 (폴백 8000)
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD curl -f http://localhost:${PORT:-8000}/health || exit 1

# tini를 PID 1로 사용 (좀비 프로세스 방지, 시그널 올바르게 전달)
# 학습 노트: tini란?
# 컨테이너 내부의 PID 1 프로세스는 특별한 역할을 합니다.
# 자식 프로세스가 죽으면 "좀비 프로세스"가 될 수 있는데,
# tini가 PID 1로서 이를 자동으로 정리하고,
# SIGTERM 같은 시그널도 자식에게 올바르게 전달합니다.
ENTRYPOINT ["tini", "--"]
CMD ["bash", "/app/start.sh"]


# ============================================
# Stage 3: Development (개발용)
# ============================================
FROM runtime AS development

USER root

RUN pip install --no-cache-dir \
    pytest \
    pytest-cov \
    pytest-asyncio \
    httpx \
    ruff \
    mypy

USER appuser

CMD ["bash", "/app/start.sh"]
