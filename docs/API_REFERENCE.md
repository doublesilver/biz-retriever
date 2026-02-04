# 📚 Biz-Retriever API Reference

**Version**: 1.0.0  
**Base URL**: `https://sideproject-one.vercel.app`  
**Authentication**: JWT Bearer Token  
**Last Updated**: 2026-02-04

---

## 📋 목차

1. [인증 (Authentication)](#인증-authentication)
2. [공고 관리 (Bids)](#공고-관리-bids)
3. [키워드 관리 (Keywords)](#키워드-관리-keywords)
4. [결제 관리 (Payment)](#결제-관리-payment)
5. [프로필 관리 (Profile)](#프로필-관리-profile)
6. [파일 업로드 (Upload)](#파일-업로드-upload)
7. [웹훅 (Webhooks)](#웹훅-webhooks)
8. [Cron Jobs](#cron-jobs)
9. [에러 코드](#에러-코드)

---

## 🔐 인증 (Authentication)

### 회원가입
회원가입하여 새 계정을 생성합니다.

**Endpoint**: `POST /api/auth?action=register`

**Request**:
```json
{
  "email": "user@example.com",
  "password": "SecurePass123!",
  "name": "홍길동"
}
```

**Response** (201 Created):
```json
{
  "id": 1,
  "email": "user@example.com",
  "name": "홍길동",
  "is_active": true,
  "created_at": "2026-02-04T00:36:29.633739",
  "message": "User registered successfully"
}
```

**Errors**:
- `400 Bad Request`: 이메일 중복
- `422 Unprocessable Entity`: 유효성 검증 실패

---

### 로그인
JWT 토큰을 발급받습니다.

**Endpoint**: `POST /api/auth?action=login`

**Request**:
```json
{
  "email": "user@example.com",
  "password": "SecurePass123!"
}
```

**Response** (200 OK):
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer",
  "user": {
    "id": 1,
    "email": "user@example.com",
    "name": "홍길동"
  }
}
```

**Errors**:
- `401 Unauthorized`: 이메일/비밀번호 불일치

---

### 내 정보 조회
현재 로그인한 사용자 정보를 조회합니다.

**Endpoint**: `GET /api/auth?action=me`  
**Auth**: Required (Bearer Token)

**Request Headers**:
```
Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
```

**Response** (200 OK):
```json
{
  "id": 1,
  "email": "user@example.com",
  "name": "홍길동",
  "is_active": true,
  "created_at": "2026-02-04T00:36:29.633739"
}
```

**Errors**:
- `401 Unauthorized`: 토큰 없음 또는 유효하지 않음

---

## 📄 공고 관리 (Bids)

### 공고 목록 조회
입찰 공고 목록을 페이지네이션과 필터링으로 조회합니다.

**Endpoint**: `GET /api/bids?action=list`  
**Auth**: Required (Bearer Token)

**Query Parameters**:
| 파라미터 | 타입 | 필수 | 기본값 | 설명 |
|---------|------|------|--------|------|
| `page` | int | No | 1 | 페이지 번호 |
| `page_size` | int | No | 20 | 페이지당 항목 수 (최대 100) |
| `keyword` | string | No | - | 제목/내용 검색 |
| `agency` | string | No | - | 기관명 검색 |
| `source` | string | No | - | 출처 필터 (g2b, onbid) |
| `status` | string | No | - | 상태 필터 (new, reviewed, bidding, done) |

**Request Example**:
```bash
curl -X GET "https://sideproject-one.vercel.app/api/bids?action=list&page=1&page_size=10&keyword=AI" \
  -H "Authorization: Bearer YOUR_TOKEN"
```

**Response** (200 OK):
```json
{
  "items": [
    {
      "id": 123,
      "title": "AI 기반 시스템 구축 사업",
      "content": "인공지능 기술을 활용한...",
      "agency": "한국정보화진흥원",
      "posted_at": "2026-02-01T09:00:00",
      "url": "https://g2b.go.kr/...",
      "source": "g2b",
      "deadline": "2026-02-15T18:00:00",
      "estimated_price": 50000000,
      "importance_score": 3,
      "status": "new",
      "created_at": "2026-02-01T09:05:00",
      "updated_at": "2026-02-01T09:05:00"
    }
  ],
  "total": 150,
  "page": 1,
  "page_size": 10,
  "total_pages": 15
}
```

---

### 공고 상세 조회
특정 공고의 상세 정보를 조회합니다 (AI 분석 포함).

**Endpoint**: `GET /api/bids?action=detail&id={bid_id}`  
**Auth**: Required (Bearer Token)

**Request Example**:
```bash
curl -X GET "https://sideproject-one.vercel.app/api/bids?action=detail&id=123" \
  -H "Authorization: Bearer YOUR_TOKEN"
```

**Response** (200 OK):
```json
{
  "id": 123,
  "title": "AI 기반 시스템 구축 사업",
  "content": "인공지능 기술을 활용한 시스템 구축 (전체 내용)...",
  "agency": "한국정보화진흥원",
  "posted_at": "2026-02-01T09:00:00",
  "url": "https://g2b.go.kr/...",
  "processed": true,
  "ai_summary": "AI 기술을 활용한 시스템 구축 사업으로, Python/TensorFlow 경험 필수",
  "ai_keywords": ["AI", "머신러닝", "Python", "TensorFlow"],
  "source": "g2b",
  "deadline": "2026-02-15T18:00:00",
  "estimated_price": 50000000,
  "importance_score": 3,
  "keywords_matched": ["AI", "Python"],
  "is_notified": true,
  "crawled_at": "2026-02-01T09:00:00",
  "attachment_content": null,
  "region_code": "11",
  "min_performance": 30000000,
  "license_requirements": "정보처리기사",
  "status": "new",
  "assigned_to": null,
  "assignee": null,
  "notes": null,
  "created_at": "2026-02-01T09:05:00",
  "updated_at": "2026-02-01T09:05:00"
}
```

**Errors**:
- `400 Bad Request`: ID 파라미터 누락
- `404 Not Found`: 공고를 찾을 수 없음

---

## 🔑 키워드 관리 (Keywords)

### 키워드 목록 조회
사용자가 등록한 키워드 목록을 조회합니다.

**Endpoint**: `GET /api/keywords?action=list`  
**Auth**: Required (Bearer Token)

**Response** (200 OK):
```json
{
  "items": [
    {
      "id": 1,
      "keyword": "AI",
      "category": "include",
      "is_active": true,
      "created_at": "2026-02-04T00:40:18.956086"
    },
    {
      "id": 2,
      "keyword": "블록체인",
      "category": "exclude",
      "is_active": true,
      "created_at": "2026-02-03T15:20:00"
    }
  ],
  "total": 2
}
```

---

### 키워드 생성
새 키워드를 등록합니다.

**Endpoint**: `POST /api/keywords?action=create`  
**Auth**: Required (Bearer Token)

**Request**:
```json
{
  "keyword": "Python",
  "category": "include",
  "is_active": true
}
```

**Response** (201 Created):
```json
{
  "id": 3,
  "keyword": "Python",
  "category": "include",
  "is_active": true,
  "created_at": "2026-02-04T01:00:00",
  "message": "Keyword created successfully"
}
```

**Errors**:
- `400 Bad Request`: 중복 키워드

---

### 키워드 삭제
등록된 키워드를 삭제합니다.

**Endpoint**: `DELETE /api/keywords?action=delete&id={keyword_id}`  
**Auth**: Required (Bearer Token)

**Response** (200 OK):
```json
{
  "message": "Keyword deleted successfully",
  "id": 3
}
```

**Errors**:
- `400 Bad Request`: ID 파라미터 누락
- `404 Not Found`: 키워드를 찾을 수 없음 또는 권한 없음

---

### 제외 키워드 목록 조회
전역 제외 키워드 목록을 조회합니다 (관리자 설정).

**Endpoint**: `GET /api/keywords?action=exclude`  
**Auth**: Required (Bearer Token)

**Response** (200 OK):
```json
{
  "items": [
    {
      "id": 1,
      "word": "불법",
      "is_active": true,
      "created_at": "2026-01-01T00:00:00"
    }
  ],
  "total": 1
}
```

---

## 💳 결제 관리 (Payment)

### 구독 정보 조회
현재 사용자의 구독 정보를 조회합니다.

**Endpoint**: `GET /api/payment?action=subscription`  
**Auth**: Required (Bearer Token)

**Response** (200 OK):
```json
{
  "id": 5,
  "plan_name": "pro",
  "is_active": true,
  "stripe_subscription_id": "sub_1234567890",
  "start_date": "2026-01-01T00:00:00",
  "next_billing_date": "2026-02-01T00:00:00",
  "created_at": "2026-01-01T00:00:00",
  "updated_at": "2026-01-01T00:00:00"
}
```

**Response (Free Plan)**:
```json
{
  "plan_name": "free",
  "is_active": true,
  "start_date": null,
  "next_billing_date": null,
  "message": "No active subscription. Using free plan."
}
```

---

### 결제 내역 조회
사용자의 결제 내역을 페이지네이션으로 조회합니다.

**Endpoint**: `GET /api/payment?action=history`  
**Auth**: Required (Bearer Token)

**Query Parameters**:
| 파라미터 | 타입 | 필수 | 기본값 | 설명 |
|---------|------|------|--------|------|
| `page` | int | No | 1 | 페이지 번호 |
| `page_size` | int | No | 20 | 페이지당 항목 수 (최대 100) |

**Response** (200 OK):
```json
{
  "items": [
    {
      "id": 1,
      "amount": 29000,
      "currency": "KRW",
      "status": "completed",
      "payment_method": "card",
      "transaction_id": "txn_1234567890",
      "description": "Pro Plan - Monthly",
      "created_at": "2026-01-01T00:00:00",
      "updated_at": "2026-01-01T00:00:05"
    }
  ],
  "total": 12,
  "page": 1,
  "page_size": 20,
  "total_pages": 1
}
```

---

### 결제 상태 조회
특정 결제 건의 상태를 조회합니다.

**Endpoint**: `GET /api/payment?action=status&payment_id={transaction_id}`  
**Auth**: Required (Bearer Token)

**Response** (200 OK):
```json
{
  "id": 1,
  "amount": 29000,
  "currency": "KRW",
  "status": "completed",
  "payment_method": "card",
  "transaction_id": "txn_1234567890",
  "description": "Pro Plan - Monthly",
  "created_at": "2026-01-01T00:00:00",
  "updated_at": "2026-01-01T00:00:05"
}
```

**Errors**:
- `400 Bad Request`: payment_id 파라미터 누락
- `404 Not Found`: 결제 내역을 찾을 수 없음

---

## 👤 프로필 관리 (Profile)

### 프로필 조회
사용자의 기업 프로필을 조회합니다.

**Endpoint**: `GET /api/profile?action=get`  
**Auth**: Required (Bearer Token)

**Response** (200 OK):
```json
{
  "id": 2,
  "company_name": "Test Company Ltd.",
  "brn": "123-45-67890",
  "location_code": "11",
  "keywords": null,
  "credit_rating": "AAA",
  "created_at": "2026-02-04T00:42:57.031683",
  "updated_at": "2026-02-04T00:55:56.881320"
}
```

**Response (No Profile)**:
```json
{
  "profile": null,
  "message": "Profile not found. Please create a profile first."
}
```

---

### 프로필 생성
새 기업 프로필을 생성합니다.

**Endpoint**: `POST /api/profile?action=create`  
**Auth**: Required (Bearer Token)

**Request**:
```json
{
  "company_name": "Test Company Ltd.",
  "brn": "123-45-67890",
  "location_code": "11",
  "keywords": "AI, Python, FastAPI",
  "credit_rating": "A+"
}
```

**Response** (201 Created):
```json
{
  "id": 2,
  "company_name": "Test Company Ltd.",
  "brn": "123-45-67890",
  "location_code": "11",
  "keywords": "AI, Python, FastAPI",
  "credit_rating": "A+",
  "created_at": "2026-02-04T00:42:57.031683",
  "message": "Profile created successfully"
}
```

**Errors**:
- `400 Bad Request`: 프로필이 이미 존재함

---

### 프로필 수정
기존 프로필을 수정합니다 (부분 업데이트 지원).

**Endpoint**: `PUT /api/profile?action=update`  
**Auth**: Required (Bearer Token)

**Request** (일부 필드만 수정 가능):
```json
{
  "company_name": "Updated Company Name",
  "credit_rating": "AAA"
}
```

**Response** (200 OK):
```json
{
  "id": 2,
  "company_name": "Updated Company Name",
  "brn": "123-45-67890",
  "location_code": "11",
  "keywords": "AI, Python, FastAPI",
  "credit_rating": "AAA",
  "updated_at": "2026-02-04T00:55:56.881320",
  "message": "Profile updated successfully"
}
```

**Errors**:
- `400 Bad Request`: 프로필이 존재하지 않음 (create 필요)

---

### 보유 면허 조회
사용자 프로필에 등록된 면허 목록을 조회합니다.

**Endpoint**: `GET /api/profile?action=licenses`  
**Auth**: Required (Bearer Token)

**Response** (200 OK):
```json
{
  "items": [
    {
      "id": 1,
      "license_name": "정보처리기사",
      "license_number": "12345678",
      "issue_date": "2020-05-15",
      "expiry_date": null,
      "issuing_agency": "한국산업인력공단",
      "created_at": "2026-02-01T10:00:00"
    }
  ],
  "total": 1
}
```

---

### 시공 실적 조회
사용자 프로필에 등록된 시공/용역 실적을 조회합니다.

**Endpoint**: `GET /api/profile?action=performances`  
**Auth**: Required (Bearer Token)

**Response** (200 OK):
```json
{
  "items": [
    {
      "id": 1,
      "project_name": "서울시청 AI 시스템 구축",
      "client_name": "서울특별시",
      "amount": 50000000,
      "start_date": "2025-01-01",
      "completion_date": "2025-06-30",
      "project_type": "용역",
      "location": "서울",
      "description": "AI 기반 민원 처리 시스템",
      "created_at": "2026-02-01T10:00:00"
    }
  ],
  "total": 1
}
```

---

## 📤 파일 업로드 (Upload)

### PDF 업로드 및 AI 분석
PDF 파일을 업로드하고 Gemini AI로 내용을 추출합니다.

**Endpoint**: `POST /api/upload`  
**Auth**: Required (Bearer Token)  
**Content-Type**: `multipart/form-data`

**Request** (Form Data):
```
file: [PDF File]
```

**Request Example** (curl):
```bash
curl -X POST https://sideproject-one.vercel.app/api/upload \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -F "file=@document.pdf"
```

**Response** (200 OK):
```json
{
  "success": true,
  "profile": {
    "company_name": "주식회사 ABC",
    "brn": "123-45-67890",
    "licenses": ["정보처리기사", "건축기사"],
    "performances": [
      {
        "project_name": "서울시청 시스템 구축",
        "amount": 50000000,
        "completion_date": "2025-06-30"
      }
    ]
  },
  "message": "PDF processed and profile updated successfully"
}
```

**Errors**:
- `400 Bad Request`: 파일 없음 또는 PDF가 아님
- `413 Payload Too Large`: 파일 크기 초과 (최대 10MB)

---

## 🔔 웹훅 (Webhooks)

### Tosspayments 결제 웹훅
Tosspayments에서 결제 이벤트 발생 시 호출됩니다.

**Endpoint**: `POST /api/webhooks`  
**Auth**: HMAC-SHA256 Signature Verification

**Request Headers**:
```
X-Signature: HMAC-SHA256 signature
Content-Type: application/json
```

**Request**:
```json
{
  "event": "payment.completed",
  "orderId": "order_1234567890",
  "paymentKey": "txn_abcdefg",
  "amount": 29000,
  "status": "DONE"
}
```

**Response** (200 OK):
```json
{
  "success": true,
  "message": "Webhook processed successfully"
}
```

**Errors**:
- `401 Unauthorized`: Signature 검증 실패
- `400 Bad Request`: 유효하지 않은 요청

---

## ⏰ Cron Jobs

### G2B 크롤링
나라장터 공고를 크롤링합니다 (하루 3회 실행).

**Endpoint**: `GET /api/cron/crawl-g2b`  
**Auth**: `Authorization: Bearer CRON_SECRET`  
**Schedule**: 08:00, 12:00, 18:00 KST

**Response** (200 OK):
```json
{
  "status": "success",
  "total_fetched": 150,
  "total_new": 12,
  "total_duplicates": 138,
  "duration_seconds": 45
}
```

---

### 모닝 브리핑
전날 수집한 공고를 Slack으로 전송합니다.

**Endpoint**: `GET /api/cron/morning-digest`  
**Auth**: `Authorization: Bearer CRON_SECRET`  
**Schedule**: 08:30 KST

**Response** (200 OK):
```json
{
  "status": "success",
  "notifications_sent": 5,
  "message": "Morning digest sent successfully"
}
```

---

### 구독 갱신
만료된 구독을 갱신합니다.

**Endpoint**: `GET /api/cron/renew-subscriptions`  
**Auth**: `Authorization: Bearer CRON_SECRET`  
**Schedule**: 00:00 KST

**Response** (200 OK):
```json
{
  "status": "success",
  "renewed_count": 3,
  "message": "Subscriptions renewed successfully"
}
```

---

## ⚠️ 에러 코드

| 코드 | 의미 | 설명 |
|------|------|------|
| `200` | OK | 성공 |
| `201` | Created | 리소스 생성 성공 |
| `400` | Bad Request | 잘못된 요청 (파라미터 누락, 중복 등) |
| `401` | Unauthorized | 인증 실패 (토큰 없음/유효하지 않음) |
| `404` | Not Found | 리소스를 찾을 수 없음 |
| `413` | Payload Too Large | 파일 크기 초과 |
| `422` | Unprocessable Entity | 유효성 검증 실패 (Pydantic) |
| `500` | Internal Server Error | 서버 내부 오류 |

### 에러 응답 형식
```json
{
  "error": true,
  "message": "Error description",
  "status_code": 400,
  "details": {
    "field": "email",
    "error": "Email already registered"
  }
}
```

---

## 🔧 Rate Limiting

현재 Vercel Hobby 플랜에서는 Rate Limiting이 적용되지 않습니다.

향후 Pro 플랜 업그레이드 시 다음 제한이 적용될 예정:
- **인증 API**: 5 req/분
- **일반 API**: 100 req/분
- **Cron API**: CRON_SECRET 인증 필수

---

## 📞 지원

**문제 신고**: GitHub Issues  
**이메일**: support@biz-retriever.com  
**문서 업데이트**: 2026-02-04

---

**Made with ❤️ by Biz-Retriever Team**
