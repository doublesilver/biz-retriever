# Vercel 프론트엔드 배포 가이드

> **프론트엔드: Vercel (무료) + 백엔드: 라즈베리파이**

## 🎯 왜 프론트엔드를 Vercel에?

| 항목 | Vercel | 라즈베리파이 |
|------|--------|--------------|
| **성능** | 글로벌 CDN (빠름) | 가정용 인터넷 (느림) |
| **배포** | Git push → 자동 배포 | 수동 배포 필요 |
| **HTTPS** | 자동 SSL 인증서 | 수동 설정 필요 |
| **비용** | **무료** | 전기세 |
| **도메인** | 무료 .vercel.app | Tailscale 필요 |
| **확장성** | 무제한 트래픽 | 대역폭 제한 |

**결론**: 프론트엔드는 Vercel, 백엔드는 라즈베리파이가 최적! 🚀

---

## 📋 전체 아키텍처

```
┌─────────────────┐
│   사용자 브라우저   │
└────────┬────────┘
         │ HTTPS
         ▼
┌─────────────────┐
│  Vercel CDN     │ ← 프론트엔드 (HTML/CSS/JS)
│  (전세계 분산)    │
└────────┬────────┘
         │ API 호출
         │ https://leeeunseok.tail32c3e2.ts.net
         ▼
┌─────────────────┐
│ 라즈베리파이      │ ← 백엔드 API
│ (FastAPI)       │
└─────────────────┘
```

---

## 1️⃣ Vercel 계정 생성 (2분)

### 준비물
- GitHub 계정 (필수)
- 이메일 주소

### 단계

1. **Vercel 가입**
   ```
   https://vercel.com/signup
   ```

2. **GitHub로 로그인**
   - "Continue with GitHub" 클릭
   - Authorize 승인

3. **완료!**
   - Vercel 대시보드 접속 확인

---

## 2️⃣ 프로젝트 설정 (5분)

### Vercel 설정 파일 생성

프로젝트 루트에 `vercel.json` 생성:

```bash
cd /c/sideproject
nano vercel.json
```

**내용:**

```json
{
  "version": 2,
  "name": "biz-retriever-frontend",
  "builds": [
    {
      "src": "frontend/**",
      "use": "@vercel/static"
    }
  ],
  "routes": [
    {
      "src": "/(.*)",
      "dest": "/frontend/$1"
    }
  ],
  "headers": [
    {
      "source": "/(.*)",
      "headers": [
        {
          "key": "Access-Control-Allow-Origin",
          "value": "*"
        },
        {
          "key": "Access-Control-Allow-Methods",
          "value": "GET, POST, PUT, DELETE, OPTIONS"
        },
        {
          "key": "Access-Control-Allow-Headers",
          "value": "Content-Type, Authorization"
        }
      ]
    }
  ]
}
```

### 환경 변수 파일 생성

`frontend/.env.production` 생성:

```bash
cd frontend
nano .env.production
```

**내용:**

```bash
VITE_API_URL=https://leeeunseok.tail32c3e2.ts.net
VITE_API_BASE_URL=https://leeeunseok.tail32c3e2.ts.net/api/v1
```

---

## 3️⃣ 백엔드 CORS 설정 (중요!)

라즈베리파이 백엔드에서 Vercel 도메인 허용:

### `app/core/config.py` 확인

```python
class Settings(BaseSettings):
    # CORS 설정
    BACKEND_CORS_ORIGINS: list[str] = [
        "http://localhost:3001",
        "http://localhost:3000",
        "https://leeeunseok.tail32c3e2.ts.net",
        "https://*.vercel.app",  # Vercel 도메인 허용
    ]
```

### 현재 CORS 설정 확인

```bash
ssh admin@100.75.72.6 "cd /home/admin/projects/biz-retriever && grep -A 5 'BACKEND_CORS_ORIGINS' app/core/config.py"
```

### CORS 설정 업데이트 (필요시)

```bash
# 로컬에서 수정 후
git add app/core/config.py
git commit -m "feat(cors): Add Vercel domain to CORS origins"
git push origin master

# 라즈베리파이에서
ssh admin@100.75.72.6 "cd /home/admin/projects/biz-retriever && git pull origin master && docker compose restart api"
```

---

## 4️⃣ Vercel 배포 (5분)

### 옵션 A: Vercel CLI (권장)

```bash
# 1. Vercel CLI 설치
npm install -g vercel

# 2. 로그인
vercel login

# 3. 프로젝트 디렉토리로 이동
cd /c/sideproject

# 4. 배포
vercel

# 처음 배포 시 질문 답변:
# Set up and deploy? Y
# Which scope? (본인 계정 선택)
# Link to existing project? N
# Project name? biz-retriever-frontend
# In which directory is your code located? frontend
# Want to override settings? N

# 5. 프로덕션 배포
vercel --prod
```

### 옵션 B: GitHub 연동 (자동 배포)

1. **GitHub에 푸시**
   ```bash
   git add vercel.json frontend/.env.production
   git commit -m "feat(deploy): Add Vercel deployment configuration"
   git push origin master
   ```

2. **Vercel 대시보드**
   - https://vercel.com/dashboard
   - "New Project" 클릭
   - GitHub 저장소 선택: `biz-retriever`
   - "Import" 클릭

3. **프로젝트 설정**
   ```
   Project Name: biz-retriever-frontend
   Framework Preset: Other
   Root Directory: frontend
   Build Command: (비워두기 - 정적 사이트)
   Output Directory: . (현재 디렉토리)
   ```

4. **환경 변수 추가**
   - Settings → Environment Variables
   ```
   VITE_API_URL = https://leeeunseok.tail32c3e2.ts.net
   VITE_API_BASE_URL = https://leeeunseok.tail32c3e2.ts.net/api/v1
   ```

5. **Deploy 클릭**
   - 자동 빌드 시작
   - 완료 시 URL 제공 (예: `https://biz-retriever-frontend.vercel.app`)

---

## 5️⃣ 프론트엔드 코드 수정

### API URL 동적 설정

`frontend/js/config.js` 생성:

```javascript
// API URL 설정 (환경에 따라 자동 선택)
const API_URL = import.meta.env?.VITE_API_URL || 
                process.env?.VITE_API_URL ||
                'https://leeeunseok.tail32c3e2.ts.net';

const API_BASE_URL = import.meta.env?.VITE_API_BASE_URL ||
                     process.env?.VITE_API_BASE_URL ||
                     `${API_URL}/api/v1`;

export { API_URL, API_BASE_URL };
```

### 기존 HTML 파일 수정

`frontend/dashboard.html` 등에서:

```html
<!-- 기존 -->
<script>
  const API_URL = 'http://localhost:8000';
</script>

<!-- 변경 후 -->
<script type="module">
  import { API_BASE_URL } from './js/config.js';
  
  // API 호출 예시
  fetch(`${API_BASE_URL}/bids/`)
    .then(response => response.json())
    .then(data => console.log(data));
</script>
```

---

## 6️⃣ 배포 확인 및 테스트

### 배포 URL 확인

Vercel CLI 사용 시:
```bash
vercel inspect
```

출력 예시:
```
Production: https://biz-retriever-frontend.vercel.app
Latest: https://biz-retriever-frontend-abc123.vercel.app
```

### 브라우저 테스트

1. **배포된 URL 접속**
   ```
   https://biz-retriever-frontend.vercel.app
   ```

2. **개발자 도구 열기** (F12)
   - Network 탭 확인
   - API 호출이 `https://leeeunseok.tail32c3e2.ts.net`로 가는지 확인

3. **CORS 에러 체크**
   - Console에 CORS 에러가 없어야 함
   - 만약 에러가 있다면 백엔드 CORS 설정 재확인

### 기능 테스트

- [ ] 메인 페이지 로드
- [ ] 회원가입
- [ ] 로그인
- [ ] 대시보드 데이터 로드
- [ ] API 호출 (Network 탭에서 200 OK 확인)

---

## 7️⃣ 커스텀 도메인 연결 (선택사항)

### Vercel에서 커스텀 도메인 추가

1. **Vercel 대시보드**
   - Project → Settings → Domains

2. **도메인 추가**
   - 본인 도메인 입력 (예: `biz-retriever.com`)
   - Vercel이 DNS 설정 안내 제공

3. **DNS 레코드 추가** (도메인 제공업체에서)
   ```
   Type: A
   Name: @
   Value: 76.76.21.21
   
   Type: CNAME
   Name: www
   Value: cname.vercel-dns.com
   ```

4. **SSL 인증서 자동 발급**
   - Vercel이 자동으로 Let's Encrypt 인증서 발급
   - 몇 분 후 HTTPS 접속 가능

---

## 🔄 자동 배포 (CI/CD)

GitHub 연동 시 자동 배포:

```bash
# 1. 프론트엔드 코드 수정
nano frontend/dashboard.html

# 2. Git 커밋
git add frontend/
git commit -m "feat(ui): Update dashboard design"

# 3. Push
git push origin master

# 4. Vercel이 자동으로 배포 시작!
# 5. 약 30초 후 배포 완료
```

**배포 알림:**
- Vercel 이메일 알림
- Slack 연동 가능

---

## 📊 성능 최적화

### Vercel 자동 최적화

Vercel이 자동으로:
- ✅ 이미지 최적화 (WebP 변환)
- ✅ CSS/JS 압축
- ✅ Gzip 압축
- ✅ HTTP/2 지원
- ✅ 전세계 CDN 캐싱

### 추가 최적화 (선택사항)

`vercel.json`에 추가:

```json
{
  "headers": [
    {
      "source": "/(.*)",
      "headers": [
        {
          "key": "Cache-Control",
          "value": "public, max-age=31536000, immutable"
        }
      ]
    }
  ]
}
```

---

## 🚨 트러블슈팅

### CORS 에러

**증상:**
```
Access to fetch at 'https://leeeunseok.tail32c3e2.ts.net/api/v1/bids/' 
from origin 'https://biz-retriever-frontend.vercel.app' 
has been blocked by CORS policy
```

**해결:**
1. 백엔드 `app/core/config.py`에 Vercel 도메인 추가:
   ```python
   BACKEND_CORS_ORIGINS: list[str] = [
       "https://*.vercel.app",
   ]
   ```

2. API 재시작:
   ```bash
   ssh admin@100.75.72.6 "cd /home/admin/projects/biz-retriever && docker compose restart api"
   ```

### API URL이 localhost로 호출됨

**원인:** 환경 변수가 적용되지 않음

**해결:**
1. `frontend/js/config.js` 확인
2. Vercel 환경 변수 설정 확인
3. 재배포: `vercel --prod`

### 빌드 실패

**로그 확인:**
```bash
vercel logs
```

**일반적인 원인:**
- Node.js 버전 호환성
- 의존성 설치 실패
- 환경 변수 누락

---

## 📈 모니터링

### Vercel Analytics

무료 분석 도구:
- 페이지 뷰
- 고유 방문자
- 성능 메트릭
- 지역별 트래픽

**활성화:**
1. Vercel 대시보드
2. Analytics 탭
3. Enable Analytics

---

## 💰 비용

### Vercel Free Tier

| 항목 | 한도 |
|------|------|
| **대역폭** | 100GB/월 |
| **빌드 시간** | 6,000분/월 |
| **배포** | 무제한 |
| **도메인** | 무제한 |
| **팀 멤버** | 1명 |

**결론:** 개인 프로젝트는 **영구 무료**! 🎉

---

## 🎯 최종 체크리스트

배포 완료 확인:

- [ ] Vercel 계정 생성
- [ ] `vercel.json` 추가
- [ ] 환경 변수 설정 (API URL)
- [ ] CORS 설정 (백엔드)
- [ ] Vercel 배포 완료
- [ ] 브라우저에서 접속 확인
- [ ] API 호출 테스트
- [ ] 회원가입/로그인 테스트
- [ ] Git 자동 배포 확인

---

## 📞 다음 단계

1. **프론트엔드 배포 완료**
   ```
   https://biz-retriever-frontend.vercel.app
   ```

2. **백엔드 계속 운영**
   ```
   https://leeeunseok.tail32c3e2.ts.net
   ```

3. **라즈베리파이 리소스 절약**
   ```bash
   # frontend 컨테이너 제거 (docker-compose.yml에서)
   # 메모리 약 200MB 절약!
   ```

4. **클라이언트 시연 준비**
   - Vercel URL로 시연 (빠르고 안정적!)
   - 백엔드는 라즈베리파이 (비용 절감)

---

**배포 성공을 기원합니다! 🚀**

**Last Updated**: 2026-01-31  
**Deployment Time**: ~10분  
**Cost**: $0 (완전 무료!)
