# Frontend - 프리미엄 다크모드 웹 UI

## 접속 방법
- **Production**: https://biz-retriever.vercel.app
- **Local**: http://localhost:8000/static/index.html

## 구조
```
frontend/
├── index.html         # 로그인 페이지
├── dashboard.html     # 메인 대시보드
├── payment.html       # Tosspayments 결제 위젯
├── css/
│   ├── variables.css    # 디자인 토큰 (50-950 색상 스케일)
│   ├── components.css   # 재사용 컴포넌트
│   ├── accessibility.css # WCAG 2.1 AA 접근성
│   ├── reset.css        # CSS 리셋 + Pretendard 폰트
│   ├── main.css         # 로그인 스타일
│   └── dashboard.css    # 대시보드 스타일
└── js/
    ├── api.js       # API 서비스 레이어 (자동 토큰 갱신)
    ├── auth.js      # 인증 로직 (계정 잠금 UI 포함)
    ├── config.js    # 환경별 API URL 설정
    ├── dashboard.js # 대시보드 로직
    └── utils.js     # 유틸리티
```

## 주요 기능
- 회원가입/로그인 (email/password)
- JWT 토큰 자동 갱신 (Access Token 만료 시 자동 refresh)
- 대시보드 (공고 목록/필터링)
- MD3 다크모드 디자인
- Toast 알림
- 반응형 레이아웃
- 계정 잠금 UI (실시간 카운트다운)
- Tosspayments V2 결제 위젯

## 디자인 시스템 v2.0

### 폰트
- **Pretendard**: 한국어 최적화 웹 폰트

### 색상 시스템
50-950 스케일의 완전한 색상 팔레트 (Tailwind CSS v3 기반):
- **Slate** (Neutral): 배경, 텍스트
- **Blue** (Primary): CTA, 링크, 강조
- **Emerald** (Success): 성공 상태
- **Amber** (Warning): 경고 상태
- **Red** (Danger): 에러, 삭제

### 토큰 아키텍처
```
1. Primitive Tokens  → 원시 색상 팔레트 (50~950)
2. Semantic Tokens   → 문맥적 의미 (--primary, --danger)
3. Component Tokens  → UI 요소 (--btn-primary-bg)
```

### 그리드 & 타이포그래피
- **Grid**: 4px base unit (0.25rem)
- **Type Scale**: Major Third (1.250)

### 다크모드
- MD3 (Material Design 3) 기반 다크모드
- `prefers-color-scheme: dark` 자동 감지
- CSS 커스텀 프로퍼티로 라이트/다크 전환

## WCAG 2.1 AA 접근성

- **Skip Navigation**: 키보드 사용자용 콘텐츠 바로가기
- **Focus Visible**: `:focus-visible`로 키보드 전용 포커스 링 표시
- **색상 대비**: AA 기준 (4.5:1) 충족
- **키보드 탐색**: 모든 인터랙티브 요소 Tab 탐색 가능

설정 파일: `frontend/css/accessibility.css`

## Tosspayments V2 결제

### 위젯 통합
- 결제 페이지: `frontend/payment.html`
- 백엔드 API: `app/api/endpoints/payment.py`
- 서비스 레이어: `app/services/payment_service.py`, `app/services/subscription_service.py`

### 구독 플랜
| 플랜 | 설명 |
|------|------|
| Free | 기본 기능 (맞춤공고 제한) |
| Pro | 전체 기능 |

## API 서비스
`frontend/js/api.js`:
- `APIService.register()` - 회원가입
- `APIService.login()` - 로그인
- `APIService.logout()` - 로그아웃 (토큰 블랙리스트)
- `APIService.getBids()` - 공고 목록
- `APIService.getAnalytics()` - 통계
- `APIService.exportExcel()` - 엑셀 다운로드

### 토큰 자동 갱신
- 401 응답 시 `/auth/refresh` 자동 호출
- 동시 요청 시 Promise 공유 (refresh 1회만 발생)
- 갱신 실패 시 로그아웃 + 로그인 페이지 리다이렉트

## 배포

### Vercel (현재 방식)
`frontend/` 디렉토리를 Vercel에 연결. API URL은 `config.js`에서 관리.

### FastAPI Static (로컬 개발)
```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000
# http://localhost:8000/static/index.html
```
