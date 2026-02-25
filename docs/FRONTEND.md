# 🎨 Frontend - 프리미엄 다크모드 웹 UI

## 접속 방법
**URL**: http://localhost:8000/static/index.html

## 구조
```
frontend/
├── index.html       # 로그인 페이지
├── dashboard.html   # 메인 대시보드
├── css/
│   ├── variables.css   # 디자인 토큰
│   ├── components.css  # 재사용 컴포넌트
│   ├── main.css        # 로그인 스타일
│   └── dashboard.css   # 대시보드 스타일
└── js/
    ├── api.js       # API 서비스 레이어
    ├── auth.js      # 인증 로직
    ├── dashboard.js # 대시보드 로직
    └── utils.js     # 유틸리티
```

## 주요 기능
- ✅ 회원가입/로그인 (OAuth2)
- ✅ JWT 토큰 자동 관리
- ✅ 대시보드 (공고 목록/필터링)
- ✅ 다크모드 프리미엄 디자인
- ✅ Toast 알림
- ✅ 반응형 레이아웃

## 백엔드 통합
[`app/main.py`](file:///c:/sideproject/app/main.py#L107-L112) - Static Files:
```python
app.mount("/static", StaticFiles(directory=static_dir), name="static")
```

## API 서비스
[`frontend/js/api.js`](file:///c:/sideproject/frontend/js/api.js)
- `APIService.register()` - 회원가입
- `APIService.login()` - 로그인 (OAuth2 grant_type 포함)
- `APIs APIService.getBids()` - 공고 목록
- `APIService.getAnalytics()` - 통계
- `APIService.exportExcel()` - 엑셀 다운로드

## 브라우저 테스트 결과
✅ 회원가입 → ✅ 로그인 → ✅ 대시보드 → ✅ 보호된 리소스 접근

## 배포 방법
### Option 1: FastAPI Static (현재 방식)
```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

### Option 2: Nginx (프로덕션)
```nginx
location / {
    root /var/www/frontend;
}
location /api {
    proxy_pass http://localhost:8000;
}
```

## 환경 변수 (프로덕션)
```javascript
const API_BASE = process.env.NODE_ENV === 'production' 
    ? 'https://api.biz-retriever.com/api/v1'
    : 'http://localhost:8000/api/v1';
```
