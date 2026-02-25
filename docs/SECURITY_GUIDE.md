# Biz-Retriever 보안 가이드

프로덕션 환경(Railway Docker)에서의 보안 체크리스트입니다.

## 0. OWASP Top 10 감사 현황 (v2.0.0)

전체 OWASP Top 10 카테고리에 대한 전수 감사 완료. 상세 보고서: `docs/SECURITY_AUDIT_OWASP_2026.md`

| 심각도 | 발견 | 수정 | 미수정(권고) |
|--------|------|------|-------------|
| Critical | 2 | 2 | 0 |
| High | 4 | 4 | 0 |
| Medium | 4 | 4 | 0 |
| Low | 2 | 0 | 2 |
| **Total** | **12** | **10** | **2** |

### 보안 헤더 미들웨어 (`SecurityHeadersMiddleware`)

모든 HTTP 응답에 자동 적용:

| 헤더 | 값 | 목적 |
|------|-----|------|
| `X-Content-Type-Options` | `nosniff` | MIME 스니핑 방지 |
| `X-Frame-Options` | `DENY` | 클릭재킹 방지 |
| `X-XSS-Protection` | `1; mode=block` | XSS 필터 |
| `Referrer-Policy` | `strict-origin-when-cross-origin` | 리퍼러 정보 제한 |
| `Permissions-Policy` | `camera=(), microphone=()` | 브라우저 API 제한 |
| `Strict-Transport-Security` | `max-age=31536000; includeSubDomains` | HTTPS 강제 (Production) |

### Fail-closed 패턴

Redis 장애 시 토큰 블랙리스트 검증이 **거부(fail-closed)** 로 동작합니다.
- 장애 시: 모든 토큰 요청 거부 (사용자는 재로그인으로 복구)
- 이유: 탈취된 토큰으로의 무단 접근 차단이 가용성보다 우선

## 1. 계정 및 접속 보안 (SSH)

*   **[필수] 비밀번호 접속 금지 및 키 기반 인증 사용**:
    *   비밀번호는 무차별 대입 공격(Brute-force)에 취약합니다. SSH Key (`id_rsa.pub`)를 등록하고 비밀번호 인증을 비활성화하세요.
*   **[필수] ROOT 로그인 금지**:
    *   `/etc/ssh/sshd_config`에서 `PermitRootLogin no` 설정을 확인하세요.
*   **SSH 포트 변경**:
    *   기본 포트(22)를 2000~60000 사이의 임의의 포트로 변경하면 자동화된 스캔 공격의 90% 이상을 차단할 수 있습니다.
*   **Fail2Ban 설치**:
    *   여러 번 로그인에 실패한 IP를 자동으로 차단하는 도구입니다.

## 2. 네트워크 보안

*   **Tailscale Funnel 모니터링**:
    *   Funnel은 공용 인터넷에 포트를 개방합니다. 필요한 포트(현재 3001) 외에는 절대 열지 마세요.
*   **UFW(방화벽) 활성화**:
    *   기본적으로 모든 입력 포트를 닫고, 필요한 포트(Tailscale, SSH용 포트)만 명시적으로 허용하세요.
    ```bash
    sudo ufw default deny incoming
    sudo ufw allow 22/tcp # SSH 포트를 변경했다면 해당 포트
    sudo ufw allow in on tailscale0 # Tailscale 내부 통신 허용
    sudo ufw enable
    ```
*   **CORS 정책 강화**:
    *   `app/main.py`의 `CORSMiddleware` 설정에서 `allow_origins`를 공용 URL(`ts.net`)로만 한정하세요.

## 3. 데이터 및 애플리케이션 보안

*   **환경 변수 관리 (`.env`)**:
    *   API 키, DB 비밀번호가 포함된 `.env` 파일은 절대 Git에 포함되어서는 안 됩니다.
*   **Postgres 비밀번호 강화**:
    *   운영 환경에서는 초기 비밀번호 대신 복잡한 무작위 문자열을 사용하세요.
*   **Docker 컨테이너 권한**:
    *   비루트 사용자(`appuser`, UID 1000)로 실행 (Dockerfile에 적용 완료)
    *   tini를 PID 1로 사용하여 시그널 올바르게 전달
*   **CI/CD 보안 스캔**:
    *   bandit: Python 코드 보안 취약점 스캔
    *   pip-audit: 의존성 취약점 스캔
    *   Trivy: Docker 이미지 취약점 스캔 (CRITICAL, HIGH)

## 4. 시스템 운영 및 유지보수

*   **정기적인 업데이트**:
    *   `sudo apt update && sudo apt upgrade`를 정기적으로 실행하거나, `unattended-upgrades` 패키지를 사용하여 보안 업데이트를 자동화하세요.
*   **로그 모니터링**:
    *   `last` 명령어로 최근 접속 기록을 확인하고, `logs/errors.log`에 비정상적인 접근 시도가 있는지 확인하세요.
*   **백업 (Backup)**:
    *   라즈베리파이의 MicroSD 카드는 수명이 짧습니다. 중요한 데이터(Postgres data)는 주기적으로 외부 클라우드나 다른 저장소로 백업하세요.

## 5. 하드웨어 관리

*   **발열 관리**:
    *   서버로 24시간 가동 시 온도가 80도를 넘지 않도록 쿨링 팬이나 방열판을 장착하세요.
*   **MicroSD 카드 수명**:
    *   잦은 로그 쓰기는 SD 카드를 손상시킵니다. 쓰기 작업이 많은 경우 SSD 연결(USB 3.0)을 권장합니다.

## 6. 인증 및 토큰 보안

*   **Access Token**: 15분 만료 (99.87% 감소: 기존 8일 → 15분)
*   **Refresh Token**: 30일 만료, 갱신 시 rotation (이전 토큰 블랙리스트)
*   **토큰 블랙리스트**: Redis 기반, TTL 자동 만료
*   **계정 잠금**: 5회 로그인 실패 → 30분 잠금
*   **비밀번호 정책**: 8자 이상, 대/소문자, 숫자, 특수문자 필수

## 7. 에러 계층 보안

*   구조화된 에러 계층 29개 (`app/core/exceptions.py`)
*   Production 환경에서 Catch-all 핸들러가 에러 상세 숨김
*   도메인별 에러 코드 (`AUTH_*`, `BID_*`, `CRAWLER_*`, `PAYMENT_*`)

---
*Last Updated: 2026-02-25*
