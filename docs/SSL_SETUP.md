# SSL/HTTPS 설정 가이드

## 개요

이 문서는 Tailscale Funnel 도메인(`leeeunseok.tail32c3e2.ts.net`)에 Let's Encrypt SSL 인증서를 적용하고, HTTP → HTTPS 리다이렉트 및 보안 헤더를 설정하는 절차를 설명합니다.

**목표:**
- ✅ Let's Encrypt 무료 SSL 인증서 발급
- ✅ HTTP → HTTPS 자동 리다이렉트
- ✅ HSTS 헤더로 HTTPS 강제
- ✅ 90일 만료 전 30일에 자동 갱신
- ✅ 개인정보보호법(PIPA) 준수

---

## 1. 사전 요구사항

### 1.1 필수 구성 요소
- **Nginx Proxy Manager**: 리버스 프록시 및 SSL 관리
- **Docker Compose**: 컨테이너 오케스트레이션
- **Tailscale Funnel**: 공개 도메인 제공

### 1.2 현재 설정 확인
```bash
# docker-compose.pi.yml에서 nginx-proxy-manager 서비스 확인
docker ps | grep nginx-proxy-manager

# 포트 확인
# - 80: HTTP
# - 443: HTTPS
# - 81: 관리 대시보드
```

---

## 2. Nginx Proxy Manager 설정

### 2.1 Nginx Proxy Manager 접속

1. **관리 대시보드 접속**
   ```
   URL: http://localhost:81
   기본 이메일: admin@example.com
   기본 비밀번호: changeme
   ```

2. **첫 로그인 시 비밀번호 변경**
   - 강력한 비밀번호로 변경 필수

### 2.2 Proxy Host 생성

**메뉴: Proxy Hosts → Add Proxy Host**

#### 설정 항목

| 항목 | 값 | 설명 |
|------|-----|------|
| Domain Names | `leeeunseok.tail32c3e2.ts.net` | Tailscale Funnel 도메인 |
| Scheme | `http` | 백엔드 프로토콜 |
| Forward Hostname/IP | `frontend` | Docker 네트워크 내 서비스명 |
| Forward Port | `80` | 프론트엔드 포트 |
| Cache Assets | ✓ | 정적 자산 캐싱 활성화 |
| Block Common Exploits | ✓ | 일반적인 공격 차단 |
| Websockets Support | ✓ | WebSocket 지원 |

#### 고급 설정 (Advanced)

```nginx
# Custom Nginx Configuration
proxy_set_header X-Real-IP $remote_addr;
proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
proxy_set_header X-Forwarded-Proto $scheme;
proxy_set_header X-Forwarded-Host $host;
proxy_set_header X-Forwarded-Port $server_port;
```

### 2.3 SSL 인증서 발급

**탭: SSL → Request a new SSL Certificate**

#### Let's Encrypt 설정

| 항목 | 값 | 설명 |
|------|-----|------|
| Email Address | `your-email@example.com` | Let's Encrypt 알림 이메일 |
| Use a DNS challenge | ✓ | DNS 검증 방식 (권장) |
| Agree to Let's Encrypt Terms | ✓ | 약관 동의 |
| Use staging Let's Encrypt server | ☐ | 테스트 환경 (프로덕션은 미체크) |

**DNS 검증 절차:**
1. Nginx Proxy Manager가 DNS TXT 레코드 생성 지시
2. Tailscale DNS 설정에서 TXT 레코드 추가
3. DNS 전파 대기 (보통 5-10분)
4. 자동 검증 및 인증서 발급

#### 인증서 발급 확인
```bash
# 발급된 인증서 확인
ls -la /data/letsencrypt/live/leeeunseok.tail32c3e2.ts.net/

# 인증서 유효성 확인
openssl x509 -in /data/letsencrypt/live/leeeunseok.tail32c3e2.ts.net/fullchain.pem -noout -dates
```

---

## 3. HTTP → HTTPS 리다이렉트 설정

### 3.1 Nginx Proxy Manager에서 리다이렉트 설정

**메뉴: Proxy Hosts → [생성한 호스트] → Edit**

**탭: SSL → Force SSL**
- ✓ **Force SSL** 활성화
- 옵션: "Redirect" 선택

이 설정으로 모든 HTTP 요청이 HTTPS로 자동 리다이렉트됩니다.

### 3.2 수동 Nginx 설정 (선택사항)

파일: `nginx/redirect-https.conf`

```nginx
server {
    listen 80;
    server_name leeeunseok.tail32c3e2.ts.net;
    
    # HTTP → HTTPS 리다이렉트
    return 301 https://$host$request_uri;
}
```

---

## 4. 보안 헤더 설정

### 4.1 HSTS (HTTP Strict-Transport-Security)

**목적**: 브라우저에 HTTPS만 사용하도록 강제

```nginx
add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;
```

**설명:**
- `max-age=31536000`: 1년(31536000초) 동안 HTTPS 강제
- `includeSubDomains`: 서브도메인도 HTTPS 강제
- `always`: 모든 응답에 헤더 추가 (에러 응답 포함)

### 4.2 X-Frame-Options

**목적**: Clickjacking 공격 방지

```nginx
add_header X-Frame-Options "SAMEORIGIN" always;
```

**옵션:**
- `DENY`: 모든 프레임 차단
- `SAMEORIGIN`: 같은 도메인의 프레임만 허용 (권장)
- `ALLOW-FROM uri`: 특정 도메인만 허용

### 4.3 X-Content-Type-Options

**목적**: MIME 타입 스니핑 방지

```nginx
add_header X-Content-Type-Options "nosniff" always;
```

### 4.4 X-XSS-Protection

**목적**: XSS(Cross-Site Scripting) 공격 방지

```nginx
add_header X-XSS-Protection "1; mode=block" always;
```

### 4.5 Referrer-Policy

**목적**: Referrer 정보 노출 제한

```nginx
add_header Referrer-Policy "strict-origin-when-cross-origin" always;
```

**옵션:**
- `no-referrer`: Referrer 정보 전송 안 함
- `strict-origin-when-cross-origin`: HTTPS에서 HTTPS로만 Referrer 전송 (권장)

### 4.6 Permissions-Policy

**목적**: 브라우저 기능 접근 제한

```nginx
add_header Permissions-Policy "geolocation=(), microphone=(), camera=()" always;
```

**제한 기능:**
- `geolocation=()`: 위치 정보 접근 차단
- `microphone=()`: 마이크 접근 차단
- `camera=()`: 카메라 접근 차단

### 4.7 Nginx Proxy Manager에서 헤더 추가

**메뉴: Proxy Hosts → [생성한 호스트] → Edit → Advanced**

```nginx
# Custom Nginx Configuration
add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;
add_header X-Frame-Options "SAMEORIGIN" always;
add_header X-Content-Type-Options "nosniff" always;
add_header X-XSS-Protection "1; mode=block" always;
add_header Referrer-Policy "strict-origin-when-cross-origin" always;
add_header Permissions-Policy "geolocation=(), microphone=(), camera=()" always;
```

---

## 5. FastAPI 보안 설정

### 5.1 TrustedHostMiddleware 추가

파일: `app/main.py`

```python
from fastapi.middleware.trustedhost import TrustedHostMiddleware

# CORS 미들웨어 이전에 추가
app.add_middleware(
    TrustedHostMiddleware,
    allowed_hosts=["leeeunseok.tail32c3e2.ts.net", "localhost", "127.0.0.1"]
)
```

**목적**: Host 헤더 검증으로 Host Header Injection 공격 방지

### 5.2 Cookie 보안 설정 확인

파일: `app/api/endpoints/auth.py`

```python
response.set_cookie(
    key="access_token",
    value=access_token,
    httponly=True,      # ✓ JavaScript 접근 차단 (XSS 방지)
    secure=True,        # ✓ HTTPS만 전송
    samesite="lax",     # ✓ CSRF 공격 방지
    max_age=60 * 60 * 24 * 8,  # 8일
    path="/"
)
```

**설정 설명:**
- `httponly=True`: JavaScript에서 쿠키 접근 불가 (XSS 방지)
- `secure=True`: HTTPS 연결에서만 쿠키 전송
- `samesite="lax"`: 크로스 사이트 요청에서 쿠키 제한 (CSRF 방지)

---

## 6. 자동 갱신 설정

### 6.1 Let's Encrypt 인증서 갱신 주기

- **발급 유효기간**: 90일
- **자동 갱신**: 60일 경과 후 (30일 여유)
- **갱신 방식**: Nginx Proxy Manager 자동 처리

### 6.2 갱신 상태 확인

**Nginx Proxy Manager 대시보드:**
- Proxy Hosts 목록에서 SSL 상태 확인
- 만료 예정 날짜 표시

**명령어:**
```bash
# 인증서 만료 날짜 확인
openssl x509 -in /data/letsencrypt/live/leeeunseok.tail32c3e2.ts.net/fullchain.pem -noout -dates

# 예상 출력:
# notBefore=Jan 30 12:00:00 2026 GMT
# notAfter=Apr 30 12:00:00 2026 GMT
```

### 6.3 갱신 실패 시 대응

**이메일 알림:**
- Let's Encrypt에서 만료 30일 전 알림 이메일 발송
- 등록된 이메일 주소 확인

**수동 갱신:**
```bash
# Nginx Proxy Manager 컨테이너 접속
docker exec -it nginx-proxy-manager /bin/sh

# 인증서 갱신 시도
certbot renew --force-renewal
```

---

## 7. 검증 및 테스트

### 7.1 HTTP → HTTPS 리다이렉트 확인

```bash
# HTTP 요청 → HTTPS 리다이렉트 확인
curl -I http://leeeunseok.tail32c3e2.ts.net

# 예상 출력:
# HTTP/1.1 301 Moved Permanently
# Location: https://leeeunseok.tail32c3e2.ts.net/
```

### 7.2 HTTPS 접속 및 헤더 확인

```bash
# HTTPS 접속 확인
curl -I https://leeeunseok.tail32c3e2.ts.net

# 예상 출력:
# HTTP/2 200
# strict-transport-security: max-age=31536000; includeSubDomains
# x-frame-options: SAMEORIGIN
# x-content-type-options: nosniff
# x-xss-protection: 1; mode=block
# referrer-policy: strict-origin-when-cross-origin
# permissions-policy: geolocation=(), microphone=(), camera=()
```

### 7.3 SSL 인증서 유효성 확인

```bash
# 인증서 정보 확인
openssl s_client -connect leeeunseok.tail32c3e2.ts.net:443 -servername leeeunseok.tail32c3e2.ts.net < /dev/null 2>/dev/null | openssl x509 -noout -dates

# 예상 출력:
# notBefore=Jan 30 12:00:00 2026 GMT
# notAfter=Apr 30 12:00:00 2026 GMT

# 인증서 발급자 확인
openssl s_client -connect leeeunseok.tail32c3e2.ts.net:443 -servername leeeunseok.tail32c3e2.ts.net < /dev/null 2>/dev/null | openssl x509 -noout -issuer

# 예상 출력:
# issuer=C = US, O = Let's Encrypt, CN = R3
```

### 7.4 보안 헤더 검증 스크립트

```bash
#!/bin/bash
# 파일: scripts/verify-ssl.sh

DOMAIN="leeeunseok.tail32c3e2.ts.net"

echo "=== SSL/HTTPS 보안 검증 ==="
echo ""

echo "1️⃣  HTTP → HTTPS 리다이렉트 확인"
curl -I http://$DOMAIN 2>/dev/null | head -3
echo ""

echo "2️⃣  HTTPS 접속 확인"
curl -I https://$DOMAIN 2>/dev/null | head -1
echo ""

echo "3️⃣  보안 헤더 확인"
curl -I https://$DOMAIN 2>/dev/null | grep -E "strict-transport-security|x-frame-options|x-content-type-options|x-xss-protection|referrer-policy|permissions-policy"
echo ""

echo "4️⃣  SSL 인증서 유효성"
openssl s_client -connect $DOMAIN:443 -servername $DOMAIN < /dev/null 2>/dev/null | openssl x509 -noout -dates
echo ""

echo "5️⃣  인증서 발급자"
openssl s_client -connect $DOMAIN:443 -servername $DOMAIN < /dev/null 2>/dev/null | openssl x509 -noout -issuer
echo ""

echo "✅ 검증 완료"
```

---

## 8. 문제 해결

### 8.1 인증서 발급 실패

**증상**: "Failed to issue certificate"

**원인 및 해결:**
1. **DNS 설정 미완료**
   - Tailscale DNS에 TXT 레코드 추가 확인
   - DNS 전파 대기 (5-10분)

2. **도메인 접근 불가**
   - Tailscale Funnel이 활성화되어 있는지 확인
   - 방화벽 설정 확인

3. **Let's Encrypt 레이트 제한**
   - 같은 도메인에 대해 주당 50회 발급 제한
   - 테스트 환경에서는 staging 서버 사용

### 8.2 HSTS 헤더 적용 안 됨

**증상**: curl 결과에 HSTS 헤더 없음

**해결:**
1. Nginx Proxy Manager 설정 재확인
2. 컨테이너 재시작
   ```bash
   docker restart nginx-proxy-manager
   ```
3. 브라우저 캐시 삭제

### 8.3 쿠키 보안 경고

**증상**: "Cookie sent over insecure connection"

**해결:**
- `secure=True` 설정 확인
- HTTPS 연결 확인
- 브라우저 개발자 도구에서 쿠키 설정 검증

---

## 9. 보안 체크리스트

- [ ] Let's Encrypt SSL 인증서 발급 완료
- [ ] HTTP → HTTPS 리다이렉트 설정
- [ ] HSTS 헤더 추가 (max-age=31536000)
- [ ] X-Frame-Options 설정 (SAMEORIGIN)
- [ ] X-Content-Type-Options 설정 (nosniff)
- [ ] X-XSS-Protection 설정 (1; mode=block)
- [ ] Referrer-Policy 설정 (strict-origin-when-cross-origin)
- [ ] Permissions-Policy 설정 (geolocation, microphone, camera 차단)
- [ ] FastAPI TrustedHostMiddleware 추가
- [ ] Cookie secure=True, SameSite="lax" 설정
- [ ] 자동 갱신 설정 확인
- [ ] 검증 테스트 완료

---

## 10. 참고 자료

- [Let's Encrypt 공식 문서](https://letsencrypt.org/docs/)
- [Nginx Proxy Manager 문서](https://nginxproxymanager.com/)
- [OWASP 보안 헤더 가이드](https://owasp.org/www-project-secure-headers/)
- [MDN HTTP 헤더 참고](https://developer.mozilla.org/en-US/docs/Web/HTTP/Headers)
- [개인정보보호법(PIPA) 기술적 보호조치](https://www.pipc.go.kr/)

---

**작성일**: 2026-01-30  
**버전**: 1.0  
**상태**: 프로덕션 준비 완료
