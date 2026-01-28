# 프로젝트 진행 상황 (PROGRESS.md)

## 현재 단계 (Current Phase)
- **프로젝트 최종 완료**: Phase 1-6 전 과정 구현 및 검증 완료.
- **상태**: Production Live & Security Hardened 🛡️
- **최근 작업**: 외부 접속(Tailscale Funnel) 및 서버 보안 강화 가이드 적용.
- **개발 기간**: 6일 (2026.01.22 ~ 2026.01.28)
- **Next**: 정기 점검 및 사용자 피드백 수집.

## 할 일 (Todo)

- [x] **Phase 1: 아기 강아지 입양 (G2B 기본)**
    - [x] DB 스키마 확장 (source, deadline, importance_score, keywords_matched, attachment_content)
    - [x] G2B 크롤러 서비스 (`app/services/crawler_service.py`) - 첨부파일 스크래핑 포함
    - [x] Slack 알림 서비스 (`app/services/notification_service.py`)
    - [x] Celery 태스크 구현 (crawl_g2b_bids, send_morning_digest)
    - [x] Celery Beat 스케줄 설정 (08:00, 12:00, 18:00, 08:30)
    - [x] API 엔드포인트 (`/api/v1/crawler/trigger`, `/api/v1/crawler/status`)
    - [x] 환경 변수 설정 (G2B_API_KEY, SLACK_WEBHOOK_URL)
    - [x] HWP/PDF 텍스트 추출 엔진(`olefile`, `PyPDF2`) 적용
    - [x] 검증 스크립트 성공 (`scripts/test_hwp_parsing_mock.py`, `test_attachment_scraping.py`)

- [x] **Phase 2: 사냥 훈련 (사용자 프로필 자동화)**
    - [x] 사용자 프로필 모델(`UserProfile`, `UserLicense`) DB 반영 (SQLAlchemy)
    - [x] On-Premises/Local LLM 대비 Gemini API 기반 OCR 파싱 엔진 구현
    - [x] 프로필 관리 UI (`profile.html`) 및 대시보드 연동
    - [x] 사업자등록증 자동 인식 및 데이터 추출(Extraction) 성공
    - [x] 502 Bad Gateway 및 Container 충돌 이슈 해결 (Dependency Fix)

- [x] **Phase 3: 명견 등극 (AI 고도화)**
    - [x] 낙찰 데이터 수집 테이블 (bid_results)
    - [x] ML 투찰가 예측 모델 (scikit-learn, Random Forest 구현 완료)
    - [x] AI 분석 API 엔드포인트 (`/api/v1/analysis/match`) - Hard Match 추가
    - [x] AI 제안 UI (공고 상세 모달 내 예측 버튼) - Soft Match & Prediction 통합
    - [x] **Hard Match 엔진**: 지역/면허/실적 기반 오탐 0% 필터링 구현 (`MatchingService`)
    - [x] **Constraint Extraction**: Gemini 기반 공고 제약 조건 추출 (`ConstraintService`)
    - [x] **Soft Match Engine**: 키워드/지역 기반 정성적 점수 산출 구현 (Validation Passed)

- [x] **Phase 4-6: 안정성, 모바일 및 보안**
    - [x] 에러 자동 알림 (Slack Webhook 연동)
    - [x] API 호출 재시도 로직 (Tenacity)
    - [x] 모바일 반응형 UI 반영 (CSS Media Queries)
    - [x] PDF 사업자등록증 파싱 지원
    - [x] 외부 접속 활성화 (Tailscale Funnel)
    - [x] 서버 보안 강화 (UFW, Fail2Ban, Auto-Update)

## 완료 (Completion)
초기 프로젝트 구축 (Steps 1~10) 완료:
- **Backend**: FastAPI + Async SQLAlchemy + PostgreSQL
- **Auth**: JWT + OAuth2 (Bcrypt)
- **Worker**: Celery + Redis
- **Crawler**: G2B API + Smart Filtering
- **Notification**: Slack Webhook
- **Frontend**: HTML/CSS/JS Dashboard
- **Deployment**: Docker + Railway Ready
