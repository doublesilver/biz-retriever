# 🐕 Biz-Retriever (비즈 리트리버)

[![CI](https://github.com/yourusername/biz-retriever/workflows/CI/badge.svg)](https://github.com/yourusername/biz-retriever/actions)
[![Python](https://img.shields.io/badge/Python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.100+-green.svg)](https://fastapi.tiangolo.com/)
[![License](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

> **"주인님, 여기 돈 냄새가 나는 입찰 공고를 찾아왔어요!"**

입찰 정보를 24시간 자동으로 수집하고, AI로 분석하여 회사의 핵심 사업(컨세션/화훼)에 맞는 '알짜 공고'만 필터링한 후, Slack 및 대시보드를 통해 실시간 알림을 제공하는 지능형 에이전트입니다.

## 📸 Demo

![Dashboard](docs/screenshots/dashboard.png)
*실시간 대시보드 - 중요도별 필터링, 통계 위젯*

![Slack Notification](docs/screenshots/slack_notification.png)
*Slack 실시간 알림 - 새로운 공고 즉시 수신*

## ✨ 주요 기능

### 🎯 Phase 1: G2B 크롤링 + 자동화
- ✅ **G2B API 연동**: 나라장터 공공데이터 API 활용
- ✅ **스마트 필터링**: 키워드 기반 자동 분류 (컨세션/화훼)
- ✅ **중요도 자동 채점**: ⭐⭐⭐ (1~3점) 알고리즘
- ✅ **Slack 실시간 알림**: 중요 공고(★★ 이상) 즉시 전송
- ✅ **모닝 브리핑**: 매일 08:30, 밤사이 수집한 공고 요약
- ✅ **자동 스케줄**: Celery Beat으로 하루 3회 (08:00, 12:00, 18:00)

### 📊 Phase 2: 대시보드 & 관리
- ✅ **웹 대시보드**: 실시간 공고 목록 + 통계
- ✅ **엑셀 Export**: 오프라인 공유/분석 용이
- ✅ **Kanban 상태 관리**: 신규 → 검토중 → 투찰예정 → 완료
- ✅ **제외어 관리**: Redis 기반 동적 업데이트
- ✅ **마감 임박 알림**: D-1 자동 알림

### 🤖 Phase 3: AI 분석
- ✅ **투찰가 예측**: 과거 낙찰 데이터 기반 ML 모델
- ✅ **신뢰도 제공**: Confidence Score + 예측 범위

---

## 🏗️ 기술 스택

| 계층 | 기술 | 설명 |
|------|------|------|
| **Backend** | FastAPI, Python 3.10+ | Async API 서버 |
| **Database** | PostgreSQL, SQLAlchemy | 공고 데이터 저장 |
| **Task Queue** | Celery, Redis | 비동기 크롤링 스케줄링 |
| **Cache** | Redis | API 응답 캐싱, 제외어 관리 |
| **AI/ML** | LangChain, OpenAI | RAG 분석, 투찰가 예측 |
| **Notification** | Slack Webhook | 실시간 알림 |
| **Testing** | pytest, Playwright | Unit/Integration/E2E |
| **CI/CD** | GitHub Actions | 자동화 테스트 및 배포 |
| **Deployment** | Docker, Railway | 컨테이너 배포 |

---

## 🚀 빠른 시작

### 1. 환경 준비
```bash
git clone https://github.com/yourusername/biz-retriever.git
cd biz-retriever

# 가상 환경
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# 의존성 설치
pip install -r requirements.txt

# 환경 변수 설정
cp .env.example .env
# .env 파일 편집
```

### 2. API 키 발급

#### G2B API 키 (필수)
1. [공공데이터포털](https://www.data.go.kr/) 회원가입
2. "나라장터 입찰공고" 데이터 활용 신청
3. Decoding Key를 `.env`에 입력

#### Slack Webhook URL (필수)
1. Slack Workspace > Apps > "Incoming Webhooks"
2. 채널 선택 (`#입찰-알림` 권장)
3. Webhook URL 복사하여 `.env`에 입력

### 3. Docker로 실행 (권장)
```bash
# 전체 스택 실행
docker-compose up -d --build

# 로그 확인
docker-compose logs -f app
```

### 4. 로컬 실행
```bash
# DB & Redis
docker-compose up -d db redis

# API 서버
uvicorn app.main:app --reload

# Celery Worker
celery -A app.worker.celery_app worker --loglevel=info

# Celery Beat (스케줄러)
celery -A app.worker.celery_app beat --loglevel=info
```

### 5. 접속
- **대시보드**: http://localhost:8000
- **Swagger API**: http://localhost:8000/docs

---

## 🧪 테스트

### Unit & Integration Tests
```bash
pytest --cov=app --cov-report=term
# Coverage: 90%+
```

### E2E Browser Test
```bash
# Playwright 설치
pip install playwright
playwright install chromium

# E2E 테스트 실행 (자동 스크린샷 생성)
python tests/e2e_browser_test.py
```

**결과:** `docs/screenshots/` 폴더에 9장의 스크린샷 자동 생성

---

## 📡 API 엔드포인트

### 인증
```http
POST /api/v1/auth/register      # 회원가입
POST /api/v1/auth/login/access-token  # 로그인
```

### 크롤러
```http
POST /api/v1/crawler/trigger    # 수동 크롤링
GET  /api/v1/crawler/status/{id}  # 상태 확인
```

### Export
```http
GET /api/v1/export/excel         # 엑셀 다운로드
GET /api/v1/export/priority-agencies?agencies=서울대병원,... # 우선 기관 Export
```

### Analytics
```http
GET /api/v1/analytics/summary    # 통계 요약
GET /api/v1/analytics/trends     # 트렌드 데이터
GET /api/v1/analytics/deadline-alerts  # 마감 임박 공고
```

### AI 분석
```http
GET /api/v1/analysis/predict-price/{id}  # 투찰가 예측
```

---

## 🌟 narajangteo 대비 차별화

| 항목 | narajangteo | Biz-Retriever |
|------|-------------|---------------|
| 실행 방식 | 수동 | **자동 (Celery)** ⭐⭐⭐⭐⭐ |
| 알림 | ❌ | **Slack 실시간** ⭐⭐⭐⭐⭐ |
| 저장 | 엑셀 | **PostgreSQL** ⭐⭐⭐⭐ |
| UI | CLI | **웹 대시보드** ⭐⭐⭐⭐ |
| 확장성 | 낮음 | **매우 높음** ⭐⭐⭐⭐⭐ |
| AI 분석 | ❌ | **투찰가 예측** ⭐⭐⭐⭐ |
| 테스트 | ❌ | **90% Coverage** ⭐⭐⭐⭐⭐ |

**배운 점 적용:**
- ✅ 엑셀 Export 기능 (오프라인 공유)
- ✅ 우선 기관 필터링

---

## 📊 프로젝트 지표

- **테스트 커버리지**: 90%+
- **API 엔드포인트**: 20+
- **코드 품질**: A급 (92/100)
- **GitHub Stars**: ⭐ (Please star!)

---

## 🤝 기여 방법

1. Fork the Project
2. Create your Feature Branch (`git checkout -b feature/AmazingFeature`)
3. Commit your Changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the Branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

---

## 📝 라이선스

MIT License - 자유롭게 사용, 수정, 배포 가능

---

## 👤 작성자

**Backend Developer Portfolio Project**

- 실무급 기술 스택 (FastAPI, Celery, pytest)
- 테스트 주도 개발 (TDD)
- CI/CD 파이프라인 구축
- 보안 best practices 적용

---

## 📚 문서

- [API 문서](http://localhost:8000/docs)
- [프로젝트 평가](PROJECT_EVALUATION.md)
- [경쟁 분석](COMPETITIVE_ANALYSIS.md)

---

**🐕 Biz-Retriever - 입찰 정보의 든든한 사냥개!**
