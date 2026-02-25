# DDoS 방어 및 Rate Limiting 가이드

> **작성일**: 2026-01-30  
> **대상 환경**: Raspberry Pi 4 (4GB RAM) + Nginx + FastAPI  
> **보안 목표**: DDoS 공격 방어, API 남용 방지, 브루트포스 차단

---

## 목차
- [개요](#개요)
- [적용된 보안 설정](#적용된-보안-설정)
- [Nginx 설정 파일](#nginx-설정-파일)
- [FastAPI Rate Limiting](#fastapi-rate-limiting)
- [Fail2Ban 자동 차단](#fail2ban-자동-차단)
- [모니터링 및 검증](#모니터링-및-검증)
- [문제 해결](#문제-해결)

---

## 개요

### DDoS 공격 유형 및 대응

| 공격 유형 | 설명 | 대응 방법 |
|----------|------|-----------|
| **HTTP Flood** | 대량의 HTTP 요청으로 서버 과부하 | Nginx Rate Limiting |
| **Slowloris** | 느린 HTTP 요청으로 연결 고갈 | Timeout 설정 |
| **Large Request** | 대용량 요청으로 메모리 소진 | Request Size 제한 |
| **Brute Force** | 로그인 반복 시도 | 로그인 Rate Limit |
| **Bot Attack** | 악성 봇 트래픽 | User-Agent 차단 |

### 방어 계층 (Defense in Depth)

```
Layer 1: Nginx Rate Limiting (10 req/s)
         ↓
Layer 2: Nginx DDoS Protection (Timeout, Size Limit)
         ↓
Layer 3: FastAPI SlowAPI (15 req/min)
         ↓
Layer 4: Fail2Ban (자동 IP 차단)
         ↓
Layer 5: Monitoring (Prometheus Alert)
```

---

## 적용된 보안 설정

### 1. Nginx Rate Limiting

**파일**: `nginx/rate-limit.conf`

#### 설정 요약

| Zone | Rate | Burst | 용도 |
|------|------|-------|------|
| `api_limit` | 10 req/s | 20 | API 엔드포인트 |
| `static_limit` | 50 req/s | 100 | 정적 파일 (CSS, JS, 이미지) |
| `login_limit` | 5 req/m | 2 | 로그인 엔드포인트 (브루트포스 방어) |
| `conn_limit_per_ip` | 10 동시 연결 | - | IP당 최대 연결 수 |

#### 작동 원리

```nginx
# API 요청 제한
location /api/ {
    limit_req zone=api_limit burst=20 nodelay;
    limit_req_status 429;  # Too Many Requests
    proxy_pass http://api:8000;
}
```

**예시**:
- 평상시: 초당 10개 요청까지 즉시 처리
- 순간 폭주: 추가 20개를 큐에 저장 (총 30개)
- 초과 시: HTTP 429 반환

---

### 2. DDoS Protection (Nginx)

**파일**: `nginx/ddos-protection.conf`

#### 타임아웃 설정 (슬로우 로리스 방어)

| 설정 | 값 | 설명 |
|------|-----|------|
| `client_body_timeout` | 10s | 요청 바디 읽기 제한 |
| `client_header_timeout` | 10s | 헤더 읽기 제한 |
| `keepalive_timeout` | 30s | Keep-Alive 연결 제한 |
| `send_timeout` | 10s | 응답 전송 제한 |

#### 요청 크기 제한

| 설정 | 값 | 설명 |
|------|-----|------|
| `client_max_body_size` | 10M | 파일 업로드 최대 크기 |
| `client_body_buffer_size` | 128k | 바디 버퍼 크기 |
| `client_header_buffer_size` | 1k | 헤더 버퍼 크기 |
| `large_client_header_buffers` | 4 x 8k | 큰 헤더용 버퍼 |

#### 악성 User-Agent 차단

```nginx
map $http_user_agent $bad_bot {
    default 0;
    ~*nikto 1;      # 취약점 스캐너
    ~*sqlmap 1;     # SQL Injection 도구
    ~*nmap 1;       # 포트 스캐너
    ~*masscan 1;    # 대량 스캐너
    ~*python-requests 1;  # 악의적 스크립트
    ~*scrapy 1;     # 무단 크롤러
}

if ($bad_bot) {
    return 403;
}
```

---

### 3. IP 기반 접근 제어

**파일**: `nginx/ip-whitelist.conf`

#### 관리자 페이지 보호

```nginx
location /admin {
    # 사무실 IP만 허용
    allow 211.xxx.xxx.xxx;
    
    # 집 IP 허용
    allow 121.xxx.xxx.xxx;
    
    # Localhost 허용
    allow 127.0.0.1;
    
    # 나머지 차단
    deny all;
    
    proxy_pass http://api:8000;
}
```

#### 동적 블랙리스트 (Fail2Ban 연동)

```nginx
# Fail2Ban이 자동 생성한 차단 목록 include
include /etc/nginx/conf.d/blocklist.conf;

# blocklist.conf 내용 예시:
# deny 1.2.3.4;
# deny 5.6.7.8;
```

---

### 4. FastAPI SlowAPI (애플리케이션 레벨)

**파일**: `app/main.py` (이미 구현됨)

```python
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

@app.get("/health")
@limiter.limit("60/minute")  # 분당 60회
async def health_check(request: Request):
    return {"status": "ok"}
```

**현재 적용 현황** (검증 완료):
- ✅ Health Check: 60/minute
- ✅ 기타 엔드포인트: Nginx 레벨에서 처리

---

## Nginx 설정 파일 적용

### 1. Nginx Proxy Manager 설정

**위치**: Docker 컨테이너 내부 또는 Nginx Proxy Manager UI

#### 옵션 A: UI에서 설정 (권장)

1. Nginx Proxy Manager 접속: `http://localhost:81`
2. Proxy Host 선택 → Edit
3. **Advanced** 탭 클릭
4. 다음 내용 추가:

```nginx
# Rate Limiting Zones (http 블록에 추가 - 전역 설정)
# 주의: Nginx Proxy Manager는 http 블록 수정 불가
# 대신 location 블록에서 직접 사용

# API Rate Limiting
location /api/ {
    # IP당 초당 10회, burst 20회
    limit_req_zone $binary_remote_addr zone=api_limit:10m rate=10r/s;
    limit_req zone=api_limit burst=20 nodelay;
    limit_req_status 429;
    
    # 연결 수 제한
    limit_conn_zone $binary_remote_addr zone=conn_limit:10m;
    limit_conn conn_limit 10;
    
    # 타임아웃 설정
    client_body_timeout 10s;
    client_header_timeout 10s;
    send_timeout 10s;
    
    # 요청 크기 제한
    client_max_body_size 10M;
    
    # 악성 봇 차단
    if ($http_user_agent ~* (nikto|sqlmap|nmap|masscan|scrapy)) {
        return 403;
    }
    
    # 빈 User-Agent 차단
    if ($http_user_agent = "") {
        return 403;
    }
    
    proxy_pass http://api:8000;
}

# 정적 파일 (완화된 제한)
location ~* \.(css|js|jpg|png|gif|ico|woff|woff2)$ {
    limit_req_zone $binary_remote_addr zone=static_limit:10m rate=50r/s;
    limit_req zone=static_limit burst=100;
    expires 1y;
    add_header Cache-Control "public, immutable";
}

# 로그인 엔드포인트 (엄격한 제한)
location /api/v1/auth/login {
    limit_req_zone $binary_remote_addr zone=login_limit:10m rate=5r/m;
    limit_req zone=login_limit burst=2 nodelay;
    limit_req_status 429;
    proxy_pass http://api:8000;
}
```

#### 옵션 B: 설정 파일 직접 수정 (고급)

**주의**: Docker 컨테이너 재시작 시 설정 초기화될 수 있음

```bash
# 컨테이너 접속
docker exec -it nginx-proxy-manager /bin/bash

# 설정 파일 편집
vi /etc/nginx/nginx.conf

# http 블록에 추가
http {
    include /data/nginx/custom/rate-limit.conf;
    include /data/nginx/custom/ddos-protection.conf;
    include /data/nginx/custom/ip-whitelist.conf;
    ...
}

# 설정 테스트
nginx -t

# 리로드
nginx -s reload
```

---

### 2. 커스텀 설정 파일 복사

```bash
# 호스트에서 컨테이너로 복사
docker cp nginx/rate-limit.conf nginx-proxy-manager:/data/nginx/custom/
docker cp nginx/ddos-protection.conf nginx-proxy-manager:/data/nginx/custom/
docker cp nginx/ip-whitelist.conf nginx-proxy-manager:/data/nginx/custom/

# Nginx 리로드
docker exec nginx-proxy-manager nginx -s reload
```

---

## Fail2Ban 자동 차단

### 설치 (라즈베리파이)

```bash
sudo apt-get update
sudo apt-get install -y fail2ban
```

### 설정

**파일**: `/etc/fail2ban/jail.local`

```ini
[DEFAULT]
# 차단 시간 (1시간)
bantime = 3600

# 탐지 시간 (10분)
findtime = 600

# 최대 재시도 횟수
maxretry = 5

# Slack 알림 (선택사항)
# action = %(action_)s
#          slack-notify

[nginx-limit-req]
enabled = true
filter = nginx-limit-req
action = nginx-blocklist
logpath = /var/log/nginx/error.log
findtime = 600
maxretry = 5
bantime = 3600

[nginx-http-auth]
enabled = true
filter = nginx-http-auth
logpath = /var/log/nginx/error.log
maxretry = 3
bantime = 7200
```

### 필터 설정

**파일**: `/etc/fail2ban/filter.d/nginx-limit-req.conf`

```ini
[Definition]
failregex = limiting requests, excess: .* by zone ".*", client: <HOST>
ignoreregex =
```

### 액션 설정 (Nginx 블랙리스트)

**파일**: `/etc/fail2ban/action.d/nginx-blocklist.conf`

```ini
[Definition]
actionstart = 
actionstop = 
actioncheck = 

actionban = echo "deny <ip>;" >> /etc/nginx/conf.d/blocklist.conf
            docker exec nginx-proxy-manager nginx -s reload

actionunban = sed -i '/deny <ip>;/d' /etc/nginx/conf.d/blocklist.conf
              docker exec nginx-proxy-manager nginx -s reload
```

### 시작 및 확인

```bash
# Fail2Ban 시작
sudo systemctl start fail2ban
sudo systemctl enable fail2ban

# 상태 확인
sudo fail2ban-client status

# 특정 jail 상태
sudo fail2ban-client status nginx-limit-req

# 차단된 IP 확인
sudo fail2ban-client get nginx-limit-req banned

# IP 수동 차단
sudo fail2ban-client set nginx-limit-req banip 1.2.3.4

# IP 해제
sudo fail2ban-client set nginx-limit-req unbanip 1.2.3.4
```

---

## 모니터링 및 검증

### 1. Rate Limiting 테스트

```bash
# API 엔드포인트 부하 테스트 (초당 15회 요청)
for i in {1..15}; do 
    curl -s https://leeeunseok.tail32c3e2.ts.net/api/v1/bids/ & 
done

# 예상 결과:
# - 10개: HTTP 200 (성공)
# - 5개: HTTP 429 Too Many Requests (차단)

# 로그인 브루트포스 테스트 (1분에 10회 시도)
for i in {1..10}; do 
    curl -X POST https://leeeunseok.tail32c3e2.ts.net/api/v1/auth/login \
      -d '{"email":"test@example.com","password":"wrong"}' & 
done

# 예상 결과:
# - 처음 5개: HTTP 401 Unauthorized (잘못된 비밀번호)
# - 나머지 5개: HTTP 429 Too Many Requests (Rate Limit)
```

### 2. Nginx 로그 모니터링

```bash
# Rate Limit 에러 확인
docker logs nginx-proxy-manager 2>&1 | grep "limiting requests"

# 예상 출력:
# [error] limiting requests, excess: 5.123 by zone "api_limit", client: 1.2.3.4

# 차단된 IP Top 10
docker logs nginx-proxy-manager | grep "403" | awk '{print $1}' | sort | uniq -c | sort -rn | head -10
```

### 3. Prometheus Alert 확인

**Alert 규칙**: `monitoring/alert_rules.yml`에 추가

```yaml
- alert: HighRateLimitErrors
  expr: rate(http_requests_total{status_code="429"}[5m]) > 10
  for: 5m
  labels:
    severity: warning
  annotations:
    summary: "높은 Rate Limit 에러율"
    description: "최근 5분간 분당 10회 이상 429 에러 발생 (공격 가능성)"
```

### 4. Grafana 대시보드

**패널 추가**:
- HTTP 429 응답 수 (시간별)
- Rate Limit 차단 IP Top 10
- 악성 User-Agent 차단 횟수

---

## 문제 해결

### Q1: 정상 사용자가 차단되는 경우

**원인**: Rate Limit 너무 낮음

**해결**:
```nginx
# rate-limit.conf 수정
limit_req_zone $binary_remote_addr zone=api_limit:10m rate=20r/s;  # 10→20 증가
```

### Q2: Fail2Ban이 작동하지 않음

**확인 사항**:
```bash
# 로그 경로 확인
sudo fail2ban-client get nginx-limit-req logpath

# 필터 테스트
sudo fail2ban-regex /var/log/nginx/error.log /etc/fail2ban/filter.d/nginx-limit-req.conf

# 로그 권한 확인
ls -l /var/log/nginx/error.log
```

### Q3: 설정 적용 후 Nginx 시작 실패

**원인**: 문법 오류

**해결**:
```bash
# 설정 검증
docker exec nginx-proxy-manager nginx -t

# 에러 로그 확인
docker logs nginx-proxy-manager
```

---

## 추가 보안 권장 사항

### 1. Cloudflare (선택사항)
- 무료 DDoS 방어 (Layer 3/4)
- WAF (Web Application Firewall)
- CDN 가속

### 2. ModSecurity (고급)
- Nginx WAF 모듈
- OWASP Core Rule Set 적용
- 리소스 많이 사용 (라즈베리파이에서 주의)

### 3. 정기 보안 업데이트
```bash
# 매주 실행
sudo apt-get update
sudo apt-get upgrade -y
docker-compose -f docker-compose.pi.yml pull
docker-compose -f docker-compose.pi.yml up -d
```

---

**작성자**: AI Agent  
**최종 업데이트**: 2026-01-30  
**관련 문서**: `nginx/rate-limit.conf`, `nginx/ddos-protection.conf`, `nginx/ip-whitelist.conf`
