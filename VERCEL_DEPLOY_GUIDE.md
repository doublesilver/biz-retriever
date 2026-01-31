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

4. **프로젝트 설정**
   ```
   Project Name: biz-retriever-frontend
   Framework Preset: Other
   Root Directory: frontend/
   Build Command: (비워두기)
   Output Directory: .
   Install Command: (비워두기)
   ```

5. **환경 변수 추가**
   - "Environment Variables" 섹션에서:
   ```
   Name: VITE_API_URL
   Value: https://leeeunseok.tail32c3e2.ts.net
   
   Name: VITE_API_BASE_URL
   Value: https://leeeunseok.tail32c3e2.ts.net/api/v1
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

### 1. 404 Not Found

**원인:** Root Directory 설정 오류

**해결:**
1. Vercel Dashboard → Settings → General
2. Root Directory: `frontend/` 확인
3. Redeploy

### 2. CORS 에러

**증상:**
```
Access to fetch blocked by CORS policy
```

**해결:**
```bash
# 1. 정확한 Vercel URL 확인
예: https://biz-retriever-frontend.vercel.app

# 2. 백엔드 CORS 업데이트 (필요시)
ssh admin@100.75.72.6
cd /home/admin/projects/biz-retriever
nano app/core/config.py

# CORS_ORIGINS에 추가:
"https://biz-retriever-frontend.vercel.app",

# 3. API 재시작
docker compose restart api
```

### 3. API 연결 안 됨

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
