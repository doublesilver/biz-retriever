# 프로젝트 상태 보고서 (PROJECT_STATE.md)

> **Supreme Execution Protocol Activated**
> **Final Objective**: 법적으로 안전하며, Hard Match 오탐 0%, MVP 기준 충족, 출시 가능 상태.
> **최종 업데이트**: 2026-01-29

---

## 1. 기본 환경 (Environment)
| 항목 | 값 |
|------|-----|
| Target Device | Raspberry Pi 4 Model B (4GB RAM) |
| OS | Raspberry Pi OS 64-bit / Ubuntu Server 22.04 LTS (ARM64) |
| Container Runtime | Docker + Docker Compose |
| 개발 환경 | Windows (`C:\sideproject`) |
| Python 버전 | 3.11 (Docker), 3.14 Alpha (Local) |

---

## 2. Supreme Roadmap (강제 로드맵)

### Phase 0: 준비 (완료 조건: MVP 범위 고정, 법적 리스크 없음)
- [x] SPEC/WBS/QA 확정 (Supreme Command 접수)
- [x] 데이터 수집 정책 명확화 (G2B/Onbid Public Data)

### Phase 1: 데이터 파이프라인 (완료 - 진행률 100%)
- [x] G2B/Onbid 데이터 수집기 안정화 (HWP/PDF 추출 엔진 고도화 완료)
- [x] 구조화 데이터 스키마 확정 (attachment_content 반영 완료)
- [x] 24시간 자동화 수집 기본 인프라 구축
- **Result**: 입찰 공고 자동 수집 + 본문/첨부파일(HWP/PDF) 파싱 체계 완비.

### Phase 2: 사용자 프로필 자동화 (완료 - 진행률 100%)
- [x] 최소 입력 프로필 생성 UI (`profile.html` + `profile.js`)
- [x] 사업자등록증/실적증명서 기반 AI 프로필 생성 엔진 (Gemini API 연동 완료)
- **Result**: 사용자 프로필 DB 모델링 + AI OCR 파싱 + 프로필 관리 UI 완비.

### Phase 3: 매칭 & 설명 엔진 (완료 - 진행률 100%)
- [x] Hard Match 규칙 엔진 (오탐 0% 목표)
- [x] Soft Match 점수화
- [x] 추천/비추천 사유 생성 로직
- **Result**: 지역/면허/실적 기반 필터링 + 키워드 기반 정성적 점수 산출 엔진 완비.

### Phase 4: 배포 및 최적화 (완료 - 진행률 100%)
- [x] Docker Compose 프로덕션 환경 구축
- [x] 라즈베리파이 배포 및 구동 확인
- **Result**: Production Live (100.75.72.6).

### Phase 5: QA & 법적 검증 (완료 - 진행률 100%)
- [x] 기능/UX QA (Frontend/Backend Integrated Test)
- [x] 법적 표현 검증 (Hard Match Zero-Error Filtering)

### Phase 6: 출시 준비 (완료 - 진행률 100%)
- [x] 배포 및 운영 가이드 확정 (`docs/OPERATION_GUIDE.md`)
- [x] 최종 런칭 (Ready for Go-Live)

---

**Mode**: Maintenance & Monitoring
**Immediate Task**:
1. 모니터링 및 사용자 피드백 수집.
2. Production Traffic 대응 (필요 시).

---

## 4. 기술적 제약 (Technical Constraints)
- **RPi 4 (4GB)**: 가벼운 라이브러리 필수 (HWP 파싱 시 무거운 의존성 주의).
- **법적/신뢰**: 데이터 수집 시 저작권/약관 준수.
- **오탐 0%**: Hard Match 필터링 로직은 보수적으로 설계.

---

## 5. 코드 품질 현황 (Code Quality Status)

### 테스트 커버리지
| 항목 | 결과 |
|------|------|
| 총 테스트 | 165개 |
| 성공 | 165개 (100%) |
| 실패 | 0개 |
| 테스트 실행 시간 | ~53초 |

### 최근 정리 작업 (2026-01-27)
- **레거시 파일 아카이브**: 7개 파일 → `archive/legacy_docs/`
- **중복 코드 제거**: `app/static/` 제거 (frontend/ 사용)
- **임시 파일 정리**: temp_audit*.html 삭제
- **deprecated API 수정**: `google.generativeai` → `google.genai` (profile_service.py)
- **테스트 수정**: patch 경로 및 assertion 업데이트

### AI 엔진 구성
| 항목 | 값 |
|------|------|
| 주 엔진 | Google Gemini 2.5 Flash |
| SDK | `google-genai` (신규 SDK) |
| Fallback | OpenAI GPT-4 (선택적) |

---

## 6. 변경 이력
- **2026-01-27 (오후)**: 프로젝트 정리 완료 - 레거시 아카이브, 테스트 100% 통과
- **2026-01-27**: Supreme Execution Command에 따라 로드맵 전면 개편. (Phase A-C -> Phase 0-6)
