# Biz-Retriever API Reference

**Version**: 2.0 (Serverless)
**Base URL**: `https://your-api.vercel.app`
**Authentication**: JWT Bearer Token

---

## Table of Contents

1. [Authentication](#authentication)
2. [Bids](#bids)
3. [Profile](#profile)
4. [Keywords](#keywords)
5. [Payment](#payment)
6. [Upload](#upload)
7. [Webhooks](#webhooks)
8. [Cron Jobs](#cron-jobs)
9. [Error Codes](#error-codes)

---

## Authentication

### Register
```http
POST /api/auth/register
Content-Type: application/json

{
  "email": "user@example.com",
  "password": "SecurePass123!",
  "company_name": "테스트 회사"
}
```

**Response** (201):
```json
{
  "access_token": "eyJhbGc...",
  "token_type": "bearer",
  "expires_in": 3600
}
```

### Login
```http
POST /api/auth/login
Content-Type: application/json

{
  "email": "user@example.com",
  "password": "SecurePass123!"
}
```

**Response** (200):
```json
{
  "access_token": "eyJhbGc...",
  "token_type": "bearer",
  "expires_in": 3600
}
```

### Get Current User
```http
GET /api/auth/me
Authorization: Bearer eyJhbGc...
```

**Response** (200):
```json
{
  "id": 1,
  "email": "user@example.com",
  "company_name": "테스트 회사",
  "plan": "basic",
  "created_at": "2026-02-03T12:00:00Z"
}
```

---

## Bids

### List Bids
```http
GET /api/bids/list?page=1&limit=20&keyword=시설&agency=서울시
Authorization: Bearer eyJhbGc...
```

**Query Parameters**:
- `page` (int, optional): Page number (default: 1)
- `limit` (int, optional): Items per page (default: 20, max: 100)
- `keyword` (string, optional): Search keyword
- `agency` (string, optional): Filter by agency
- `source` (string, optional): g2b | onbid
- `status` (string, optional): active | closed

**Response** (200):
```json
{
  "items": [
    {
      "id": 123,
      "title": "2026년 공공 시설 관리 용역",
      "agency": "서울특별시",
      "estimated_price": 50000000,
      "deadline": "2026-03-15",
      "importance_score": 3,
      "ai_summary": "서울시 공공시설 관리 용역 입찰"
    }
  ],
  "total": 150,
  "page": 1,
  "page_size": 20,
  "total_pages": 8
}
```

### Get Bid Detail
```http
GET /api/bids/123
Authorization: Bearer eyJhbGc...
```

**Response** (200):
```json
{
  "id": 123,
  "title": "2026년 공공 시설 관리 용역",
  "agency": "서울특별시",
  "content": "입찰 공고 상세 내용...",
  "estimated_price": 50000000,
  "deadline": "2026-03-15T23:59:59Z",
  "region_code": "11000",
  "license_requirements": ["건설업"],
  "min_performance": 30000000,
  "importance_score": 3,
  "ai_summary": "서울시 공공시설 관리 용역 입찰",
  "ai_keywords": ["시설관리", "용역", "서울시"],
  "created_at": "2026-02-01T10:00:00Z"
}
```

### Analyze Bid (RAG)
```http
POST /api/bids/123/analyze
Authorization: Bearer eyJhbGc...
```

**Response** (200):
```json
{
  "id": 123,
  "ai_summary": "서울시 공공시설 관리 용역 입찰",
  "ai_keywords": ["시설관리", "용역", "서울시"],
  "region_code": "11000",
  "license_requirements": ["건설업"],
  "min_performance": 30000000,
  "analyzed_at": "2026-02-03T22:00:00Z"
}
```

### Get Matched Bids (Hard Match)
```http
GET /api/bids/matched?sort_by=deadline&page=1&limit=20
Authorization: Bearer eyJhbGc...
```

**Query Parameters**:
- `sort_by` (string, optional): deadline | price | importance_score (default: deadline)
- `page` (int, optional): Page number
- `limit` (int, optional): Items per page

**Response** (200):
```json
{
  "items": [...],
  "total": 10,
  "limit": 3,
  "plan": "free",
  "page": 1,
  "page_size": 20,
  "total_pages": 1
}
```

---

## Profile

### Get Profile
```http
GET /api/profile
Authorization: Bearer eyJhbGc...
```

**Response** (200):
```json
{
  "id": 1,
  "company_name": "테스트 회사",
  "brn": "123-45-67890",
  "representative": "홍길동",
  "address": "서울특별시 강남구...",
  "location_code": "11000",
  "licenses": [
    {
      "id": 1,
      "license_name": "건설업",
      "license_number": "2024-1234",
      "issue_date": "2024-01-01"
    }
  ],
  "performances": [
    {
      "id": 1,
      "project_name": "OO 공사",
      "amount": 50000000,
      "completion_date": "2025-12-31"
    }
  ]
}
```

### Update Profile
```http
PUT /api/profile
Authorization: Bearer eyJhbGc...
Content-Type: application/json

{
  "company_name": "새로운 회사명",
  "representative": "김철수",
  "address": "서울특별시 서초구..."
}
```

**Response** (200):
```json
{
  "success": true,
  "profile": {...}
}
```

### Add License
```http
POST /api/profile/licenses
Authorization: Bearer eyJhbGc...
Content-Type: application/json

{
  "license_name": "건설업",
  "license_number": "2024-1234",
  "issue_date": "2024-01-01"
}
```

**Response** (201):
```json
{
  "id": 2,
  "license_name": "건설업",
  "license_number": "2024-1234",
  "issue_date": "2024-01-01"
}
```

### Delete License
```http
DELETE /api/profile/licenses/2
Authorization: Bearer eyJhbGc...
```

**Response** (200):
```json
{
  "success": true,
  "message": "License deleted"
}
```

### Add Performance
```http
POST /api/profile/performances
Authorization: Bearer eyJhbGc...
Content-Type: application/json

{
  "project_name": "OO 공사",
  "amount": 50000000,
  "completion_date": "2025-12-31"
}
```

**Response** (201):
```json
{
  "id": 2,
  "project_name": "OO 공사",
  "amount": 50000000,
  "completion_date": "2025-12-31"
}
```

### Delete Performance
```http
DELETE /api/profile/performances/2
Authorization: Bearer eyJhbGc...
```

**Response** (200):
```json
{
  "success": true,
  "message": "Performance deleted"
}
```

### Update Region
```http
PUT /api/profile/region
Authorization: Bearer eyJhbGc...
Content-Type: application/json

{
  "location_code": "11000"
}
```

**Response** (200):
```json
{
  "success": true,
  "location_code": "11000"
}
```

---

## Keywords

### List Keywords
```http
GET /api/keywords
Authorization: Bearer eyJhbGc...
```

**Response** (200):
```json
{
  "keywords": [
    {
      "id": 1,
      "text": "시설관리",
      "category": "include",
      "created_at": "2026-02-01T10:00:00Z"
    }
  ],
  "total": 5,
  "limit": 5,
  "plan": "free"
}
```

### Add Keyword
```http
POST /api/keywords
Authorization: Bearer eyJhbGc...
Content-Type: application/json

{
  "text": "건설",
  "category": "include"
}
```

**Response** (201):
```json
{
  "id": 2,
  "text": "건설",
  "category": "include",
  "created_at": "2026-02-03T22:00:00Z"
}
```

**Error** (403 - Limit Exceeded):
```json
{
  "detail": "Keyword limit reached for Free plan (5/5)"
}
```

### Delete Keyword
```http
DELETE /api/keywords/2
Authorization: Bearer eyJhbGc...
```

**Response** (200):
```json
{
  "success": true,
  "message": "Keyword deleted"
}
```

### List Exclude Keywords
```http
GET /api/keywords/exclude
Authorization: Bearer eyJhbGc...
```

**Response** (200):
```json
{
  "keywords": [
    {
      "id": 1,
      "text": "폐기물",
      "category": "exclude"
    }
  ]
}
```

---

## Payment

### Create Payment
```http
POST /api/payment/create
Authorization: Bearer eyJhbGc...
Content-Type: application/json

{
  "plan": "basic",
  "payment_method": "card"
}
```

**Response** (201):
```json
{
  "orderId": "20260203220000-USER1",
  "amount": 9900,
  "client_key": "test_ck_...",
  "checkout_url": "https://tosspayments.com/..."
}
```

### Confirm Payment
```http
POST /api/payment/confirm
Authorization: Bearer eyJhbGc...
Content-Type: application/json

{
  "orderId": "20260203220000-USER1",
  "paymentKey": "tviva20231201...",
  "amount": 9900
}
```

**Response** (200):
```json
{
  "success": true,
  "subscription": {
    "plan_name": "basic",
    "is_active": true,
    "start_date": "2026-02-03T22:00:00Z",
    "next_billing_date": "2026-03-03T22:00:00Z"
  }
}
```

### Get Payment Status
```http
GET /api/payment/status?orderId=20260203220000-USER1
Authorization: Bearer eyJhbGc...
```

**Response** (200):
```json
{
  "orderId": "20260203220000-USER1",
  "status": "paid",
  "amount": 9900,
  "payment_method": "card",
  "created_at": "2026-02-03T22:00:00Z"
}
```

### Register Billing Key (Auto-renewal)
```http
POST /api/payment/billing-key
Authorization: Bearer eyJhbGc...
Content-Type: application/json

{
  "customerKey": "USER_1",
  "authKey": "billing_auth_key_..."
}
```

**Response** (200):
```json
{
  "billingKey": "billing_key_...",
  "card_info": {
    "number": "1234-****-****-5678",
    "type": "신용"
  }
}
```

---

## Upload

### Upload PDF (Business Registration Certificate)
```http
POST /api/upload/pdf
Authorization: Bearer eyJhbGc...
Content-Type: multipart/form-data

file: (binary PDF data)
```

**Response** (200):
```json
{
  "success": true,
  "extracted": {
    "company_name": "테스트 회사",
    "brn": "123-45-67890",
    "representative": "홍길동",
    "address": "서울특별시 강남구..."
  },
  "profile_updated": true,
  "message": "Business registration certificate processed successfully"
}
```

**Error** (413 - File Too Large):
```json
{
  "detail": "File size exceeds 10MB limit"
}
```

---

## Webhooks

### Tosspayments Webhook
```http
POST /api/webhooks/tosspayments
Content-Type: application/json
X-Tosspayments-Signature: hmac-sha256-signature

{
  "eventType": "payment.confirmed",
  "orderId": "20260203220000-USER1",
  "paymentKey": "tviva20231201...",
  "status": "DONE",
  "totalAmount": 9900
}
```

**Response** (200):
```json
{
  "success": true,
  "message": "Webhook processed"
}
```

---

## Cron Jobs

**Note**: All cron jobs require `CRON_SECRET` in Authorization header.

### Crawl G2B
```http
GET /api/cron/crawl-g2b
Authorization: Bearer {CRON_SECRET}
```

**Response** (200):
```json
{
  "success": true,
  "message": "Crawling completed successfully",
  "stats": {
    "total_crawled": 50,
    "new_saved": 30,
    "duplicates_skipped": 20,
    "notifications_sent": 5
  }
}
```

### Crawl OnBid
```http
GET /api/cron/crawl-onbid
Authorization: Bearer {CRON_SECRET}
```

### Morning Digest
```http
GET /api/cron/morning-digest
Authorization: Bearer {CRON_SECRET}
```

### Renew Subscriptions
```http
GET /api/cron/renew-subscriptions
Authorization: Bearer {CRON_SECRET}
```

**Response** (200):
```json
{
  "success": true,
  "processed": 10,
  "renewed": 8,
  "failed": 2,
  "canceled": 0,
  "elapsed_seconds": 12.34
}
```

---

## Error Codes

| Code | Meaning | Description |
|------|---------|-------------|
| 200 | OK | Request successful |
| 201 | Created | Resource created |
| 400 | Bad Request | Invalid input data |
| 401 | Unauthorized | Missing or invalid JWT token |
| 403 | Forbidden | Permission denied (e.g., plan limit exceeded) |
| 404 | Not Found | Resource not found |
| 409 | Conflict | Duplicate resource (e.g., duplicate orderId) |
| 413 | Payload Too Large | File size exceeds limit |
| 500 | Internal Server Error | Server error |

### Error Response Format
```json
{
  "detail": "Error message describing what went wrong"
}
```

---

## Rate Limiting

**Free Plan**:
- 100 requests/hour
- 1,000 requests/day

**Basic Plan**:
- 1,000 requests/hour
- 10,000 requests/day

**Pro Plan**:
- 10,000 requests/hour
- 100,000 requests/day

**429 Too Many Requests**:
```json
{
  "detail": "Rate limit exceeded. Try again in 60 seconds."
}
```

---

## Pagination

All list endpoints support pagination:

**Query Parameters**:
- `page` (int): Page number (default: 1)
- `limit` (int): Items per page (default: 20, max: 100)

**Response Format**:
```json
{
  "items": [...],
  "total": 150,
  "page": 1,
  "page_size": 20,
  "total_pages": 8
}
```

---

## Examples

### Complete User Journey

```bash
# 1. Register
curl -X POST https://your-api.vercel.app/api/auth/register \
  -H "Content-Type: application/json" \
  -d '{"email":"user@example.com","password":"SecurePass123!","company_name":"테스트 회사"}'

# 2. Login
TOKEN=$(curl -X POST https://your-api.vercel.app/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"user@example.com","password":"SecurePass123!"}' \
  | jq -r '.access_token')

# 3. Update Profile
curl -X PUT https://your-api.vercel.app/api/profile/region \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"location_code":"11000"}'

# 4. Add Keywords
curl -X POST https://your-api.vercel.app/api/keywords \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"text":"시설관리","category":"include"}'

# 5. Get Matched Bids
curl -X GET "https://your-api.vercel.app/api/bids/matched?limit=3" \
  -H "Authorization: Bearer $TOKEN"

# 6. Subscribe to Basic Plan
curl -X POST https://your-api.vercel.app/api/payment/create \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"plan":"basic","payment_method":"card"}'
```

---

**Last Updated**: 2026-02-03
**API Version**: 2.0 (Serverless)
**Support**: https://github.com/doublesilver/biz-retriever/issues
