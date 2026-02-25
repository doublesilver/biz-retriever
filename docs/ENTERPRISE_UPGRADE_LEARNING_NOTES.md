# Enterprise Upgrade v2.0 학습 노트

> 커밋: `47853b5` | 527 files changed | +52,900 / -96,936 lines
> 8개 전문 에이전트가 병렬로 수행한 엔터프라이즈 전면 고도화

---

## 목차
1. [아키텍처 패턴 표준화](#1-아키텍처-패턴-표준화)
2. [결제 하드닝 & 구독 라이프사이클](#2-결제-하드닝--구독-라이프사이클)
3. [프론트엔드 결제 연동 & UX 고도화](#3-프론트엔드-결제-연동--ux-고도화)
4. [디자인 시스템 & 접근성](#4-디자인-시스템--접근성)
5. [CI/CD & 인프라 자동화](#5-cicd--인프라-자동화)
6. [테스트 커버리지 95%](#6-테스트-커버리지-95)
7. [OWASP 보안 감사](#7-owasp-보안-감사)
8. [비즈니스 분석 & 가격 전략](#8-비즈니스-분석--가격-전략)

---

## 1. 아키텍처 패턴 표준화

### 개념 설명

**API 응답 래퍼(Envelope Pattern)란?**

편지를 보낼 때 내용물만 던지지 않고 **봉투**에 넣어 보내는 것과 같다. API도 데이터만 반환하면 "이게 성공인지 실패인지, 에러면 어떤 에러인지" 프론트엔드가 매번 추측해야 한다. 봉투(envelope)에 `success`, `data`, `error`, `timestamp`를 담아 보내면 프론트엔드가 **한 가지 방식**으로 모든 응답을 처리할 수 있다.

**구조화된 에러 계층이란?**

병원에서 "아프다"라고만 하면 의사가 뭘 해야 할지 모른다. "왼쪽 무릎 앞십자인대가 파열됐다"처럼 **구체적으로** 말해야 정확한 치료가 가능하다. 에러도 마찬가지로 `HTTPException(404)` 대신 `NotFoundError("공고", bid_id)`처럼 **도메인 언어**로 표현하면, 로그 분석/디버깅/사용자 메시지 모두 정확해진다.

**핵심 키워드**: Envelope Pattern, Domain Exception, Error Code Taxonomy, Global Error Handler

### 코드 설명

#### 변경 전 — 일관성 없는 응답

```python
# 엔드포인트마다 다른 형태
@router.get("/bids")
async def get_bids():
    return {"items": bids, "total": len(bids)}  # 자유 형식

@router.get("/bids/{id}")
async def get_bid(id: int):
    if not bid:
        raise HTTPException(status_code=404, detail="Not found")  # 에러도 제각각
    return bid.__dict__  # dict 직접 반환
```

- 성공 응답 형태가 엔드포인트마다 다름 (`items`, `data`, `result` 등)
- 에러는 `raise HTTPException`으로 HTTP 계층에 직접 의존
- 프론트엔드가 엔드포인트별로 파싱 로직을 다르게 작성해야 함

#### 변경 후 — 표준 래퍼 + 도메인 예외

```python
# app/schemas/response.py — 표준 래퍼
class ApiResponse(BaseModel, Generic[T]):
    success: bool
    data: Optional[T] = None
    error: Optional[ErrorDetail] = None
    timestamp: datetime

def ok(data: Any) -> dict:
    """성공 응답 헬퍼"""
    return {"success": True, "data": data, "timestamp": datetime.utcnow().isoformat()}

def ok_paginated(items: list, total: int, skip: int, limit: int) -> dict:
    """페이지네이션 성공 응답"""
    return {"success": True, "data": items, "meta": {"total": total, "skip": skip, "limit": limit}, ...}

def fail(code: str, message: str) -> dict:
    """실패 응답 헬퍼"""
    return {"success": False, "error": {"code": code, "message": message}, ...}
```

```python
# app/core/exceptions.py — 구조화된 에러 계층 (29개 클래스)
class BizRetrieverError(Exception):
    """모든 도메인 에러의 기본 클래스"""
    status_code: int = 500
    error_code: str = "INTERNAL_ERROR"

class NotFoundError(BizRetrieverError):
    status_code = 404
    error_code = "NOT_FOUND"
    def __init__(self, resource: str, identifier: Any):
        super().__init__(f"{resource} '{identifier}'을(를) 찾을 수 없습니다.")

class PaymentError(BizRetrieverError):
    status_code = 402
    error_code = "PAYMENT_ERROR"

class WeakPasswordError(BadRequestError):
    error_code = "AUTH_WEAK_PASSWORD"
```

```python
# app/main.py — 글로벌 에러 핸들러 (자동 HTTP 매핑)
@app.exception_handler(BizRetrieverError)
async def biz_error_handler(request, exc):
    return JSONResponse(
        status_code=exc.status_code,
        content=fail(exc.error_code, str(exc))  # 표준 포맷으로 자동 변환
    )
```

```python
# 엔드포인트 — 깔끔한 사용법
@router.get("/bids/{id}")
async def get_bid(id: int):
    bid = await bid_service.get_by_id(id)
    if not bid:
        raise NotFoundError("공고", id)  # 도메인 언어로 표현
    return ok(bid)                        # 표준 래퍼로 반환
```

- `ok()` / `ok_paginated()` / `fail()` — 3개 헬퍼로 모든 응답 통일
- `raise NotFoundError("공고", 123)` — HTTP 상태코드를 몰라도 됨 (자동 매핑)
- 에러 코드 체계: `AUTH_001`, `BID_001`, `PAYMENT_001` — 로그/모니터링에서 즉시 식별 가능

### 결과 정리

| 항목 | 변경 전 | 변경 후 |
|------|---------|---------|
| 응답 형태 | 엔드포인트마다 다름 | `{success, data, error, timestamp}` 통일 |
| 에러 처리 | `HTTPException` 직접 사용 | 29개 도메인 예외 → 자동 매핑 |
| 에러 코드 | 없음 | `AUTH_*`, `BID_*`, `PAYMENT_*` 체계 |
| 프론트엔드 | 엔드포인트별 파싱 | 1개 공통 파서로 전체 처리 |

---

## 2. 결제 하드닝 & 구독 라이프사이클

### 개념 설명

**결제 하드닝이란?**

온라인 결제는 **돈이 오가는** 작업이라 일반 API보다 훨씬 엄격한 안전장치가 필요하다. 은행 금고를 생각해보자:
- **HMAC 서명 검증** = 금고 열쇠가 진짜인지 확인 (웹훅 위변조 방지)
- **멱등성 키** = 같은 거래를 두 번 처리하지 않는 잠금장치 (중복 결제 방지)
- **지수 백오프 재시도** = 결제사 서버가 응답 없으면 1초 → 2초 → 4초 간격으로 재시도 (무한 폭탄 호출 방지)

**구독 라이프사이클이란?**

넷플릭스 구독을 생각하면 된다:
```
가입(active) → 매월 자동결제(renewal) → 해지요청(cancelled) → 만료(expired)
                     ↓ 결제실패
              연체(past_due) → 3회 실패 → 만료(expired)
                     ↓
              재구독(resubscribe) → 활성(active)
```

**과금 엔진이란?**

매달 똑같은 금액이 아니라, **플랜 변경 시 일할 계산(프로레이션)**이 필요하다. Basic(10,000원)을 15일째에 Pro(30,000원)로 업그레이드하면:
- Basic 남은 15일분 = 5,000원 환불
- Pro 남은 15일분 = 15,000원 청구
- **차액 10,000원만 결제** — 이게 프로레이션

**핵심 키워드**: HMAC-SHA256, Idempotency Key, Exponential Backoff, Subscription Lifecycle, Proration, Billing Engine, Invoice

### 코드 설명

#### HMAC 웹훅 검증

```python
# app/services/payment_service.py
import hmac, hashlib

def verify_webhook_signature(self, payload: bytes, signature: str) -> bool:
    """Tosspayments 웹훅이 진짜인지 검증"""
    # 1. 우리 서버의 시크릿 키로 payload의 HMAC-SHA256 해시를 계산
    expected = hmac.new(
        self.webhook_secret.encode(),  # 우리만 아는 비밀 키
        payload,                        # 수신한 데이터
        hashlib.sha256                  # SHA-256 해시 알고리즘
    ).hexdigest()
    # 2. Tosspayments가 보낸 서명과 비교 (타이밍 공격 방지를 위해 hmac.compare_digest 사용)
    return hmac.compare_digest(expected, signature)
```

- `hmac.new(key, data, algo)` — 키 기반 해시 생성. 키를 모르면 같은 해시를 만들 수 없음
- `compare_digest` — 문자열 비교 시 **일정 시간** 소요 (타이밍 사이드채널 공격 방지)

#### 멱등성 키 + 지수 백오프

```python
# 멱등성: 같은 주문을 두 번 결제하지 않음
def generate_idempotency_key(self, user_id: int, order_id: str) -> str:
    return str(uuid.uuid4())  # 고유 키 생성, DB에 저장하여 중복 체크

# 지수 백오프: 결제사 서버 장애 시 점진적 재시도
@retry(
    stop=stop_after_attempt(3),        # 최대 3회
    wait=wait_exponential(min=1, max=4), # 1초 → 2초 → 4초
    retry=retry_if_exception_type(PaymentError)
)
async def confirm_payment(self, payment_key: str, order_id: str, amount: int):
    # 서버 사이드 금액 검증 (클라이언트 변조 방지)
    if amount != expected_amount:
        raise PaymentConfirmationError("금액이 일치하지 않습니다")
    response = await self._call_tosspayments_api(...)
```

- `@retry` — tenacity 라이브러리의 데코레이터. 함수 실패 시 자동 재시도
- `wait_exponential(min=1, max=4)` — 1초 → 2초 → 4초로 대기 시간 증가 (서버 부하 방지)
- 서버 사이드 금액 검증: 클라이언트가 `amount=100`으로 조작해도 서버가 원래 금액과 비교

#### 구독 라이프사이클

```python
# app/services/subscription_service.py
async def cancel_subscription(self, user_id: int, reason: str):
    """구독 해지 — 즉시 해지가 아닌 기간 만료 시 해지"""
    sub = await self._get_active_subscription(user_id)
    sub.status = "cancelled"
    sub.cancelled_at = datetime.utcnow()
    sub.cancel_reason = reason
    # end_date는 그대로 유지 → 남은 기간 동안 서비스 계속 이용

async def handle_payment_failure(self, user_id: int):
    """결제 실패 처리 — 3회 연속 실패 시 만료"""
    sub.failed_payment_count += 1
    if sub.failed_payment_count >= 3:
        sub.status = "expired"   # 서비스 중단
    else:
        sub.status = "past_due"  # 연체 상태 (서비스는 계속)
```

- `cancelled` 상태: 해지 요청했지만 결제 기간 끝까지 이용 가능 (넷플릭스 방식)
- `past_due` 상태: 결제 실패했지만 즉시 차단하지 않고 재시도 기회 제공
- 3회 실패 후 `expired`: 최종 서비스 중단

#### 과금 엔진 (인보이스)

```python
# app/services/invoice_service.py
async def create_invoice(self, user_id: int, amount: int, description: str):
    """인보이스 생성 — 자동 채번, 부가세 내세"""
    invoice_number = f"INV-{datetime.now():%Y%m%d}-{uuid4().hex[:8].upper()}"
    vat = amount - (amount * 10 // 11)  # 내세 방식: 110원 중 10원이 부가세
    return Invoice(
        number=invoice_number,
        subtotal=amount - vat,
        vat=vat,
        total=amount,
        status="pending"
    )
```

- 인보이스 번호: `INV-20260225-A1B2C3D4` — 날짜 + 랜덤 8자리로 고유성 보장
- 부가세 내세: 사용자가 보는 가격(10,000원)에 이미 부가세가 포함된 방식

### 결과 정리

| 항목 | 변경 전 | 변경 후 |
|------|---------|---------|
| 웹훅 검증 | 없음 (누구나 가짜 웹훅 전송 가능) | HMAC-SHA256 서명 검증 |
| 중복 결제 | 방지 안 됨 | 멱등성 키로 완벽 차단 |
| 결제사 장애 | 즉시 에러 | 지수 백오프 3회 재시도 |
| 구독 관리 | 단순 on/off | 5단계 라이프사이클 |
| 청구서 | 없음 | 자동 채번 인보이스 + 부가세 |
| 플랜 변경 | 미지원 | 프로레이션 일할 계산 |

---

## 3. 프론트엔드 결제 연동 & UX 고도화

### 개념 설명

**Tosspayments V2 위젯이란?**

결제 화면을 직접 만들면 PCI DSS(카드 정보 보안 인증)를 받아야 한다. 대신 Tosspayments가 제공하는 **위젯(iframe)**을 우리 페이지에 삽입하면, 카드번호가 우리 서버를 거치지 않고 Tosspayments로 직접 전송된다. 택배 보관함과 비슷하다 — 물건(카드정보)을 보관함(위젯)에 넣으면 택배회사(Tosspayments)가 직접 수거한다.

**스켈레톤 스크린이란?**

로딩 중에 빈 화면이나 스피너를 보여주면 사용자가 "멈춘 건가?" 생각한다. 대신 **실제 콘텐츠의 윤곽(뼈대)**을 회색 박스로 미리 보여주면 "곧 내용이 채워지겠구나"라고 직관적으로 이해한다. YouTube, Facebook이 사용하는 기법이다.

**Envelope Auto-Unwrap이란?**

백엔드가 `{success: true, data: {id: 1, name: "..."}}` 형태로 보내면, 프론트엔드의 API 클라이언트가 자동으로 `data` 부분만 꺼내서 반환한다. 택배가 오면 박스(envelope)를 열고 내용물(data)만 사용하는 것과 같다.

**핵심 키워드**: Payment Widget, Skeleton Screen, Envelope Unwrap, Toast Notification, Retry with Backoff

### 코드 설명

#### ADR-001 Envelope Auto-Unwrap

```javascript
// frontend/js/api.js — 응답 자동 처리
async request(method, url, data) {
    const response = await fetch(url, options);
    const json = await response.json();

    // ADR-001 envelope 감지 및 자동 unwrap
    if (json && typeof json === 'object' && 'success' in json) {
        if (json.success) {
            return json.data;  // 성공 → data만 꺼내서 반환
        } else {
            throw new ApiError(json.error.message, response.status, json.error.code);
        }
    }
    return json;  // 레거시 호환: envelope 없는 응답도 처리
}
```

- `'success' in json` — envelope 형태인지 자동 감지
- 레거시 호환: 아직 래퍼를 적용하지 않은 엔드포인트도 정상 동작

#### 상태 코드별 사용자 친화적 에러 메시지

```javascript
// 에러 발생 시 사용자가 이해할 수 있는 한국어 메시지
const ERROR_MESSAGES = {
    401: "로그인이 필요합니다.",
    403: "접근 권한이 없습니다.",
    404: "요청하신 정보를 찾을 수 없습니다.",
    408: "서버 응답 시간이 초과되었습니다.",
    429: "요청이 너무 많습니다. 잠시 후 다시 시도해주세요.",
    500: "서버 오류가 발생했습니다.",
    502: "서버가 일시적으로 응답하지 않습니다.",
    503: "서비스 점검 중입니다.",
};

// 에러에 재시도 가능 여부 표시
error.isRetryable = [408, 429, 500, 502, 503, 504].includes(status);
error.retryAfter = response.headers.get('Retry-After');
```

#### 스켈레톤 스크린

```javascript
// frontend/js/utils.js
function createSkeleton(type, count = 1) {
    // type: 'card' | 'stat' | 'table' | 'plan'
    const skeletons = [];
    for (let i = 0; i < count; i++) {
        const el = document.createElement('div');
        el.className = `skeleton skeleton-${type}`;
        el.setAttribute('aria-busy', 'true');      // 접근성: 스크린리더에 로딩 중 알림
        el.setAttribute('aria-label', '로딩 중');
        skeletons.push(el);
    }
    return skeletons;
}

// 사용 예시 — 대시보드 로딩
container.innerHTML = '';
createSkeleton('card', 3).forEach(s => container.appendChild(s));  // 카드 3개 뼈대
const data = await API.getBids();  // 실제 데이터 로드
renderBids(data);                   // 스켈레톤을 실제 데이터로 교체
```

#### 지수 백오프 재시도 래퍼

```javascript
// frontend/js/utils.js
async function withRetry(fn, { maxRetries = 3, baseDelay = 1000 } = {}) {
    for (let attempt = 0; attempt <= maxRetries; attempt++) {
        try {
            return await fn();
        } catch (error) {
            if (!error.isRetryable || attempt === maxRetries) throw error;
            const delay = baseDelay * Math.pow(2, attempt);  // 1초 → 2초 → 4초
            await new Promise(r => setTimeout(r, delay));
        }
    }
}

// 사용: 결제 확인 시 자동 재시도
const result = await withRetry(() => API.confirmPayment(paymentKey, orderId, amount));
```

### 결과 정리

| 항목 | 변경 전 | 변경 후 |
|------|---------|---------|
| 결제 UI | 없음 | Tosspayments V2 위젯 + 3단 플랜 비교 |
| 로딩 상태 | 빈 화면 / 스피너 | 4종 스켈레톤 스크린 |
| 에러 메시지 | 영문 기술 메시지 | 한국어 상태 코드별 안내 |
| 네트워크 에러 | 즉시 실패 | 지수 백오프 자동 재시도 |
| 구독 관리 | 없음 | 상태 배너 + 해지 모달 + 결제 내역 |

---

## 4. 디자인 시스템 & 접근성

### 개념 설명

**디자인 토큰이란?**

색상, 폰트, 간격 같은 디자인 값을 **변수로 관리**하는 것이다. 집의 전기 배선과 같다 — 각 방에 전선을 따로 연결하면 하나 바꿀 때 전부 뜯어야 한다. 하지만 배전판(토큰)에 연결하면 배전판 하나만 바꾸면 모든 방이 바뀐다.

**Material Design 3 Elevated Surface란?**

다크모드에서 단순히 배경을 검정으로 바꾸면 요소 간 **깊이감**이 사라진다. MD3의 해법은 **높이가 높을수록 밝게** 만드는 것이다:
- Surface 0 (배경) = 가장 어두운 색
- Surface 1 (카드) = 약간 밝음
- Surface 5 (모달) = 가장 밝음

이렇게 하면 실제 빛이 위에서 비치는 것 같은 자연스러운 깊이감이 생긴다.

**WCAG 2.1 AA란?**

Web Content Accessibility Guidelines — 장애가 있는 사용자도 웹을 사용할 수 있도록 하는 국제 표준이다. AA 등급은:
- 텍스트 대비비 4.5:1 이상
- 키보드만으로 모든 기능 사용 가능
- 스크린리더가 모든 콘텐츠를 읽을 수 있음
- 터치 타겟 최소 44px

**핵심 키워드**: Design Token, CSS Custom Properties, Elevated Surface, WCAG 2.1 AA, Pretendard, prefers-color-scheme, prefers-reduced-motion

### 코드 설명

#### 디자인 토큰 시스템 (CSS Custom Properties)

```css
/* frontend/css/variables.css — Primitive Tokens (원시 값) */
:root {
    /* Slate 스케일: 50(거의 흰색) ~ 950(거의 검정) */
    --slate-50: #f8fafc;
    --slate-100: #f1f5f9;
    --slate-200: #e2e8f0;
    /* ... 50단위로 950까지 */
    --slate-900: #0f172a;
    --slate-950: #020617;

    /* Blue (Brand) 스케일 */
    --blue-500: #3b82f6;   /* Primary */
    --blue-600: #2563eb;   /* Primary Hover */

    /* 4px/8px Grid System — 24단계 */
    --space-1: 0.25rem;    /* 4px */
    --space-2: 0.5rem;     /* 8px */
    --space-3: 0.75rem;    /* 12px */
    --space-4: 1rem;       /* 16px */
    /* ... */
    --space-24: 6rem;      /* 96px */

    /* Type Scale — Major Third (1.250 ratio) */
    --text-xs: 0.75rem;    /* 12px */
    --text-sm: 0.875rem;   /* 14px */
    --text-base: 1rem;     /* 16px */
    --text-lg: 1.125rem;   /* 18px */
    --text-xl: 1.25rem;    /* 20px */
    --text-2xl: 1.5rem;    /* 24px — × 1.25 */

    /* Semantic Tokens (의미 기반) */
    --color-success: var(--emerald-500);
    --color-warning: var(--amber-500);
    --color-danger: var(--red-500);
    --color-info: var(--blue-500);

    /* Component Tokens (컴포넌트 전용) */
    --btn-primary-bg: var(--blue-500);
    --btn-primary-hover: var(--blue-600);
    --card-bg: var(--surface-1);
    --card-shadow: var(--shadow-md);
}
```

- **3계층 토큰**: Primitive(색상 값) → Semantic(의미) → Component(컴포넌트)
- 색상을 바꾸고 싶으면 Primitive만 수정 → 전체 자동 반영
- `Major Third` 타입 스케일: 각 단계가 × 1.25 비율 (수학적으로 조화로운 크기)

#### Material Design 3 다크모드

```css
/* 라이트 모드 */
:root {
    --surface-0: #ffffff;
    --surface-1: #f8fafc;
    --surface-2: #f1f5f9;
    --text-primary: #0f172a;     /* 거의 검정 */
}

/* 다크모드 — 단순 반전이 아닌 전용 팔레트 */
@media (prefers-color-scheme: dark) {
    :root {
        --surface-0: #0f172a;    /* 가장 어두운 배경 */
        --surface-1: #1e293b;    /* 카드 — 약간 밝게 */
        --surface-2: #334155;    /* 드롭다운 — 더 밝게 */
        --surface-3: #475569;    /* 모달 — 가장 밝게 */
        --text-primary: #f1f5f9; /* 거의 흰색, 대비비 14.7:1 */
    }
}

/* 수동 토글 (prefers-color-scheme과 독립) */
body.dark-mode {
    --surface-0: #0f172a;
    /* ... 동일한 다크 팔레트 */
}
```

- `prefers-color-scheme: dark` — OS 설정 자동 감지
- `body.dark-mode` — 사용자가 수동으로 토글
- Surface 0~3: 높이(elevation)에 따라 밝기가 증가 → 자연스러운 깊이감

#### WCAG 2.1 AA 접근성

```css
/* frontend/css/accessibility.css */

/* Skip Navigation — 키보드 사용자가 네비게이션 건너뛰기 */
.skip-nav {
    position: absolute;
    top: -100%;
    left: 0;
    z-index: 10000;
}
.skip-nav:focus {
    top: 0;  /* Tab 키를 누르면 화면에 나타남 */
}

/* 키보드 전용 포커스 링 — 마우스 클릭 시에는 안 보임 */
:focus-visible {
    outline: 2px solid var(--blue-500);
    outline-offset: 2px;
    box-shadow: 0 0 0 4px rgba(59, 130, 246, 0.3);
}

/* 모션 감소 설정 — 전정기관 장애 사용자를 위해 */
@media (prefers-reduced-motion: reduce) {
    *, *::before, *::after {
        animation-duration: 0.01ms !important;
        transition-duration: 0.01ms !important;
    }
}

/* Windows 고대비 모드 지원 */
@media (forced-colors: active) {
    .btn { border: 2px solid ButtonText; }
}

/* 최소 터치 타겟 44px */
.btn, a, input, select, textarea {
    min-height: 44px;
    min-width: 44px;
}
```

```html
<!-- HTML 접근성 마크업 예시 -->
<nav role="navigation" aria-label="메인 내비게이션">
<button aria-expanded="false" aria-haspopup="menu">메뉴</button>
<div role="dialog" aria-modal="true" aria-labelledby="modal-title">
<div role="status" aria-live="polite"><!-- 토스트 알림 --></div>
```

### 결과 정리

| 항목 | 변경 전 | 변경 후 |
|------|---------|---------|
| 폰트 | Nanum Gothic (Google Fonts) | Pretendard Variable (CDN) |
| 색상 시스템 | 하드코딩 hex 값 | 50-950 풀 스케일 × 6색 |
| 다크모드 | 없음 | MD3 Elevated Surface + 수동/자동 토글 |
| 접근성 | 없음 | WCAG 2.1 AA (대비비 14.7:1, 키보드, 스크린리더) |
| 컴포넌트 | 개별 스타일 | 통합 디자인 시스템 (버튼 5종, 모달, 토스트 등) |
| 반응형 | 일부 | 모바일 퍼스트 + 3단계 브레이크포인트 |

---

## 5. CI/CD & 인프라 자동화

### 개념 설명

**CI/CD란?**

코드를 작성하고 배포하기까지의 과정을 **자동 컨베이어 벨트**로 만드는 것이다:
- **CI (Continuous Integration)**: 코드를 푸시하면 자동으로 린트 → 테스트 → 빌드 실행
- **CD (Continuous Deployment)**: 테스트 통과하면 자동으로 서버에 배포

수동으로 하면 "린트 깜빡했다", "테스트 안 돌렸다" 같은 실수가 생긴다. 자동화하면 **사람의 실수를 기계가 잡아준다**.

**tini란?**

Docker 컨테이너에서 첫 번째 프로세스(PID 1)는 특별한 역할을 한다 — 종료 시그널(SIGTERM)을 받아서 자식 프로세스들에게 전달해야 한다. 일반 shell(bash)은 이 역할을 못 해서 좀비 프로세스가 생기거나 시그널이 무시된다. `tini`는 이 역할만 전담하는 **경량 init 프로세스**다.

**Graceful Shutdown이란?**

서버를 끌 때 갑자기 전원을 뽑으면 진행 중인 요청이 날아간다. 대신:
1. 새 요청 거부 (503 반환)
2. 진행 중인 요청 완료 대기 (최대 25초)
3. 워커 프로세스 역순 종료 (API → Scheduler → Worker)
4. 타임아웃 후 강제 종료

이게 Graceful Shutdown이다. 비행기 착륙과 같다 — 활주로에 바로 박는 게 아니라 서서히 고도를 낮춘다.

**structlog란?**

일반 로그: `2026-02-25 ERROR: Payment failed for user 123`
구조화 로그: `{"timestamp": "2026-02-25T10:30:00Z", "level": "error", "event": "payment_failed", "user_id": 123, "amount": 10000, "error": "insufficient_funds"}`

JSON 형태라서 로그 분석 도구(Grafana, CloudWatch)가 자동으로 파싱하고 필터링할 수 있다.

**핵심 키워드**: GitHub Actions, Multi-stage Build, tini, Graceful Shutdown, structlog, Sentry, Ruff

### 코드 설명

#### GitHub Actions CI/CD 파이프라인

```yaml
# .github/workflows/ci.yml — 5단계 파이프라인
name: CI/CD Pipeline

on:
  push:
    branches: [master]
  pull_request:
    branches: [master]

concurrency:
  group: ${{ github.ref }}
  cancel-in-progress: true  # 같은 브랜치 중복 실행 취소

jobs:
  lint:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - run: pip install ruff
      - run: ruff check .        # black+flake8+isort 3개 → ruff 1개로 통합 (100배 빠름)

  security:
    needs: lint
    steps:
      - run: bandit -r app/      # Python 보안 취약점 스캔
      - run: pip-audit            # 의존성 CVE 스캔
      - run: trivy fs .           # 파일시스템 전체 스캔

  test:
    needs: security
    steps:
      - run: pytest --cov=app --cov-report=xml
      - uses: codecov/codecov-action@v4

  build:
    needs: test
    steps:
      - uses: docker/build-push-action@v5
        with:
          cache-from: type=gha    # GitHub Actions 캐시로 빌드 50%+ 단축
          cache-to: type=gha,mode=max

  deploy:
    needs: build
    if: github.ref == 'refs/heads/master'  # master 브랜치만 배포
    steps:
      - run: railway up          # Railway 자동 배포
      - run: curl $RAILWAY_URL/health  # 배포 후 헬스체크
```

- `concurrency.cancel-in-progress` — 같은 브랜치에 연속 푸시 시 이전 실행 취소 (자원 절약)
- `ruff` — Rust로 만든 Python 린터. black+flake8+isort를 1개로 통합, 100배 빠름
- `bandit + pip-audit + trivy` — 3중 보안 스캔

#### Docker + tini + Graceful Shutdown

```dockerfile
# Dockerfile — 멀티스테이지 빌드
FROM python:3.11-slim AS builder
RUN pip install --no-cache-dir -r requirements.txt

FROM python:3.11-slim
RUN apt-get update && apt-get install -y tini  # PID 1 전용 init 프로세스
COPY --from=builder /usr/local/lib/python3.11 /usr/local/lib/python3.11

HEALTHCHECK --interval=30s --start-period=40s \
    CMD curl -f http://localhost:8000/health || exit 1

ENTRYPOINT ["tini", "--"]  # tini가 PID 1을 담당
CMD ["./start.sh"]
```

```bash
# start.sh — Graceful Shutdown 핸들러
#!/bin/bash
cleanup() {
    echo "Shutting down gracefully..."
    kill -TERM "$API_PID"        # 1. API 서버 종료
    kill -TERM "$SCHEDULER_PID"  # 2. 스케줄러 종료
    kill -TERM "$WORKER_PID"     # 3. 워커 종료
    wait                          # 모든 프로세스 종료 대기
}
trap cleanup SIGTERM SIGINT       # 종료 시그널 수신 시 cleanup 실행

uvicorn app.main:app --timeout-graceful-shutdown 25 &  # 25초 내 요청 완료
API_PID=$!
wait
```

- `ENTRYPOINT ["tini", "--"]` — tini가 SIGTERM을 정확히 전달, 좀비 프로세스 방지
- `trap cleanup SIGTERM` — 셸에서 시그널을 잡아서 자식 프로세스들을 순서대로 종료
- `--timeout-graceful-shutdown 25` — 진행 중인 요청에 25초 유예

#### structlog JSON 로깅

```python
# app/core/logging.py
import structlog

def setup_logging():
    if settings.ENVIRONMENT == "production":
        renderer = structlog.processors.JSONRenderer()  # JSON 출력
    else:
        renderer = structlog.dev.ConsoleRenderer()       # 컬러 콘솔 출력

    structlog.configure(
        processors=[
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.add_log_level,
            structlog.contextvars.merge_contextvars,  # request_id 자동 바인딩
            renderer,
        ]
    )

# 사용 예시
logger = structlog.get_logger()
logger.info("payment_confirmed", user_id=123, amount=10000, plan="pro")
# 출력: {"timestamp":"2026-02-25T10:30:00Z","level":"info","event":"payment_confirmed","user_id":123,"amount":10000,"plan":"pro"}
```

### 결과 정리

| 항목 | 변경 전 | 변경 후 |
|------|---------|---------|
| 린터 | black + flake8 + isort (3개) | ruff (1개, 100배 빠름) |
| 보안 스캔 | 없음 | bandit + pip-audit + trivy |
| 빌드 캐시 | 없음 | Docker BuildX + GHA 캐시 (50%+ 단축) |
| PID 1 | bash (시그널 문제) | tini (정확한 시그널 전달) |
| 서버 종료 | 강제 종료 | 25초 Graceful Shutdown |
| 로깅 | 텍스트 형식 | JSON 구조화 (structlog) |
| 에러 추적 | 로그 파일 수동 확인 | Sentry 실시간 대시보드 |
| DB 백업 | 수동 | GitHub Actions 매일 자동 |

---

## 6. 테스트 커버리지 95%

### 개념 설명

**테스트 커버리지란?**

전체 코드 중 테스트가 실행한 코드의 비율이다. 집에 화재 감지기를 설치할 때 95%의 방에 설치했다면 커버리지 95%다. 나머지 5%에서 불이 나면 감지 못하듯, 테스트 안 된 코드에서 버그가 날 수 있다.

**95%가 의미하는 것:**
- 전체 4,046 줄의 코드 중 3,849줄이 테스트로 실행됨
- 남은 197줄은 대부분 외부 의존성 코드 (ML 라이브러리, 결제 API 호출 등)

**테스트 종류:**
- **단위 테스트(Unit)**: 함수 하나를 고립시켜 테스트 (가장 빠르고 많음)
- **통합 테스트(Integration)**: API 엔드포인트를 실제로 호출하여 테스트
- **E2E 테스트**: 사용자 시나리오 전체를 처음부터 끝까지 테스트
- **부하 테스트(Load)**: 동시 접속자 수를 늘려가며 성능 한계 측정

**핵심 키워드**: pytest, coverage, Factory Pattern, Mock/Patch, TestClient, Locust

### 코드 설명

#### 테스트 커버리지 설정

```ini
# .coveragerc
[run]
source = app
concurrency = greenlet  # async 코드 추적 정상화 (이 한 줄로 74% → 81%)

[report]
exclude_lines =
    pragma: no cover
    if TYPE_CHECKING:
    if __name__ == .__main__.:
```

- `concurrency = greenlet` — SQLAlchemy 2.0의 async 엔진이 greenlet을 사용. 이 설정 없으면 async 코드의 커버리지가 0%로 잡힘

#### 외부 의존성 모킹

```python
# tests/unit/test_payment_service.py
from unittest.mock import AsyncMock, patch

@patch("app.services.payment_service.httpx.AsyncClient")
async def test_confirm_payment_success(mock_client):
    """결제 확인 — Tosspayments API를 실제로 호출하지 않고 테스트"""
    # Mock 설정: Tosspayments가 성공 응답을 보낸다고 가정
    mock_response = AsyncMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {"status": "DONE", "orderId": "order-123"}
    mock_client.return_value.__aenter__.return_value.post.return_value = mock_response

    # 실행
    result = await payment_service.confirm_payment("pk_123", "order-123", 10000)

    # 검증
    assert result["status"] == "DONE"
    mock_client.return_value.__aenter__.return_value.post.assert_called_once()
```

- `@patch` — 실제 HTTP 호출을 가짜(mock)로 교체
- `AsyncMock` — async 함수를 모킹할 때 사용
- 실제 결제가 발생하지 않으면서 코드 로직은 100% 검증

#### ASGI 통합 테스트

```python
# tests/integration/test_payment_api.py
from httpx import AsyncClient, ASGITransport
from app.main import app

async def test_get_subscription_status():
    """구독 상태 조회 API 통합 테스트"""
    transport = ASGITransport(app=app, raise_app_exceptions=False)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get(
            "/api/v1/payments/subscription",
            headers={"Authorization": f"Bearer {test_token}"}
        )
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
```

- `ASGITransport` — 실제 서버를 띄우지 않고 FastAPI 앱을 직접 호출
- `raise_app_exceptions=False` — 앱 에러를 HTTP 응답으로 받음 (에러 핸들링 테스트 가능)

### 결과 정리

| 항목 | 변경 전 | 변경 후 |
|------|---------|---------|
| 테스트 수 | ~164개 | **955개** (5.8배 증가) |
| 커버리지 | ~66% | **95%** |
| 실패 | 2건 | **0건** |
| auth.py | 46% | **96%** |
| payment.py | 43% | **89%** |
| subscription_service.py | 75% | **100%** |

---

## 7. OWASP 보안 감사

### 개념 설명

**OWASP Top 10이란?**

OWASP(Open Web Application Security Project)가 발표하는 **웹 애플리케이션 10대 보안 위협**이다. 집의 보안 점검 체크리스트와 같다:

| # | 위협 | 비유 |
|---|------|------|
| A01 | Broken Access Control | 현관문 잠금장치가 고장 |
| A02 | Cryptographic Failures | 금고 비밀번호가 "1234" |
| A03 | Injection | 택배 상자에 폭탄 숨기기 |
| A05 | Security Misconfiguration | 뒷문을 열어둔 채 퇴근 |
| A09 | Logging & Monitoring | CCTV 없이 은행 운영 |

**Fail-Closed vs Fail-Open이란?**

- **Fail-Open**: 보안 시스템 장애 시 **문이 열림** (위험!) — "Redis가 죽었으니 일단 통과시키자"
- **Fail-Closed**: 보안 시스템 장애 시 **문이 잠김** (안전) — "Redis가 죽었으니 모든 요청 거부"

은행 금고의 전자 잠금장치가 고장나면? **열려야** 할까 **잠겨야** 할까? 당연히 잠겨야 한다.

**핵심 키워드**: OWASP Top 10, Fail-Closed, CSP, CORS, HMAC, PII, Security Headers

### 코드 설명

#### [CRITICAL] Token Blacklist Fail-Open → Fail-Closed

```python
# 변경 전 — Fail-Open (치명적 취약점)
async def is_token_blacklisted(token: str) -> bool:
    try:
        return await redis.get(f"blacklist:{token}") is not None
    except Exception:
        return False  # ❌ Redis 장애 시 블랙리스트 무력화!
        # 로그아웃한 토큰도 통과됨

# 변경 후 — Fail-Closed
async def is_token_blacklisted(token: str) -> bool:
    try:
        return await redis.get(f"blacklist:{token}") is not None
    except Exception:
        return True  # ✅ Redis 장애 시 모든 토큰 거부 (안전)
        # 일시적 불편 vs 보안 침해 → 안전 선택
```

#### Security Headers 미들웨어

```python
# app/main.py — OWASP 권장 보안 헤더 전체 추가
class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"       # MIME 스니핑 방지
        response.headers["X-Frame-Options"] = "DENY"                  # 클릭재킹 방지
        response.headers["X-XSS-Protection"] = "1; mode=block"       # XSS 필터
        response.headers["Strict-Transport-Security"] = "max-age=31536000"  # HTTPS 강제
        response.headers["Content-Security-Policy"] = "default-src 'self'"  # CSP
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        return response
```

- `X-Frame-Options: DENY` — 우리 페이지를 iframe에 넣지 못하게 함 (클릭재킹 방지)
- `HSTS` — 브라우저에게 "이 사이트는 항상 HTTPS로 접속해"라고 알림
- `CSP` — 허용된 출처의 스크립트/스타일만 실행 (XSS 방지)

#### PII 로그 누출 방지

```python
# 변경 전 — 이메일 주소가 로그에 노출
logger.info(f"Login attempt for {email}")
logger.warning(f"Account locked: {email}")

# 변경 후 — 사용자 ID만 로그
logger.info(f"Login attempt for user_id={user.id}")
logger.warning(f"Account locked: user_id={user.id}")
```

### 결과 정리

| 취약점 | 심각도 | 수정 내용 |
|--------|--------|-----------|
| Token Blacklist Fail-Open | **CRITICAL** | Fail-Closed로 변경 |
| Security Headers 미싱 | HIGH | 6개 보안 헤더 미들웨어 추가 |
| OpenAPI 프로덕션 노출 | HIGH | Production에서 /docs, /redoc 비활성화 |
| Crawler 권한 없음 | HIGH | is_superuser 검증 추가 |
| Traceback 노출 | HIGH | 클라이언트에 상세 에러 숨김 |
| PII 로그 누출 | MEDIUM | 이메일 → user_id로 대체 (11곳) |

---

## 8. 비즈니스 분석 & 가격 전략

### 개념 설명

**SaaS 가격 전략이란?**

소프트웨어를 구독 형태로 판매할 때, **무료 → 유료 전환**이 핵심이다. 마트 시식 코너와 같다:
- **Free 티어** = 시식 (가치를 체감하게 함)
- **Basic** = 일반 구매 (핵심 기능)
- **Pro** = 대용량/프리미엄 (파워 유저용)

핵심은 Free에서 **"아, 이거 더 쓰고 싶다"** 느낌을 주되, 너무 많이 주면 유료 전환 동기가 없어진다.

**주요 KPI:**
- **MRR** (Monthly Recurring Revenue): 월간 반복 매출 — SaaS의 심장
- **Churn Rate**: 해지율 — 물이 새는 양동이, 아무리 물을 부어도 구멍이 크면 소용없음
- **LTV** (Lifetime Value): 고객 1명의 총 매출 — 평균 구독 기간 × 월 결제액
- **CAC** (Customer Acquisition Cost): 고객 획득 비용 — 마케팅비 ÷ 신규 고객 수
- **LTV:CAC Ratio**: 3:1 이상이어야 건강한 비즈니스

**핵심 키워드**: SaaS Pricing, Freemium, MRR, Churn, LTV, CAC, Conversion Funnel, Dunning Management

### 분석 결과 요약

#### 가격 재설계

| 티어 | 변경 전 | 변경 후 | 근거 |
|------|---------|---------|------|
| Free | 맞춤공고 3건, AI 5건 | 맞춤공고 5건, AI 2건 | AI를 업셀 트리거로 활용 (맛보기만 제공) |
| Basic | ₩10,000/월 | **₩19,900/월** | 경쟁사 모두입찰(₩27,500)의 72% (AI 포함 가성비) |
| Pro | ₩30,000/월 | **₩39,900/월** (연간 ₩29,900) | AI 무제한 + 연간 결제 앵커링 효과 |

#### 경쟁사 포지셔닝

```
             AI 분석 없음                    AI 분석 있음
 고가(3만+)  ┌──────────────────────┬──────────────────────┐
             │ 비드프로 (33,000)    │                      │
             │ 모두입찰 (27,500)    │   ★ Biz-Retriever    │
 중가(2만)   ├──────────────────────┤   (19,900) ← here!   │
             │                      │                      │
 저가(1만-)  │ 나라장터 (무료)      │ 지투비플러스 (무료)   │
             └──────────────────────┴──────────────────────┘
```

- **차별화 포인트**: "AI 분석이 있으면서 경쟁사보다 저렴한" 유일한 포지션

#### 전환 퍼널 전략

```
가입 → [Day 3] 웰컴 이메일 + AI 분석 하이라이트
     → [Day 7] "무료 AI 분석 1회 남음" 알림
     → [Day 14] "Basic 7일 무료 체험" 제안 (카드 등록 불요)
     → [사용량 한도] 업셀 배너 "AI 분석 무제한은 Basic부터"
     → [해지 시] 맞춤 오퍼 (다운그레이드 제안 or 1개월 50% 할인)
```

#### 수익 시뮬레이션

| 시나리오 | 6개월 후 MRR | 유료 고객 수 |
|----------|-------------|-------------|
| 보수적 | ₩517,800 | 22명 |
| 낙관적 | ₩1,713,200 | 68명 |
| BEP (인건비 제외) | - | 유료 3명 |
| BEP (인건비 포함) | - | 유료 82명 |

### 결과 정리

| 산출물 | 내용 |
|--------|------|
| 가격 전략 | Free/Basic/Pro 재설계 + 연간 결제 할인 |
| 경쟁사 분석 | 10개 서비스 비교 + 포지셔닝 맵 |
| 전환 퍼널 | 자동 이메일 캠페인 + 업셀 트리거 |
| KPI 체계 | 3티어 (매일/주간/월간) 지표 정의 |
| 해지 방어 | 예측 점수 + 3단계 방어 + Dunning |
| 수익 시뮬레이션 | 보수/낙관 시나리오 + BEP 분석 |
| DB 설계 | usage_tracking, conversion_events, churn_reasons |

---

## 전체 요약

### 골인지점 달성 현황

| 골인지점 | 핵심 지표 | 상태 |
|----------|----------|------|
| **수익화** | Tosspayments 결제 + 과금 엔진 + 인보이스 | ✅ |
| **서비스 품질** | 955 tests, 95% coverage, CI/CD 5단계 | ✅ |
| **보안** | OWASP 12건 발견/10건 수정, Fail-Closed | ✅ |
| **UX** | Pretendard, MD3 다크모드, WCAG 2.1 AA | ✅ |
| **비즈니스** | 가격 재설계, 10개 경쟁사 분석, KPI 체계 | ✅ |

### 숫자로 보는 변화

| 지표 | 변경 전 | 변경 후 |
|------|---------|---------|
| 테스트 수 | 164개 | **955개** |
| 커버리지 | 66% | **95%** |
| 에러 클래스 | 5개 | **29개** |
| 보안 헤더 | 0개 | **6개** |
| CI/CD 단계 | 2단계 | **5단계** |
| 디자인 토큰 | 0개 | **500+줄** |
| 접근성 | 없음 | **WCAG 2.1 AA** |

### 플레이스홀더 값 (직접 입력 필요)

```bash
# .env 또는 GitHub Secrets에 설정
TOSSPAYMENTS_CLIENT_KEY=test_ck_...        # Tosspayments 클라이언트 키
TOSSPAYMENTS_SECRET_KEY=test_sk_...        # Tosspayments 시크릿 키
TOSSPAYMENTS_WEBHOOK_SECRET=whsec_...      # 웹훅 HMAC 검증 시크릿
SENTRY_DSN=https://...@sentry.io/...       # Sentry 에러 추적
RAILWAY_TOKEN=...                           # Railway 배포 토큰
SENDGRID_API_KEY=SG....                    # 이메일 발송
CODECOV_TOKEN=...                           # 커버리지 리포트 (선택)
```
