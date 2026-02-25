# Biz-Retriever 비즈니스 분석 보고서
# 가격 전략 최적화 및 KPI/전환 퍼널 설계

> **작성일**: 2026-02-24
> **작성자**: Business Analyst (Enterprise Upgrade Team)
> **버전**: v2.0 (BUSINESS_ASSESSMENT.md 후속 보고서)
> **대상**: 프로젝트 오너, 기술 리드

---

## 목차

1. [Executive Summary](#1-executive-summary)
2. [현재 상태 분석](#2-현재-상태-분석)
3. [경쟁사 분석](#3-경쟁사-분석)
4. [가격 전략 최적화](#4-가격-전략-최적화)
5. [전환 퍼널 설계](#5-전환-퍼널-설계)
6. [KPI 체계 정의](#6-kpi-체계-정의)
7. [해지 방어 전략](#7-해지-방어-전략)
8. [랜딩페이지/온보딩 개선](#8-랜딩페이지온보딩-개선)
9. [수익 대시보드 데이터 모델](#9-수익-대시보드-데이터-모델)
10. [실행 로드맵](#10-실행-로드맵)

---

## 1. Executive Summary

### 핵심 제안 요약

| 항목 | 현재 | 제안 | 근거 |
|------|------|------|------|
| **Free 티어** | 맞춤공고 3건/일 | 맞춤공고 5건/일 + AI 분석 2건/일 | 가치 체감 최소 기준점 |
| **Basic** | 10,000원/월 | 19,900원/월 | 경쟁사 대비 가격 경쟁력 유지 |
| **Pro** | 30,000원/월 | 39,900원/월 (연간 결제 시 29,900원) | 모두입찰 27,500원 대비 AI 분석 프리미엄 |
| **전환율 목표** | 0% (사용자 없음) | Free->Basic 5%, Basic->Pro 15% | B2B SaaS 업계 중간값 |
| **BEP** | 미달성 | 유료 고객 15명 | 월 고정비 50만원 기준 |

### 전략 방향

Biz-Retriever는 **AI 분석이라는 명확한 기술적 차별점**을 보유하고 있으나, 현재 가격 체계가 이 가치를 적절히 반영하지 못하고 있다. 본 보고서는 다음 세 가지를 제안한다:

1. **Free 티어 강화** - 가치 체감을 위한 최소 기능 확대 (3건 -> 5건)
2. **Basic/Pro 가격 인상** - AI 분석 프리미엄 반영 + 연간 결제 할인으로 LTV 극대화
3. **전환 퍼널 자동화** - 사용량 기반 업셀 트리거 + 해지 방어 메커니즘

---

## 2. 현재 상태 분석

### 2.1 현재 가격 체계

```
app/services/subscription_service.py:31-47 (현재 구현)

Free:   hard_match 3건/일, AI 분석 5건/일, 키워드 5개
Basic:  hard_match 50건/일, AI 분석 100건/일, 키워드 20개 (10,000원/월)
Pro:    hard_match 무제한, AI 분석 무제한, 키워드 100개 (30,000원/월)
```

### 2.2 현재 기능 매트릭스

| 기능 | 구현 상태 | 가치 수준 |
|------|-----------|-----------|
| G2B 자동 크롤링 (3회/일) | 완료 | 핵심 가치 |
| Gemini AI 분석 (요약/키워드/중요도) | 완료 | **최대 차별점** |
| Hard Match (지역/면허/실적) | 완료 | 핵심 가치 |
| Slack 알림 | 완료 | 부가 가치 |
| 웹 대시보드 + 통계 | 완료 | 기본 가치 |
| 칸반 보드 | 부분 완료 | 부가 가치 |
| Excel Export | 완료 | 부가 가치 |
| 기업 프로필 (사업자등록증 AI 추출) | 완료 | 부가 가치 |
| 면허/실적 관리 | 완료 | 핵심 가치 |
| Tosspayments 결제 | 구현됨 (미검증) | 수익화 필수 |

### 2.3 기술 비용 구조

| 항목 | 월 비용 | 비고 |
|------|---------|------|
| Gemini API | 0원 | 무료 티어 1,500 req/일 (충분) |
| Vercel (Frontend) | 0원 | Free tier |
| Raspberry Pi 서버 | ~5,000원 | 전기료 |
| 도메인 | ~1,000원 | 연 12,000원 / 12 |
| Railway (이전 예정) | ~5,000원 | Hobby plan $5/월 |
| **합계** | **~11,000원** | 사용자 0명 기준 |

**스케일링 비용 변곡점**: Gemini API 무료 한도(1,500 req/일) 초과 시 유료 전환 필요. 유료 사용자 약 100명 기준으로 발생 예상.

---

## 3. 경쟁사 분석

### 3.1 한국 공공입찰 정보 서비스 시장

한국 공공입찰 정보 시장은 약 10개 이상의 사업자가 경쟁하는 성숙 시장이다.

| 서비스 | 설립 | 월 요금 | 연간 할인 | 핵심 기능 | AI 분석 |
|--------|------|---------|-----------|-----------|---------|
| **모두입찰** | - | 27,500원 | 33% (12개월) | 빅데이터 낙찰가 예측(특허), 1:1 컨설팅 | 없음 |
| **비드프로** | 2002 | 22,000~33,000원 | 있음 | 낙찰 컨설팅, 입찰 대행 | 없음 |
| **딥비드** | - | 무료~유료 | - | 빅데이터 기반, 기관/기업 분석 | 제한적 |
| **비드메이트** | - | 프리미엄 | - | 전자입찰 상위 1% 분석 | 없음 |
| **비드큐** | - | 유료 | - | 낙찰 분석 (34조원 누계) | 없음 |
| **인포21C** | - | 22,000원~ | - | 만족도 1위, 적격심사 계산 | 없음 |
| **지투비플러스** | - | 무료 | - | AI 분석 제공 | 있음 (경쟁자) |
| **Biz-Retriever** | 2026 | 10,000~30,000원 | 없음 | **Gemini AI 분석**, Hard Match | **있음** |

### 3.2 경쟁 포지셔닝

```
                    높은 가격
                       |
    비드프로(컨설팅)     |    모두입찰(시장 1위)
    비드메이트(프리미엄)  |    인포21C
                       |
   ----기본 기능--------+--------AI/고급 기능----
                       |
    딥비드(무료)        |    Biz-Retriever (HERE)
    지투비플러스(무료)    |    (AI 분석 + 저가)
                       |
                    낮은 가격
```

### 3.3 Biz-Retriever의 경쟁 우위

**강점 (Strengths)**
- Google Gemini AI 기반 자동 분석 (경쟁사 대부분 미제공)
- Hard Match 엔진 (지역/면허/실적 자동 검증)
- 무료 API 비용 (Gemini 1,500 req/일)
- 모던 기술 스택 (SPA, 실시간, 반응형)

**약점 (Weaknesses)**
- 브랜드 인지도 0%, 사용자 0명
- 시장 진입 22년 늦음 (비드프로 2002년 설립)
- 낙찰가 예측 기능 미보유 (모두입찰 특허)
- 입찰 대행 서비스 없음

**기회 (Opportunities)**
- AI 입찰 분석 수요 급증 (2025년 YoY 60% 성장)
- 기존 서비스의 레거시 기술 (AI 전환 느림)
- 중소기업 디지털 전환 정책 지원

**위협 (Threats)**
- 지투비플러스: 무료 + AI 분석 제공 (직접 경쟁자)
- 모두입찰/비드프로의 AI 기능 추가 가능성
- 대기업(네이버, 카카오) 시장 진입 가능성

---

## 4. 가격 전략 최적화

### 4.1 가격 재설계 제안

#### Free 티어 (무료)

| 항목 | 현재 | 제안 | 변경 근거 |
|------|------|------|-----------|
| Hard Match | 3건/일 | **5건/일** | 3건은 가치 체감 불충분. 5건이면 "더 보고 싶다" 발생 |
| AI 분석 | 5건/일 | **2건/일** | AI 분석이 핵심 차별점. 맛보기만 제공 |
| 키워드 | 5개 | 3개 | Free 제한 강화로 업셀 동기 부여 |
| Slack 알림 | 미제공 | **일 1회 요약** | 가치 체감용 최소 기능 |
| 데이터 보관 | 무제한 | **7일** | 과거 데이터 접근 제한으로 업셀 유도 |
| Excel Export | 미언급 | **불가** | Pro 전용 기능으로 재분류 |

**Free 티어 설계 원칙**: "충분히 유용하지만, 비즈니스 의사결정에는 부족한" 수준

#### Basic 티어 (19,900원/월)

| 항목 | 현재 (10,000원) | 제안 (19,900원) | 변경 근거 |
|------|-----------------|-----------------|-----------|
| Hard Match | 50건/일 | 50건/일 | 유지 |
| AI 분석 | 100건/일 | **30건/일** | 원가 관리 + Pro 업셀 여지 |
| 키워드 | 20개 | 15개 | Pro 업셀 여지 확보 |
| Slack 알림 | 제공 | **실시간** | 핵심 가치 |
| 이메일 알림 | 미언급 | **일 1회 리포트** | 부가 가치 |
| 데이터 보관 | 무제한 | **90일** | 합리적 범위 |
| Excel Export | 미언급 | **월 10회** | 제한적 제공 |
| 칸반 보드 | 미언급 | **기본** | 공고 관리 가치 |

**가격 근거**:
- 모두입찰 27,500원의 72% 수준
- AI 분석 포함이므로 가성비 우위 확보
- 10,000원은 "장난감" 인상을 줌 → 19,900원은 "전문 도구" 인식

#### Pro 티어 (39,900원/월, 연간 29,900원/월)

| 항목 | 현재 (30,000원) | 제안 (39,900원) | 변경 근거 |
|------|-----------------|-----------------|-----------|
| Hard Match | 무제한 | 무제한 | 유지 |
| AI 분석 | 무제한 | **무제한** | 핵심 가치 |
| 키워드 | 100개 | **50개** | 100개는 과잉. 50개도 충분 |
| Slack 알림 | 제공 | **실시간 + 커스텀** | 알림 규칙 설정 |
| 이메일 알림 | 제공 | **실시간** | 풀 기능 |
| 데이터 보관 | 무제한 | **무제한** | 프리미엄 혜택 |
| Excel Export | 미언급 | **무제한** | 프리미엄 혜택 |
| 칸반 보드 | 미언급 | **고급 (담당자 지정, 마감 관리)** | 팀 협업 |
| 우선 지원 | 미언급 | **24시간 내 응답** | 프리미엄 서비스 |
| API 접근 | 미언급 | **읽기 전용 API** | 엔터프라이즈 연동 |

**가격 근거**:
- 모두입찰 27,500원 대비 45% 프리미엄이지만 AI 분석 무제한 포함
- 연간 결제 29,900원은 모두입찰과 동일 수준
- "연간 할인 25%"라는 심리적 앵커링 효과

### 4.2 가격 심리학 적용

| 기법 | 적용 방식 |
|------|-----------|
| **앵커링** | Pro 가격(39,900원)을 먼저 노출 → Basic(19,900원)이 합리적으로 느껴짐 |
| **디코이 효과** | Basic 대비 Pro의 기능 차이를 크게 설계 → Pro가 "가성비" 느낌 |
| **9의 법칙** | 20,000원 -> 19,900원, 40,000원 -> 39,900원 |
| **연간 할인** | "월 39,900원 → 연간 결제 시 월 29,900원 (25% 절약)" |
| **손실 회피** | Free 사용자에게 "놓치고 있는 AI 분석 결과" 미리보기 제공 |

### 4.3 가격 변경 구현 가이드

현재 코드에서 변경이 필요한 파일:

**Backend**: `app/services/subscription_service.py`
```python
# 변경 전 (현재)
"free": {"hard_match_limit": 3, "ai_analysis_limit": 5, "keywords_limit": 5}
"basic": {"hard_match_limit": 50, "ai_analysis_limit": 100, "keywords_limit": 20}
"pro": {"hard_match_limit": 9999, "ai_analysis_limit": 9999, "keywords_limit": 100}

# 변경 후 (제안)
"free": {
    "hard_match_limit": 5,
    "ai_analysis_limit": 2,
    "keywords_limit": 3,
    "data_retention_days": 7,
    "export_limit": 0,
    "slack_notification": "daily_summary",
}
"basic": {
    "hard_match_limit": 50,
    "ai_analysis_limit": 30,
    "keywords_limit": 15,
    "data_retention_days": 90,
    "export_limit": 10,
    "slack_notification": "realtime",
    "email_notification": "daily_report",
}
"pro": {
    "hard_match_limit": 9999,
    "ai_analysis_limit": 9999,
    "keywords_limit": 50,
    "data_retention_days": -1,  # 무제한
    "export_limit": -1,  # 무제한
    "slack_notification": "realtime_custom",
    "email_notification": "realtime",
    "api_access": True,
    "priority_support": True,
}
```

**Backend**: `app/services/payment_service.py`
```python
# 변경 전
plan_prices = {"free": 0, "basic": 10000, "pro": 30000}

# 변경 후
plan_prices = {"free": 0, "basic": 19900, "pro": 39900}
# + 연간 가격
annual_prices = {"free": 0, "basic": 15900 * 12, "pro": 29900 * 12}
```

**Frontend**: `frontend/payment.html`
```javascript
// 변경 전
basic: { price: 10000 }, pro: { price: 30000 }

// 변경 후
basic: { price: 19900, annualPrice: 15900 },
pro: { price: 39900, annualPrice: 29900 }
```

---

## 5. 전환 퍼널 설계

### 5.1 사용자 여정 맵

```
[방문자] → [회원가입] → [Free 활성화] → [가치 체감] → [Basic 전환] → [Pro 업셀]
  100%        15%           80%            40%           5%            15%
                                                    (of Free)    (of Basic)
```

### 5.2 Free -> Basic 전환 전략

**트리거 포인트 (사용자가 제한에 부딪히는 순간)**

| 트리거 | 발생 조건 | 액션 |
|--------|-----------|------|
| **Hard Match 한도 도달** | 일일 5건 소진 | "오늘 12건의 추가 맞춤 공고가 있습니다. Basic에서 확인하세요" 배너 |
| **AI 분석 한도 도달** | 일일 2건 소진 | "AI가 이 공고의 낙찰 확률을 78%로 분석했습니다. 전체 분석을 Basic에서 확인하세요" |
| **키워드 한도 도달** | 3개 키워드 등록 시도 | "더 정밀한 매칭을 위해 Basic에서 15개 키워드를 등록하세요" |
| **데이터 만료 경고** | 가입 후 5일차 | "2일 후 기존 데이터가 삭제됩니다. Basic에서 90일간 보관하세요" |
| **사용 패턴 분석** | 3일 연속 로그인 | "적극적으로 사용 중이시네요! Basic 7일 무료 체험을 시작하세요" |

**전환 촉진 캠페인**

1. **가입 후 3일차**: 이메일 - "AI가 분석한 맞춤 공고 요약 리포트" (무료 샘플)
2. **가입 후 7일차**: 이메일 - "지난 7일간 놓친 공고 23건 (Basic이었다면 모두 확인 가능)"
3. **가입 후 14일차**: 이메일 - "Basic 7일 무료 체험 초대" (전환율 최대화 시점)

### 5.3 Basic -> Pro 업셀 전략

| 트리거 | 발생 조건 | 액션 |
|--------|-----------|------|
| **AI 분석 한도 근접** | 월 30건 중 25건 소진 | "이번 달 AI 분석 5건 남았습니다. Pro에서 무제한으로 분석하세요" |
| **팀 협업 시도** | 칸반 보드에서 담당자 지정 시도 | "Pro에서 팀 협업 기능을 사용하세요" |
| **Export 한도 도달** | 월 10회 엑셀 추출 소진 | "Pro에서 무제한 데이터 추출이 가능합니다" |
| **높은 활용도** | 월 로그인 20회+ | "파워 유저이시군요! Pro 업그레이드로 제한 없이 사용하세요" |

### 5.4 무료 체험 (Free Trial) 전략

**제안: Opt-In 7일 Basic 무료 체험**

- **시점**: Free 가입 후 7~14일 (가치 체감 후)
- **조건**: 신용카드 등록 불필요 (Opt-In 방식)
- **전환율 목표**: 체험 -> 유료 17.8% (업계 벤치마크)
- **이유**: 한국 시장에서는 카드 등록 요구 시 이탈률 급증

**구현 방안**:
```
1. Free 사용자가 "7일 무료 체험" 버튼 클릭
2. 즉시 Basic 기능 활성화 (결제 정보 불요)
3. 체험 3일차: 푸시 알림 "체험 기간 4일 남았습니다"
4. 체험 6일차: 이메일 "내일 체험이 종료됩니다. 지금 구독하면 첫 달 30% 할인"
5. 체험 7일차: 자동 Free 복귀 + "Basic에서 사용했던 기능이 제한됩니다" 알림
```

### 5.5 전환율 벤치마크 및 목표

| 지표 | 글로벌 B2B SaaS 벤치마크 | Biz-Retriever 목표 (6개월) | Biz-Retriever 목표 (12개월) |
|------|--------------------------|---------------------------|----------------------------|
| 방문자 -> 가입 | 13.7% | 10% | 15% |
| Free -> Basic | 2-5% | 3% | 5% |
| Basic -> Pro | 10-15% | 10% | 15% |
| 체험 -> 유료 | 17.8% (Opt-In) | 12% | 18% |
| 월 해지율 | 3-5% (SMB) | 5% | 3% |

---

## 6. KPI 체계 정의

### 6.1 핵심 KPI 대시보드

#### Tier 1: 생존 지표 (매일 확인)

| KPI | 정의 | 계산 방식 | 목표 |
|-----|------|-----------|------|
| **MRR** | Monthly Recurring Revenue | SUM(각 유료 사용자의 월 결제액) | 6개월: 300,000원 |
| **Active Users (DAU/MAU)** | 일간/월간 활성 사용자 | 로그인 또는 API 호출 기준 | DAU 20, MAU 100 |
| **Paid Customers** | 유료 고객 수 | Basic + Pro 구독자 합계 | 6개월: 15명 |

#### Tier 2: 성장 지표 (주간 확인)

| KPI | 정의 | 계산 방식 | 목표 |
|-----|------|-----------|------|
| **Churn Rate** | 월간 해지율 | 해지 고객 / 전월 유료 고객 x 100 | < 5% |
| **Net Revenue Retention (NRR)** | 순 매출 유지율 | (MRR + 업그레이드 - 다운그레이드 - 해지) / 전월 MRR x 100 | > 100% |
| **ARPU** | 유료 고객당 평균 매출 | MRR / 유료 고객 수 | 25,000원 |
| **Free -> Paid Conversion** | 무료 -> 유료 전환율 | 신규 유료 / 전체 Free 사용자 x 100 | 5% |

#### Tier 3: 효율 지표 (월간 확인)

| KPI | 정의 | 계산 방식 | 목표 |
|-----|------|-----------|------|
| **LTV** | 고객 생애 가치 | ARPU / Churn Rate | 500,000원 |
| **CAC** | 고객 획득 비용 | 마케팅 비용 / 신규 유료 고객 수 | < 100,000원 |
| **LTV:CAC Ratio** | LTV 대 CAC 비율 | LTV / CAC | > 3.0 |
| **Payback Period** | CAC 회수 기간 | CAC / ARPU | < 4개월 |
| **Quick Ratio** | SaaS 성장 효율 | (New MRR + Expansion) / (Churn + Contraction) | > 4.0 |

### 6.2 KPI 상세 계산 방법

#### MRR (Monthly Recurring Revenue)

```
MRR = (Basic 고객 수 x 19,900) + (Pro 월간 고객 수 x 39,900) + (Pro 연간 고객 수 x 29,900)

예시: Basic 10명 + Pro 월간 3명 + Pro 연간 2명
MRR = (10 x 19,900) + (3 x 39,900) + (2 x 29,900)
    = 199,000 + 119,700 + 59,800
    = 378,500원
```

#### Churn Rate

```
월간 Churn Rate = 해당 월 해지 고객 수 / 전월 말 유료 고객 수 x 100

예시: 전월 유료 20명, 이번 달 해지 1명
Churn Rate = 1 / 20 x 100 = 5%

연간 환산 = 1 - (1 - 0.05)^12 = 46% (월 5%는 연간으로 매우 높음)
목표: 월 3% 이하 = 연간 ~31%
```

#### LTV (Lifetime Value)

```
LTV = ARPU x 평균 사용 기간 (월)
    = ARPU / Monthly Churn Rate

예시: ARPU 25,000원, Churn 5%
LTV = 25,000 / 0.05 = 500,000원

보수적 계산 (할인율 10% 적용):
LTV = ARPU x (1 / (Churn + Discount Rate))
    = 25,000 x (1 / (0.05 + 0.008))
    = 431,034원
```

#### CAC (Customer Acquisition Cost)

```
CAC = (마케팅 비용 + 영업 비용) / 신규 유료 고객 수

초기 단계 (마케팅 0원, 유기적 성장):
CAC = 0원 (실질적으로 개발자 시간 비용만 발생)

성장 단계 (월 마케팅 30만원):
CAC = 300,000 / 5 (신규 유료) = 60,000원
```

### 6.3 코호트 분석 프레임워크

```
Month 0: 가입 100명 (Free)
Month 1: 활성 60명, 유료 전환 5명 (5%)
Month 2: 활성 45명, 유료 유지 4.75명 (95% retention), 신규 전환 2명
Month 3: 활성 35명, 유료 유지 6.4명, 신규 전환 1명
...
```

**추적할 코호트 지표**:
- Week 1 Retention (목표: 60%)
- Month 1 Retention (목표: 40%)
- Month 3 Retention (목표: 25%)
- Time to First Value (목표: < 5분)
- Time to Upgrade (평균 전환 소요일)

---

## 7. 해지 방어 전략

### 7.1 해지 예측 시그널

| 시그널 | 점수 | 감지 방법 |
|--------|------|-----------|
| 7일간 미로그인 | +3 | last_login_at 모니터링 |
| 키워드 삭제 | +2 | keyword DELETE 이벤트 |
| 알림 비활성화 | +2 | notification_enabled = false |
| 결제 실패 | +5 | payment_status = "failed" |
| 프로필 미완성 | +1 | profile completeness < 50% |
| 이번 달 AI 분석 0건 | +3 | usage_count = 0 |

**해지 위험 등급**: 합계 5점 이상 = "위험", 8점 이상 = "긴급"

### 7.2 해지 방어 플레이북

#### 단계 1: 선제적 개입 (위험 감지 시)

```
위험 등급 → 자동 이메일:
"[사용자명]님, 이번 주 놓친 맞춤 공고 [N]건을 확인하세요"
+ 가장 관련도 높은 공고 3건 미리보기
```

#### 단계 2: 해지 시도 시 방어 흐름

```
[해지 버튼 클릭]
    → Step 1: 해지 이유 설문 (필수)
        □ 가격이 비싸요
        □ 기능이 부족해요
        □ 다른 서비스로 이동해요
        □ 더 이상 입찰에 참여하지 않아요
        □ 기타

    → Step 2: 이유별 맞춤 오퍼
        "가격이 비싸요" → "다음 3개월 30% 할인 쿠폰을 드릴게요"
        "기능이 부족해요" → "어떤 기능이 필요하신지 알려주세요. 우선 반영하겠습니다"
        "다른 서비스" → "어떤 서비스로 이동하시나요? [경쟁사 대비표] 한번 더 확인해주세요"

    → Step 3: 최종 확인
        "정말 해지하시겠습니까? 현재 보유한 [N]건의 분석 데이터가 삭제됩니다."
        [해지 유예 (1주일 후 해지)] [즉시 해지]

    → Step 4: 해지 완료 후
        "언제든 돌아오실 수 있습니다. 30일 내 재구독 시 데이터 복원 + 첫 달 50% 할인"
```

#### 단계 3: 윈백 캠페인

| 시점 | 액션 | 오퍼 |
|------|------|------|
| 해지 후 7일 | 이메일: "이번 주 놓친 맞춤 공고 [N]건" | 없음 (가치 리마인드) |
| 해지 후 14일 | 이메일: "30일 내 재구독 시 50% 할인" | 50% 할인 1개월 |
| 해지 후 30일 | 이메일: "마지막 기회: 데이터 삭제 예정" | 데이터 보존 + 30% 할인 |
| 해지 후 90일 | 이메일: "Biz-Retriever가 업데이트되었습니다" | 신규 기능 소개 |

### 7.3 비자발적 해지 방어 (Involuntary Churn)

결제 실패로 인한 비자발적 해지는 전체 해지의 20-40%를 차지한다.

**Dunning Management (미수금 관리)**:

```
결제 실패 발생
    → 즉시: 재시도 (자동)
    → 1일 후: 이메일 "결제 수단을 확인해주세요"
    → 3일 후: 재시도 + SMS 알림
    → 7일 후: 마지막 재시도 + "서비스가 곧 중단됩니다" 이메일
    → 14일 후: 서비스 중단 (Free로 다운그레이드)
    → 30일 후: 계정 보존 (데이터 유지)
```

---

## 8. 랜딩페이지/온보딩 개선

### 8.1 현재 랜딩페이지 문제점

현재 `frontend/index.html` 분석 결과:

| 문제 | 심각도 | 상세 |
|------|--------|------|
| 가치 제안 불명확 | HIGH | "AI 기반 입찰 공고 지능형 모니터링"은 추상적 |
| 가격 페이지 부재 | HIGH | 랜딩에서 가격 정보 확인 불가 |
| 사회적 증거 부족 | HIGH | "500+ 엔터프라이즈 기업이 신뢰"는 허구 (사용자 0명) |
| CTA 불명확 | MEDIUM | "안전하게 로그인"만 있고 가입 유도 약함 |
| SEO 미최적화 | MEDIUM | 메타 태그, 구조화 데이터 부재 |
| 모바일 체험 미검증 | MEDIUM | 반응형이나 CTA 위치 최적화 안됨 |

### 8.2 랜딩페이지 개선 제안

#### 히어로 섹션 (Above the fold)

```
변경 전:
"AI 기반 입찰 공고 지능형 모니터링"

변경 후:
"입찰 검색에 매일 2시간을 낭비하고 계신가요?"
→ "Biz-Retriever가 AI로 맞춤 공고만 골라드립니다"
→ [7일 무료 체험 시작하기] (Primary CTA)
→ [가격 확인하기] (Secondary CTA)
```

#### 가치 제안 3단계

```
1. "매일 아침, AI가 분석한 맞춤 공고 리포트를 받아보세요"
   → 시간 절약 강조 (하루 2시간 → 5분)

2. "지역, 면허, 실적 자동 검증으로 헛된 입찰 방지"
   → Hard Match 가치 (오탐 0%)

3. "경쟁사 대비 AI 분석 무제한 제공"
   → 모두입찰 27,500원에는 없는 AI 분석
```

#### 사회적 증거 (정직한 버전)

```
변경 전: "500+ 엔터프라이즈 기업이 신뢰" (허구)

변경 후:
- "Beta 서비스 운영 중 - 선착순 100명 무료 체험"
- "개발자가 직접 만든 도구 - 오픈소스 GitHub"
- 실제 사용 스크린샷 (대시보드, AI 분석 결과)
```

### 8.3 온보딩 플로우 개선

#### 현재 온보딩 (문제)

```
가입 → 빈 대시보드 → ???
(사용자는 무엇을 해야 하는지 모름)
```

#### 제안 온보딩 (5단계 가이드)

```
Step 1: 환영 + 업종 선택 (30초)
    "어떤 분야의 입찰에 관심이 있으신가요?"
    [건설] [IT/SW] [용역] [구매] [기타]
    → 자동 키워드 추천 생성

Step 2: 사업자 정보 입력 (선택, 1분)
    "사업자등록증을 업로드하면 AI가 자동으로 정보를 추출합니다"
    [업로드하기] [나중에 하기]

Step 3: 키워드 설정 (30초)
    "추천 키워드를 확인하고 수정하세요"
    [추천된 키워드 칩 목록]
    [+ 키워드 추가]

Step 4: 알림 설정 (30초)
    "새 맞춤 공고를 어떻게 받아보시겠어요?"
    [Slack] [이메일] [웹만]

Step 5: 첫 번째 결과 확인 (즉시)
    "설정 완료! AI가 분석한 맞춤 공고입니다"
    [대시보드에서 확인하기]
    → 대시보드에 가이드 투어 오버레이
```

**핵심 지표**: Time to First Value (TTFV) 목표: **5분 이내**

### 8.4 가격 페이지 신규 설계

현재 `frontend/payment.html`은 결제 전용 페이지이다. 별도의 **가격 비교 페이지** 필요.

#### 가격 페이지 구조

```
[월간] [연간 - 25% 절약]  ← 토글 스위치

┌─────────────┬─────────────────┬──────────────────┐
│   FREE      │    BASIC        │    PRO (추천)     │
│   무료       │  19,900원/월    │  39,900원/월      │
│             │                 │  연간: 29,900원/월 │
├─────────────┼─────────────────┼──────────────────┤
│ 맞춤공고 5건 │ 맞춤공고 50건    │ 맞춤공고 무제한   │
│ AI 분석 2건  │ AI 분석 30건/월  │ AI 분석 무제한    │
│ 키워드 3개   │ 키워드 15개      │ 키워드 50개       │
│ 데이터 7일   │ 데이터 90일      │ 데이터 무제한     │
│             │ Excel 월 10회    │ Excel 무제한      │
│ 일 1회 요약  │ 실시간 Slack     │ 커스텀 알림 규칙  │
│             │ 일 1회 이메일    │ 실시간 이메일     │
│             │                 │ API 접근          │
│             │                 │ 우선 지원         │
├─────────────┼─────────────────┼──────────────────┤
│ [현재 플랜]  │ [7일 무료 체험]  │ [7일 무료 체험]   │
└─────────────┴─────────────────┴──────────────────┘

"모든 플랜에 포함: G2B 자동 수집, 대시보드, 칸반 보드 기본"
```

---

## 9. 수익 대시보드 데이터 모델

### 9.1 필요한 DB 테이블/필드

#### 사용량 추적 테이블 (신규)

```sql
CREATE TABLE usage_tracking (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id),
    date DATE NOT NULL DEFAULT CURRENT_DATE,
    hard_match_count INTEGER DEFAULT 0,
    ai_analysis_count INTEGER DEFAULT 0,
    export_count INTEGER DEFAULT 0,
    login_count INTEGER DEFAULT 0,
    page_views INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT NOW(),

    UNIQUE(user_id, date)
);
```

#### 전환 이벤트 테이블 (신규)

```sql
CREATE TABLE conversion_events (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id),
    event_type VARCHAR(50) NOT NULL,
    -- 'signup', 'trial_start', 'trial_end', 'upgrade',
    -- 'downgrade', 'churn', 'reactivation'
    from_plan VARCHAR(20),
    to_plan VARCHAR(20),
    trigger_source VARCHAR(100),
    -- 'limit_reached', 'trial_expired', 'email_campaign',
    -- 'pricing_page', 'manual'
    metadata JSONB,
    created_at TIMESTAMP DEFAULT NOW()
);
```

#### 해지 이유 테이블 (신규)

```sql
CREATE TABLE churn_reasons (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id),
    subscription_id INTEGER REFERENCES subscriptions(id),
    reason_category VARCHAR(50) NOT NULL,
    -- 'price', 'features', 'competitor', 'no_need', 'other'
    reason_detail TEXT,
    offer_presented VARCHAR(100),
    offer_accepted BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT NOW()
);
```

### 9.2 대시보드 API 엔드포인트 (제안)

```
GET /api/v1/admin/metrics/overview
  → MRR, 유료 고객 수, Churn Rate, ARPU

GET /api/v1/admin/metrics/mrr-history?period=6m
  → 월별 MRR 추이 (New + Expansion - Churn - Contraction)

GET /api/v1/admin/metrics/cohort?start=2026-01&end=2026-06
  → 코호트별 리텐션 매트릭스

GET /api/v1/admin/metrics/conversion-funnel
  → 방문 → 가입 → Free → Trial → Basic → Pro 퍼널

GET /api/v1/admin/metrics/churn-analysis
  → 해지 이유 분포, 해지 위험 사용자 목록

GET /api/v1/admin/metrics/usage-summary
  → 기능별 사용량 (AI 분석, Hard Match, Export 등)
```

### 9.3 대시보드 위젯 구성

```
┌──────────────────────────────────────────────────────────┐
│                    수익 대시보드                           │
├──────────┬──────────┬──────────┬──────────┬──────────────┤
│ MRR      │ 유료고객  │ Churn    │ ARPU     │ LTV:CAC     │
│ 378,500  │ 15명     │ 3.2%    │ 25,233원  │ 4.2:1       │
│ +12% ↑   │ +3 ↑    │ -0.5% ↓ │ +800 ↑   │ stable      │
├──────────┴──────────┴──────────┴──────────┴──────────────┤
│ [MRR 추이 차트 - 6개월]                                    │
│ ████ New  ████ Expansion  ░░░░ Churn  ░░░░ Contraction   │
├────────────────────────┬─────────────────────────────────┤
│ [코호트 리텐션 히트맵]  │ [전환 퍼널 차트]                  │
│  M0  M1  M2  M3        │ 방문자 1000                      │
│  100 60  45  35         │ → 가입 150 (15%)                │
│  ██  ██  █▒  █░         │ → Free 120 (80%)                │
│                        │ → 체험 40 (33%)                  │
│                        │ → Basic 7 (17%)                  │
│                        │ → Pro 1 (14%)                    │
├────────────────────────┴─────────────────────────────────┤
│ [해지 이유 분석]                [플랜별 분포]               │
│ 가격 40% ████████              Free: 85명                 │
│ 기능 25% █████                 Basic: 12명                │
│ 경쟁사 20% ████                Pro: 3명                   │
│ 기타 15% ███                                             │
└──────────────────────────────────────────────────────────┘
```

---

## 10. 실행 로드맵

### Phase 1: 즉시 (1-2주) - 가격 체계 업데이트

- [ ] `subscription_service.py` 플랜 제한 값 변경
- [ ] `payment_service.py` 가격 업데이트 (19,900/39,900)
- [ ] `payment.html` 프론트엔드 가격 표시 업데이트
- [ ] 연간 결제 옵션 추가 (Backend + Frontend)
- [ ] 가격 비교 페이지 신규 생성 (`pricing.html`)

### Phase 2: 단기 (2-4주) - 사용량 추적 및 전환 기반

- [ ] `usage_tracking` 테이블 생성 및 미들웨어 구현
- [ ] `conversion_events` 테이블 생성
- [ ] Free 사용자 제한 도달 시 업셀 배너 UI
- [ ] 7일 무료 체험 기능 구현
- [ ] 온보딩 5단계 가이드 구현

### Phase 3: 중기 (1-2개월) - 해지 방어 및 자동화

- [ ] `churn_reasons` 테이블 생성
- [ ] 해지 플로우 UI (설문 + 맞춤 오퍼)
- [ ] 자동 이메일 캠페인 (가입 후 3/7/14일)
- [ ] 해지 예측 시그널 모니터링
- [ ] Dunning management (결제 실패 자동 재시도)

### Phase 4: 장기 (2-3개월) - 수익 대시보드

- [ ] 관리자 수익 대시보드 API
- [ ] MRR/Churn/코호트 시각화
- [ ] A/B 테스트 프레임워크 (가격/기능)
- [ ] 윈백 캠페인 자동화

---

## 부록 A: 수익 시뮬레이션

### 시나리오 1: 보수적 (6개월)

```
Month 1: 베타 사용자 50명 (Free)
Month 2: Free 80명, Basic 4명 (5%), MRR = 79,600원
Month 3: Free 120명, Basic 8명, Pro 1명, MRR = 199,100원
Month 4: Free 150명, Basic 12명, Pro 2명, MRR = 318,600원
Month 5: Free 180명, Basic 15명, Pro 3명, MRR = 418,200원
Month 6: Free 200명, Basic 18명, Pro 4명, MRR = 517,800원

연간 환산 MRR: ~620만원
```

### 시나리오 2: 낙관적 (6개월)

```
Month 1: 베타 사용자 100명 (Free)
Month 2: Free 200명, Basic 10명, Pro 2명, MRR = 278,800원
Month 3: Free 350명, Basic 20명, Pro 5명, MRR = 597,500원
Month 4: Free 500명, Basic 30명, Pro 8명, MRR = 916,200원
Month 5: Free 700명, Basic 40명, Pro 12명, MRR = 1,274,800원
Month 6: Free 1000명, Basic 50명, Pro 18명, MRR = 1,713,200원

연간 환산 MRR: ~2,050만원
```

### 손익분기점 (BEP) 분석

```
월 고정비:
  서버 (Railway): 5,000원
  기타 인프라: 6,000원
  합계: ~11,000원 (사용자 0명 기준)

변동비 (사용자 증가 시):
  Gemini API (100명 이상): ~30,000원/월
  이메일 서비스 (SendGrid): ~10,000원/월
  합계: ~51,000원 (100명 기준)

BEP = 고정비 / (ARPU - 변동비 per user)
    = 51,000 / (25,000 - 400)
    = 약 2.1명

실질 BEP (인건비 제외): 유료 고객 3명 이상
실질 BEP (인건비 포함, 월 200만원): 유료 고객 약 82명
```

---

## 부록 B: 참고 자료 및 벤치마크 출처

- [SaaS Freemium Conversion Rates: 2026 Report - First Page Sage](https://firstpagesage.com/seo-blog/saas-freemium-conversion-rates/)
- [Average SaaS Conversion Rates: 2026 Report - First Page Sage](https://firstpagesage.com/seo-blog/average-saas-conversion-rates/)
- [B2B SaaS Churn Rate Benchmarks 2025 - Vitally](https://www.vitally.io/post/saas-churn-benchmarks)
- [B2B SaaS Churn Rates Statistics 2025 - Genesys Growth](https://genesysgrowth.com/blog/saas-churn-rates-stats-for-marketing-leaders)
- [모두입찰 이용요금](https://www.modoobid.co.kr/service/inform) - 월 27,500원
- [비드프로](https://www.bidpro.co.kr/) - 공공입찰 컨설팅
- [딥비드](https://www.deepbid.com/) - 빅데이터 기반 입찰정보
- [비드큐](https://www.bidq.co.kr/) - 낙찰 분석 전문
- [비드메이트](https://bidmate.co.kr/) - 프리미엄 입찰정보
- [SaaS Pricing Page Best Practices 2026 - InfluenceFlow](https://influenceflow.io/resources/saas-pricing-page-best-practices-complete-guide-for-2026/)
- [Freemium Conversion Rate Guide - Userpilot](https://userpilot.com/blog/freemium-conversion-rate/)
- [Product-Led Growth Benchmarks - ProductLed](https://productled.com/blog/product-led-growth-benchmarks)

---

**Last Updated**: 2026-02-24
**다음 리뷰 예정**: Phase 1 완료 후 (가격 체계 변경 적용 시점)
