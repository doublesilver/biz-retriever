# Biz-Retriever 프로젝트 평가 (백엔드 신입 채용 관점)

## 📊 종합 평가: **B+ (75/100)**

### 평가 기준
- **기술 스택**: 85/100 ⭐⭐⭐⭐
- **실무 활용도**: 90/100 ⭐⭐⭐⭐⭐
- **코드 품질**: 65/100 ⭐⭐⭐
- **테스트**: 40/100 ⭐⭐
- **문서화**: 90/100 ⭐⭐⭐⭐⭐
- **배포 준비도**: 70/100 ⭐⭐⭐

---

## ✅ 강점 (면접관이 좋아할 포인트)

### 1. 실무적 문제 해결 능력 ⭐⭐⭐⭐⭐
- **Real-world Problem**: 입찰 정보 자동화는 실제 비즈니스 가치가 있는 문제
- **도메인 이해도**: 컨세션/화훼 사업에 특화된 필터링 로직
- **자동화 사고**: 수동 작업(매일 1~2시간)을 자동화로 대체

**면접에서 어필 포인트:**
> "단순 CRUD가 아닌, 실제 업무 효율을 개선하는 백엔드를 설계했습니다."

---

### 2. 현대적 기술 스택 ⭐⭐⭐⭐⭐
- **FastAPI**: 트렌디한 비동기 프레임워크 선택
- **Celery + Redis**: 작업 큐 이해도
- **PostgreSQL + SQLAlchemy 2.0**: ORM 최신 버전 사용
- **Docker Compose**: 인프라스트럭처 as Code

**면접에서 어필 포인트:**
> "신입이지만 비동기 처리, 작업 큐, 캐싱 등 중급 개념을 직접 구현했습니다."

---

### 3. 체계적 설계 ⭐⭐⭐⭐
- **Layered Architecture**: API - Service - DB 계층 분리
- **Phase별 구현**: 점진적 개발 능력 입증
- **확장 가능한 구조**: ML 모델 교체 가능하도록 추상화

**면접에서 어필 포인트:**
> "단순 기능 구현이 아닌, 유지보수와 확장을 고려한 설계를 했습니다."

---

### 4. 뛰어난 문서화 ⭐⭐⭐⭐⭐
- **README**: 친절한 Quick Start 가이드
- **SPEC.md**: 명확한 요구사항 정의
- **PROGRESS.md**: 개발 이력 추적
- **주석**: 한글 주석으로 가독성 확보

**면접에서 어필 포인트:**
> "협업을 고려한 문서화 습관이 몸에 배어 있습니다."

---

## ⚠️ 약점 (개선 필요)

### 1. 테스트 커버리지 부족 ⚠️⚠️⚠️
**현재 상태:**
- `scripts/` 폴더에 수동 검증 스크립트만 존재
- 자동화된 Unit Test가 없음
- Integration Test 미흡

**개선 방안:**
```bash
# pytest 기반 테스트 추가 필요
tests/
├── unit/
│   ├── test_crawler_service.py    # 크롤러 로직 테스트
│   ├── test_ml_service.py          # ML 예측 로직 테스트
│   └── test_notification_service.py
├── integration/
│   └── test_api_endpoints.py       # API 통합 테스트
└── conftest.py                     # Fixture 정의
```

**추가할 테스트 예시:**
```python
# tests/unit/test_crawler_service.py
def test_importance_score_calculation():
    announcement = {
        "title": "서울대병원 구내식당 위탁운영",
        "estimated_price": 150000000,
        "keywords_matched": ["구내식당", "위탁운영"]
    }
    score = g2b_crawler.calculate_importance_score(announcement)
    assert score == 3  # 최고 중요도

def test_exclude_keyword_filtering():
    announcement = {
        "title": "폐기물 처리 용역",
        "content": "..."
    }
    assert not g2b_crawler._should_notify(announcement)
```

**GitHub Actions CI 추가:**
```yaml
# .github/workflows/ci.yml
name: CI
on: [push, pull_request]
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - run: pip install -r requirements.txt
      - run: pytest --cov=app --cov-report=xml
      - uses: codecov/codecov-action@v3
```

**면접관 질문 예상:**
- Q: "테스트 커버리지는 얼마나 되나요?"
- A: ❌ "아직 작성 중입니다" → ✅ "핵심 로직은 80% 이상 커버, CI로 자동화했습니다"

---

### 2. 로깅이 print()만 사용 ⚠️⚠️
**현재 상태:**
```python
print(f"G2B 크롤링 완료: {len(announcements)}건")  # ❌
```

**개선 방안:**
```python
# app/core/logging.py
import logging
import sys

def setup_logger():
    logger = logging.getLogger("biz_retriever")
    logger.setLevel(logging.INFO)
    
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    ))
    logger.addHandler(handler)
    return logger

logger = setup_logger()

# 사용 예시
logger.info(f"G2B 크롤링 완료: {len(announcements)}건")
logger.error(f"Slack 알림 전송 실패: {e}")
```

**Structured Logging 추가 (중급):**
```python
import structlog

logger = structlog.get_logger()
logger.info("crawl_completed", source="G2B", count=len(announcements))
# → {"event": "crawl_completed", "source": "G2B", "count": 15, "timestamp": "..."}
```

---

### 3. 에러 핸들링 미흡 ⚠️
**현재 상태:**
```python
except Exception as e:
    print(f"에러: {e}")  # 너무 Generic
    return []
```

**개선 방안:**
```python
# app/core/exceptions.py
class CrawlerException(Exception):
    """크롤러 관련 에러"""
    pass

class APIKeyInvalidError(CrawlerException):
    """API 키 오류"""
    pass

# 사용
try:
    response = await self.client.get(self.api_endpoint, params=params)
    response.raise_for_status()
except httpx.HTTPStatusError as e:
    if e.response.status_code == 401:
        raise APIKeyInvalidError("G2B API 키가 유효하지 않습니다.")
    raise
except httpx.TimeoutException:
    logger.error("G2B API 타임아웃")
    raise CrawlerException("크롤링 타임아웃")
```

**Sentry 연동 (Production):**
```python
# app/main.py
import sentry_sdk

sentry_sdk.init(
    dsn=settings.SENTRY_DSN,
    environment="production"
)
```

---

### 4. 보안 측면 ⚠️

#### 4.1 비밀번호 정책 없음
**개선:**
```python
# app/core/security.py
import re

def validate_password(password: str):
    if len(password) < 8:
        raise ValueError("비밀번호는 8자 이상이어야 합니다.")
    if not re.search(r'[A-Z]', password):
        raise ValueError("대문자 포함 필요")
    if not re.search(r'[0-9]', password):
        raise ValueError("숫자 포함 필요")
```

#### 4.2 CORS 설정 필요
```python
# app/main.py
from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://yourdomain.com"],  # 특정 도메인만
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

#### 4.3 Rate Limiting 필요
```python
from slowapi import Limiter
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)

@app.post("/api/v1/crawler/trigger")
@limiter.limit("5/minute")  # 분당 5회 제한
async def trigger_crawl():
    ...
```

---

### 5. 실제 데이터 부재 ⚠️
**현재 상태:**
- G2B API 키 미발급 상태로 Mock만 존재
- Slack 알림 미검증

**GitHub 공개 전 필수:**
1. G2B API 키 발급 후 **실제 크롤링 결과 스크린샷** 추가
2. Slack 알림 **실제 전송 캡처** 추가
3. README에 `Demo` 섹션 추가

**Demo 섹션 예시:**
```markdown
## 📸 Demo

### Slack 실시간 알림
![Slack Notification](docs/screenshots/slack_notification.png)

### 대시보드
![Dashboard](docs/screenshots/dashboard.png)

### AI 투찰가 예측
![AI Prediction](docs/screenshots/ai_prediction.png)
```

---

## 🔧 GitHub 공개 전 체크리스트

### 필수 (Must Have)
- [ ] `.env` 파일 .gitignore에 추가 (보안)
- [ ] `SECRET_KEY`를 실제 랜덤 값으로 변경
- [ ] 민감 정보 제거 (API 키, Webhook URL)
- [ ] LICENSE 파일 추가 (MIT 권장)
- [ ] `.github/workflows/ci.yml` 추가 (테스트 자동화)
- [ ] `requirements-dev.txt` 분리 (pytest, black, flake8)
- [ ] 최소 Unit Test 5개 이상 작성
- [ ] README에 Demo 스크린샷 추가

### 권장 (Should Have)
- [ ] `CONTRIBUTING.md` 작성
- [ ] Issue Template 추가
- [ ] Pre-commit hook 설정 (black, flake8)
- [ ] Code Coverage Badge 추가
- [ ] Docker Hub에 이미지 배포
- [ ] Railway 실제 배포 후 Live Demo URL 추가

### 선택 (Nice to Have)
- [ ] Swagger UI 커스터마이징
- [ ] API 문서에 Example Response 추가
- [ ] Makefile로 명령어 단순화
- [ ] Postman Collection 추가
- [ ] Architecture Diagram (Mermaid)

---

## 📝 GitHub README 개선 제안

### 현재 README의 문제
1. 너무 길다 (면접관이 1분 안에 파악 불가)
2. Quick Demo가 없다
3. 기술 선택 이유가 없다

### 개선된 구조
```markdown
# 🐕 Biz-Retriever

[![CI](badge)](link) [![Coverage](badge)](link)

> 입찰 정보를 자동 수집하고 AI로 분석하는 지능형 에이전트

[Live Demo](https://...) | [API Docs](https://...)

## 🎯 What & Why

**Problem**: 매일 1~2시간씩 수동으로 입찰 공고를 검색하는 단순 반복 업무
**Solution**: G2B API + AI 필터링 + Slack 알림 자동화
**Impact**: 업무 시간 100% 절감, 놓치는 공고 0%

## 🚀 Quick Demo

```bash
docker-compose up -d
# → http://localhost:8000
```

![Demo GIF](demo.gif)

## 💻 Tech Stack & Why

| 기술 | 선택 이유 |
|------|----------|
| FastAPI | 비동기 처리 + 자동 문서화 |
| Celery | 백그라운드 작업 스케줄링 |
| PostgreSQL | 관계형 데이터 + 확장성 |

## 🏗 Architecture

[Mermaid Diagram]

## 📚 Key Features

- Phase 1: G2B 크롤러 (완료)
- Phase 2: Kanban 관리 (완료)
- Phase 3: AI 투찰가 예측 (완료)

## 🧪 Test

```bash
pytest --cov=app
# Coverage: 82%
```

## 📄 License

MIT
```

---

## 🎯 면접 시 예상 질문 & 답변 준비

### Q1: "왜 FastAPI를 선택했나요?"
**좋은 답변:**
> "비동기 처리가 필수인 크롤링 작업에 적합하고, Swagger 자동 생성으로 API 문서화가 쉽기 때문입니다. Flask보다 성능이 좋고, Django보다 가볍습니다."

**나쁜 답변:**
> "요즘 핫한 기술이라서요."

---

### Q2: "Celery를 왜 썼나요? Cron으로도 되지 않나요?"
**좋은 답변:**
> "Cron은 단순 스케줄링만 가능하지만, Celery는 작업 재시도, 우선순위, 결과 추적이 가능합니다. 또한 수평 확장이 쉬워 트래픽 증가에 대응할 수 있습니다."

---

### Q3: "테스트는 어떻게 하셨나요?"
**현재 답변 (약함):**
> "수동으로 검증 스크립트를 돌렸습니다."

**개선 후 답변 (강함):**
> "pytest로 Unit/Integration 테스트를 작성하고, GitHub Actions로 CI를 구축했습니다. 핵심 비즈니스 로직은 80% 이상 커버합니다."

---

### Q4: "에러가 발생하면 어떻게 처리하나요?"
**현재 답변 (약함):**
> "try-except로 잡아서 로그를 출력합니다."

**개선 후 답변 (강함):**
> "커스텀 Exception 계층을 만들어 에러 타입별로 처리하고, Sentry로 실시간 모니터링합니다. Critical 에러는 Slack으로 즉시 알림을 보냅니다."

---

### Q5: "실제로 배포해봤나요?"
**최고의 답변:**
> "Railway에 배포했고, Celery Beat이 매일 3회 자동 실행됩니다. [Live Demo URL]에서 확인하실 수 있습니다."

---

## 🏆 최종 평가 및 제안

### 현재 점수: B+ (75/100)

### A급(90점 이상)으로 올리는 방법
1. **테스트 추가** (+10점)
   - pytest로 20개 이상 테스트 작성
   - CI/CD 파이프라인 구축
   
2. **실제 배포** (+5점)
   - Railway/Vercel 배포
   - Live Demo URL 제공

3. **보안 강화** (+5점)
   - Rate Limiting
   - CORS 설정
   - 비밀번호 정책

4. **모니터링** (+5점)
   - Sentry 연동
   - Prometheus + Grafana (선택)

---

## 📌 요약: GitHub 공개 전 1일 작업 계획

### Day 1 (4시간)
1. **테스트 작성** (2시간)
   - `test_crawler_service.py`: 필터링 로직 테스트
   - `test_api_endpoints.py`: API 통합 테스트
   
2. **CI/CD 구축** (1시간)
   - GitHub Actions 설정
   - CodeCov 연동

3. **문서화 개선** (1시간)
   - README 간소화
   - Demo 스크린샷 추가
   - LICENSE 파일 추가

### 완료 후 예상 점수: **A- (88/100)**

---

## 💡 결론

**현재 상태:**
- 신입 치고는 **매우 잘 만든** 프로젝트
- 기술 스택과 설계는 **중급 수준**
- 하지만 테스트와 보안은 **아쉬움**

**조언:**
> "완벽한 프로젝트보다, '개선 과정을 보여줄 수 있는' 프로젝트가 면접에서 더 유리합니다. 테스트를 추가하고, GitHub Issues에 'TODO: Rate Limiting 추가' 같은 항목을 남겨두면 '성장 가능성'을 어필할 수 있습니다."

**GitHub 공개 시점:**
- 최소: 테스트 5개 + CI + Demo 스크린샷 추가 후
- 권장: 실제 배포 + Live Demo URL까지 준비 후
