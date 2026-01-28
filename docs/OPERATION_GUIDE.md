# Biz-Retriever 운영 매뉴얼 (Raspberry Pi Environment)

## 1. 시스템 개요
Biz-Retriever는 나라장터(G2B) 입찰 공고를 수집하고, AI(Gemini)를 통해 분석하여 사용자에게 맞춤형 정보를 제공하는 서비스입니다.
본 가이드는 Raspberry Pi (Ubuntu/Debian 기반) 환경에서의 배포 및 운영 방법을 다룹니다.

## 2. 배포 관리 (Deployment)

### 2.1 소스 코드 업데이트
로컬 개발 환경에서 수정된 코드를 운영 서버(Raspberry Pi)로 배포할 때 사용합니다.

**전체 배포 (Backend + Frontend + Workers):**
```bash
# 로컬 개발 PC (Windows PowerShell)
python scripts/force_deploy.py
```
*주의: 이 스크립트는 컨테이너를 재시작하므로 약 10~20초의 다운타임이 발생할 수 있습니다.*

**프론트엔드 긴급 패치 (브라우저 캐시 문제 해결 포함):**
```bash
# 로컬 개발 PC
python scripts/rebuild_frontend.py
```
*이 스크립트는 프론트엔드 컨테이너만 이미지를 새로 빌드하여 교체합니다.*

### 2.2 서비스 재시작
서버 접속 후 컨테이너를 수동으로 제어해야 할 때 사용합니다.

```bash
# SSH 접속
ssh admin@100.75.72.6

# 프로젝트 폴더 이동
cd ~/projects/biz-retriever

# 전체 재시작
docker compose restart

# 특정 서비스만 재시작 (예: API 서버)
docker compose restart api
```

## 3. 모니터링 (Monitoring)

### 3.1 리소스 사용량 확인
서버의 CPU, 메모리, 디스크 사용량을 한눈에 확인하는 스크립트입니다.

```bash
# SSH 접속 후 실행
bash ~/projects/biz-retriever/scripts/monitor.sh
```

### 3.2 로그 확인
실시간 로그를 확인하여 문제 원인을 파악합니다.

**API 서버 로그:**
```bash
docker compose logs -f api
```

**크롤러/워커 로그:**
```bash
docker compose logs -f celery-worker
```

**에러 전용 로그 파일 (서버 내부):**
```bash
cat logs/errors.log
```

### 3.3 자동 알림 (Slack)
심각한 에러(ERROR 레벨 이상)가 발생하면 설정된 Slack 채널로 알림이 전송됩니다.
*설정 파일: `app/core/config.py`의 `SLACK_WEBHOOK_URL`*

## 4. 트러블슈팅 (Troubleshooting)

### Q1. 브라우저에서 업데이트된 화면이 안 보여요!
**원인**: 브라우저 캐시 또는 Nginx 캐시가 구버전 파일을 잡고 있기 때문입니다.
**해결**:
1. 브라우저에서 `Ctrl + Shift + R` (강력 새로고침)을 누릅니다.
2. 해결되지 않으면 `python scripts/rebuild_frontend.py`를 실행하여 컨테이너 이미지를 재생성합니다.

### Q2. 크롤러가 작동하지 않아요 (수집된 공고가 0건).
**원인**: G2B API 키 만료, 네트워크 오류, 또는 DB 락(Lock) 문제일 수 있습니다.
**해결**:
1. `docker compose logs -f celery-worker`로 에러 메시지를 확인합니다.
2. `Event loop is closed` 에러가 보이면 워커를 재시작합니다: `docker compose restart celery-worker`.
3. G2B API 키가 만료되었다면 `.env` 파일에서 키를 갱신하고 재시작합니다.

### Q3. "422 Unprocessable Entity" 에러가 떠요.
**원인**: API 요청 파라미터가 잘못되었거나 형식이 맞지 않을 때 발생합니다.
**해결**:
1. 프론트엔드 콘솔(F12)을 열어 정확한 에러 메시지(JSON)를 확인합니다.
2. 파일 업로드 시 발생한다면 파일 확장자가 허용된 것(`image/*, .pdf`)인지 확인합니다.

## 5. 주요 파일 경로

| 구분 | 호스트 경로 (`~/projects/biz-retriever`) | 설명 |
|---|---|---|
| 환경 변수 | `.env` | API 키, DB 접속 정보 등 민감 정보 |
| 로그 | `logs/` | 애플리케이션 로그 저장소 (Docker 볼륨) |
| 설정 | `docker-compose.pi.yml` | 운영 배포용 Docker 설정 파일 |
| DB 스키마 | `app/db/models.py` | 데이터베이스 구조 정의 |

---
*Last Updated: 2026-01-28*
