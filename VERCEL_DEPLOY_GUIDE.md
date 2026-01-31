# Vercel 배포 실행 가이드

> Vercel CLI 로그인 에러 우회: GitHub 연동을 통한 자동 배포 (권장)

## ⚠️ CLI 로그인 이슈

**문제:**
```
Error: 링크웍스 @ vercel 50.9.6 is not a legal HTTP header value
```

**원인:** Windows 사용자 이름에 한글이 포함되어 있어 HTTP 헤더 에러 발생

**해결:** GitHub 연동 사용 (더 안전하고 편리함)

---

## 🚀 GitHub 연동 배포 (권장)

### 1️⃣ Vercel 계정 생성 (2분)

1. **Vercel 웹사이트 접속**
   ```
   https://vercel.com/signup
   ```

2. **GitHub로 로그인**
   - "Continue with GitHub" 클릭
   - GitHub 계정으로 로그인
   - Vercel 권한 승인

3. **완료!**

---

### 2️⃣ 프로젝트 연동 (3분)

1. **Vercel 대시보드**
   ```
   https://vercel.com/dashboard
   ```

2. **"Add New" → "Project" 클릭**

3. **GitHub 저장소 연결**
   - "Import Git Repository" 선택
   - `biz-retriever` 저장소 찾기
   - "Import" 클릭

4. **프로젝트 설정** ⚠️ 중요!
   ```
   Project Name: biz-retriever-frontend (또는 원하는 이름)
   Framework Preset: Other
   Root Directory: frontend/
   Build Command: (완전히 비워두기 - 입력하지 마세요!)
   Output Directory: (비워두기)
   Install Command: (비워두기)
   ```
   
   **⚠️ 주의사항:**
   - **Build Command 필드를 완전히 비워야 합니다!**
   - 이 프로젝트는 정적 HTML 사이트입니다 (빌드 불필요)
   - TypeScript 빌드 스크립트가 있지만 실제로는 사용되지 않습니다
   - Build Command를 입력하면 `npm run build exited with 126` 오류 발생

5. **환경 변수** (선택사항, 권장하지 않음)
   - 환경 변수는 **필요 없습니다**
   - 프론트엔드 JavaScript가 자동으로 API URL을 감지합니다:
     - Vercel 배포: `https://leeeunseok.tail32c3e2.ts.net/api/v1`
     - Local 개발: `http://localhost:8000/api/v1`
   - 설정하려면 (선택사항):
     ```
     Name: VITE_API_URL
     Value: https://leeeunseok.tail32c3e2.ts.net
     ```

6. **"Deploy" 클릭**
   - 자동 빌드 시작 (약 30초)
   - 완료 시 배포 URL 생성

---

### 3️⃣ 배포 완료 확인

**배포 URL 확인:**
```
https://biz-retriever-frontend.vercel.app
```
또는
```
https://biz-retriever-frontend-<hash>.vercel.app
```

**브라우저 테스트:**
1. 배포된 URL 접속
2. F12 (개발자 도구) 열기
3. Network 탭에서 API 호출 확인
4. CORS 에러 없는지 확인

---

## 🔄 자동 배포 설정 완료!

이제부터:
```bash
# 코드 수정
git add .
git commit -m "Update frontend"
git push origin master

# Vercel이 자동으로 배포 시작!
# 약 30초 후 배포 완료
```

---

## 🎯 배포 URL 커스터마이징

### 프로젝트 도메인 변경

1. **Vercel Dashboard → Settings → Domains**

2. **Production Domain 설정**
   ```
   biz-retriever-frontend.vercel.app
   ```

3. **저장**

---

## 📊 배포 확인 체크리스트

배포 후 확인:

- [ ] 배포 URL 접속 성공
- [ ] 메인 페이지 (index.html) 로드
- [ ] 대시보드 (/dashboard) 접속
- [ ] Kanban (/kanban) 접속
- [ ] API 호출 테스트 (Network 탭)
- [ ] CORS 에러 없음
- [ ] 회원가입/로그인 테스트
- [ ] 데이터 로드 확인

---

## 🔧 트러블슈팅

### 1. Build Error: npm run build exited with 126

**증상:**
```
Error: Command "npm run build" exited with 126
```

**원인:** 
- Build Command 필드에 값이 입력되어 있음
- 이 프로젝트는 정적 HTML 사이트로 빌드가 필요 없음
- TypeScript 파일(`src/`)은 실제로 사용되지 않음

**해결:**
1. Vercel Dashboard → Settings → General
2. **Build & Development Settings**에서:
   - Build Command: **완전히 비워두기** (Override 체크 해제)
   - Install Command: 비워두기
   - Output Directory: 비워두기
3. **Save** 클릭
4. **Deployments** → 최신 배포 → **Redeploy**

**확인:**
```
✅ Cloning repository...
✅ Analyzing source code...
✅ Deploying... (빌드 단계 건너뜀)
✅ Deployment completed!
```

### 2. vercel.json Configuration Error

**증상:**
```
If `rewrites`, `redirects`, `headers`, `cleanUrls` or `trailingSlash` 
are used, then `routes` cannot be present.
```

**원인:** `routes` (구형 설정)와 `headers`를 동시에 사용

**해결:** ✅ 이미 수정 완료 (커밋 `198c183`)
- `routes` 제거됨
- `cleanUrls: true` 사용 중

### 3. 404 Not Found

**원인:** Root Directory 설정 오류

**해결:**
1. Vercel Dashboard → Settings → General
2. Root Directory: `frontend/` 확인
3. Redeploy

### 4. CORS 에러

**증상:**
```
Access to fetch blocked by CORS policy
```

**해결:**
- **대부분의 경우 CORS 설정 필요 없음** (이미 `*.vercel.app` 허용됨)
- 커스텀 도메인 사용 시에만 업데이트 필요:

```bash
# 1. 정확한 Vercel URL 확인
예: https://biz-retriever-frontend.vercel.app

# 2. 백엔드 CORS 업데이트 (커스텀 도메인만)
ssh admin@100.75.72.6
cd /home/admin/projects/biz-retriever
nano app/core/config.py

# CORS_ORIGINS에 추가 (커스텀 도메인인 경우):
"https://your-custom-domain.com",

# 3. API 재시작
docker compose restart api
```

### 5. API 연결 안 됨

**체크리스트:**
- [ ] 라즈베리파이 API 실행 중: `ssh admin@100.75.72.6 "curl http://localhost:8000/health"`
- [ ] Tailscale Funnel 활성화: `https://leeeunseok.tail32c3e2.ts.net/health`
- [ ] 환경 변수 설정 확인 (Vercel Dashboard)
- [ ] 브라우저 Console에서 API URL 확인

---

## 📱 모바일 테스트

배포 URL은 모바일에서도 접속 가능:
```
https://biz-retriever-frontend.vercel.app
```

**테스트:**
- [ ] 스마트폰 브라우저에서 접속
- [ ] 반응형 디자인 확인
- [ ] 터치 인터페이스 동작 확인

---

## 🎉 배포 완료!

### 최종 구조

```
사용자 브라우저
      ↓ HTTPS
Vercel CDN (프론트엔드) ✅ 배포 완료!
https://biz-retriever-frontend.vercel.app
      ↓ API 호출
라즈베리파이 (백엔드) ✅ 실행 중!
https://leeeunseok.tail32c3e2.ts.net
```

### 접속 URL

**프론트엔드 (Vercel):**
```
https://biz-retriever-frontend.vercel.app
```

**백엔드 API (라즈베리파이):**
```
https://leeeunseok.tail32c3e2.ts.net/docs
```

---

## 📞 다음 단계

1. **배포 URL 테스트**
   - 모든 페이지 접속 확인
   - API 연동 확인

2. **클라이언트 시연**
   - Vercel URL로 시연
   - 빠른 로딩 속도 강조
   - 안정성 어필

3. **선택사항: 커스텀 도메인**
   - 도메인 구입 후 Vercel 연결
   - 자동 HTTPS 적용

---

**배포 성공! 🚀**
**Vercel CLI 에러 우회 완료**
**GitHub 자동 배포 설정 완료**
