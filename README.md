# 🐕 Biz-Retriever (비즈 리트리버)

[![Python](https://img.shields.io/badge/Python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115+-009688.svg)](https://fastapi.tiangolo.com/)
[![Tests](https://img.shields.io/badge/Tests-955%2F955_Passed-brightgreen.svg)]()
[![Coverage](https://img.shields.io/badge/Coverage-95%25-green.svg)]()
[![License](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

> 입찰 공고를 24시간 자동 수집하고, **Google Gemini AI**로 분석하여 회사 핵심 사업에 맞는 공고만 필터링 → Slack 실시간 알림 + 웹 대시보드 제공

| 항목 | 내용 |
|------|------|
| **개발 기간** | 10일 (2026.01.22 ~ 01.31) |
| **개발 인원** | 1인 (기획 → 설계 → 개발 → 테스트 → 배포) |
| **코드 규모** | 30,000+ lines · 955 tests (100% pass) · 95% coverage |
| **라이브** | [Frontend](https://biz-retriever.vercel.app) (Vercel) · Backend (Railway) |

---

## 주요 기능

| 기능 | 설명 | 기술 |
|------|------|------|
| **G2B 자동 크롤링** | 나라장터 공공데이터 API에서 하루 3회 자동 수집 (9,572건 검증) | Taskiq Scheduler, httpx |
| **AI 분석 & 필터링** | 공고 자동 요약, 키워드 추출, 중요도 채점 (1~3점) | Gemini 2.5 Flash, Instructor |
| **Hard Match** | 지역·면허·실적 기반 오탐 0% 필터링 | 구조화된 JSON 스키마 |
| **Slack 실시간 알림** | 중요 공고 즉시 전송 + 매일 08:30 모닝 브리핑 | Slack Webhook |
| **웹 대시보드** | 공고 목록, 통계 위젯, Kanban 상태 관리, Excel Export | Vanilla JS SPA |
| **JWT 인증** | Access Token 15분 + Refresh Token 30일 + 토큰 블랙리스트 | python-jose, Redis |
| **결제 시스템** | Tosspayments V2 통합, 구독 라이프사이클, 과금 엔진 (인보이스) | Tosspayments API |
| **보안** | OWASP Top 10 감사 완료, 보안 헤더 미들웨어, Fail-closed, Rate Limiting | SlowAPI, TrustedHost |

---

## 기술 스택

```
Frontend    Vanilla JS (SPA) · Pretendard · MD3 Design System · WCAG 2.1 AA · Vercel
Backend     FastAPI (Async) · SQLAlchemy 2.0 (Async ORM) · Pydantic 2.10
AI          Google Gemini 2.5 Flash · LangChain · Instructor
Database    PostgreSQL 14+ · Valkey 8 (Redis fork)
Task Queue  Taskiq (Celery 대비 메모리 70% 절감: 400MB → 120MB)
Payment     Tosspayments V2 · 구독 라이프사이클 · 인보이스 과금 엔진
Infra       Docker (Multi-stage, tini) · GitHub Actions CI/CD 5단계 · Railway
Monitoring  structlog JSON + Sentry · Prometheus + Grafana (11 Alert Rules)
Linter      ruff (black + flake8 + isort 대체)
```

---

## 아키텍처

```mermaid
graph TB
    subgraph Client
        A[Web Dashboard<br/>Vercel]
        B[Slack<br/>Notifications]
    end

    subgraph "Backend (FastAPI)"
        C[REST API]
        D[Crawler Service<br/>G2B API]
        E[RAG Service<br/>Gemini AI]
        F[Notification Service]
    end

    subgraph "Task Queue"
        G[Taskiq Scheduler<br/>3회/일 자동 실행]
    end

    subgraph "Data Layer"
        H[(PostgreSQL)]
        I[(Valkey<br/>Cache + Queue)]
    end

    subgraph "External"
        J[G2B 나라장터 API]
        K[Gemini API]
        L[Slack Webhook]
    end

    A --> C
    C --> D & E & F
    G --> D & E & F
    D --> J
    E --> K
    F --> L
    D & E --> H
    C --> I
    B --> L

    style C fill:#009688
    style E fill:#4285F4
    style H fill:#4169E1
    style I fill:#DC382D
```

---

## 기술적 도전과 해결

| 문제 | 원인 | 해결 | 결과 |
|------|------|------|------|
| G2B API 인코딩 에러 | URL 인코딩 미처리 | `unquote(api_key)` + `YYYYMMDD` 포맷 | 9,572건 수집 성공 |
| `google-generativeai` deprecated | 패키지 교체 필요 | `google-genai` + Gemini 2.5 Flash 전환 | 무료 1,500 req/일 |
| Celery 메모리 과다 (400MB) | 동기 Worker 구조 | Taskiq Async-native로 전환 | **120MB** (70% 절감) |
| SD 카드 수명 문제 | PostgreSQL 쓰기 집중 | WAL 최적화, vacuum 튜닝 | 쓰기 80% 감소, 수명 3배 |
| 테스트 1개 실패 (119/120) | Pydantic 422 vs 400 | 실제 응답코드에 맞게 수정 | **955/955** (100%) |

---

## 실행 방법

```bash
# Clone & Setup
git clone https://github.com/doublesilver/biz-retriever.git
cd biz-retriever
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env  # API 키 설정

# DB Migration & Run
alembic upgrade head
uvicorn app.main:app --reload --port 8000

# Worker & Scheduler (별도 터미널)
taskiq worker app.worker.taskiq_app:broker --fs-discover
taskiq scheduler app.worker.taskiq_app:scheduler
```

### 필수 환경 변수

```bash
DATABASE_URL=postgresql+asyncpg://user:pass@host/db
REDIS_HOST=localhost
SECRET_KEY=your_secret_key
G2B_API_KEY=your_g2b_api_key          # 공공데이터포털
GEMINI_API_KEY=your_gemini_api_key    # Google AI Studio
SLACK_WEBHOOK_URL=your_webhook_url
```

### Docker

```bash
docker-compose up -d
```

---

## 프로젝트 구조

```
biz-retriever/
├── app/
│   ├── api/endpoints/     # REST API (auth, bids, analytics, export)
│   ├── core/              # config, security, database
│   ├── models/            # SQLAlchemy models
│   ├── schemas/           # Pydantic schemas
│   ├── services/          # crawler, rag, notification, ml
│   ├── worker/            # Taskiq tasks & scheduler
│   └── main.py
├── frontend/              # Vanilla JS SPA (Vercel 배포)
├── tests/                 # 955 tests · 95% coverage
├── alembic/               # DB migrations
├── docs/                  # 운영 가이드
├── monitoring/            # Prometheus + Grafana configs
├── Dockerfile             # Multi-stage build
└── docker-compose.yml
```

---

## 테스트

```bash
pytest tests/ -v                          # 전체 실행 (955 tests)
pytest tests/ --cov=app --cov-report=html  # 커버리지 리포트 (95%)
```

| 구분 | 테스트 수 | 비율 |
|------|----------|------|
| Unit | ~592 | 62% |
| Integration | ~267 | 28% |
| E2E | ~96 | 10% |
| **합계** | **955** | **100% pass, 95% coverage** |

---

## 라이브 서비스

| 서비스 | URL | 플랫폼 |
|--------|-----|--------|
| Frontend | [biz-retriever.vercel.app](https://biz-retriever.vercel.app) | Vercel (CDN) |
| Backend API | Railway | Docker (tini + Graceful Shutdown) |
| API Docs | `/docs` (Swagger) · `/redoc` | FastAPI 자동 생성 |

---

## License

MIT License - see [LICENSE](LICENSE)

---

**Made with ❤️ by [doublesilver](https://github.com/doublesilver)**
