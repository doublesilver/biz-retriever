# Biz-Retriever 확장 분석 + WBS + QA + Phase 정의

## 1. 프로젝트 분석 (Analysis)
Biz-Retriever는 공공 입찰 공고(G2B, Onbid)를 수집하여 사용자에게 최적의 공고를 매칭하는 AI 기반 SaaS 서비스입니다.

### 핵심 제약 사항 (Constraints)
- **Hard Match 오탐 0%**: 지역, 면허, 금액 등 물리적 상충 시 절대 매칭 금지.
- **법적 신뢰성**: 낙찰 보장 표현 금지, 투찰 대행 암시 금지.
- **경량 운영**: Raspberry Pi 4 (4GB) 환경에서 안정적 구동.

## 2. WBS (Work Breakdown Structure)

### Phase 1: 데이터 파이프라인 (Data Pipeline)
- [ ] G2B/Onbid 데이터 수집기 안정화
- [ ] HWP/PDF 텍스트 추출 엔진 고도화
- [ ] 구조화 데이터 스키마 검증

### Phase 2: 사용자 프로필 자동화 (User Profiling)
- [ ] 서류 기반 자동 프로필 생성
- [ ] 면허/지역/실적 필드 구조화

### Phase 3: 매칭 & 설명 엔진 (Matching Engine)
- [ ] Hard Match 필터 로직 (오탐 0% 목표)
- [ ] Soft Match 점수 산출
- [ ] 매칭 사유(Why) 생성 로직

### Phase 4: 사용자 전달 (Delivery)
- [ ] 일일 리포트 알림 (Slack/Email)
- [ ] 대시보드 UI 연동

### Phase 5: QA & 법규 검토 (QA & Legal)
- [ ] 0% 오탐 검증 테스트
- [ ] 법적 표현 필터링

### Phase 6: 최종 배포 (Launch)
- [ ] 프로덕션 배포 및 가이드 작성

## 3. QA 규칙 (Constitution)
- **Rule QA-1**: Hard Match 조건 충족되지 않을 시 어떠한 경우에도 추천 목록에 올리지 않는다.
- **Rule QA-2**: 모든 추천 사유에는 "본 데이터는 참고용이며 법적 증빙이 될 수 없음"을 명시한다.
- **Rule QA-3**: 모든 데이터 수집 로그는 30일간 보존한다.
