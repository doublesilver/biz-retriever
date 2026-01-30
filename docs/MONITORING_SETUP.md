# Biz-Retriever 모니터링 스택 설정 가이드

## 개요

Prometheus + Grafana + Alertmanager를 사용한 실시간 모니터링 시스템입니다.
라즈베리파이 4GB RAM 환경에 최적화되어 있습니다.

## 아키텍처

```
┌─────────────────────────────────────────────────────────────┐
│                    Biz-Retriever API                        │
│                   (FastAPI + /metrics)                      │
└────────────────────┬────────────────────────────────────────┘
                     │
                     ├─────────────────────────────────────────┐
                     │                                         │
         ┌───────────▼──────────┐                 ┌───────────▼──────────┐
         │    Prometheus        │                 │   Exporters          │
         │  (메트릭 수집/저장)   │◄────────────────│  - postgres_exporter │
         │   Port: 9090         │                 │  - redis_exporter    │
         └───────────┬──────────┘                 └──────────────────────┘
                     │
         ┌───────────▼──────────┐
         │   Alertmanager       │
         │   (알림 관리)         │
         │   Port: 9093         │
         └───────────┬──────────┘
                     │
                     ├─────────────────────────────────────────┐
                     │                                         │
         ┌───────────▼──────────┐                 ┌───────────▼──────────┐
         │     Grafana          │                 │      Slack           │
         │   (대시보드)          │                 │   (알림 수신)         │
         │   Port: 3000         │                 │                      │
         └──────────────────────┘                 └──────────────────────┘
```

## 서비스 구성

### 1. Prometheus (포트: 9090)
- **역할**: 메트릭 수집 및 시계열 데이터 저장
- **메모리**: 512MB (예약: 256MB)
- **CPU**: 0.5 코어
- **데이터 보관**: 30일 또는 5GB
- **수집 간격**: 15초

### 2. Grafana (포트: 3000)
- **역할**: 시각화 대시보드
- **메모리**: 256MB (예약: 128MB)
- **CPU**: 0.5 코어
- **기본 계정**: admin / admin (변경 필요)

### 3. Alertmanager (포트: 9093)
- **역할**: 알림 라우팅 및 관리
- **메모리**: 128MB
- **CPU**: 0.25 코어
- **Slack 연동**: 환경변수 `SLACK_WEBHOOK_URL` 필요

### 4. Exporters
- **postgres_exporter** (포트: 9187): PostgreSQL 메트릭
- **redis_exporter** (포트: 9121): Redis 메트릭

## 접속 방법

### Prometheus
```bash
# 로컬 접속
http://localhost:9090

# Tailscale 접속
http://<라즈베리파이-IP>:9090
```

**주요 기능**:
- Targets: 수집 대상 상태 확인 (`/targets`)
- Graph: PromQL 쿼리 실행 (`/graph`)
- Alerts: 활성 알림 확인 (`/alerts`)

### Grafana
```bash
# 로컬 접속
http://localhost:3000

# Tailscale 접속
http://<라즈베리파이-IP>:3000
```

**기본 로그인**:
- Username: `admin`
- Password: `admin` (첫 로그인 시 변경 요구)

**보안 설정**:
```bash
# .env 파일에 추가
GRAFANA_ADMIN_PASSWORD=your_secure_password
```

### Alertmanager
```bash
# 로컬 접속
http://localhost:9093

# 알림 상태 확인
curl http://localhost:9093/api/v2/alerts
```

## 기본 대시보드 사용법

### 1. 대시보드 접속
Grafana 로그인 후 자동으로 "Biz-Retriever Dashboard"가 프로비저닝됩니다.

**경로**: Home > Dashboards > Biz-Retriever Dashboard

### 2. 주요 패널

#### 상단 통계 (Stats)
- **HTTP Requests (24h)**: 일일 총 요청 수
- **API Latency (P95)**: 95 백분위 응답 시간
- **Announcements Collected (24h)**: 일일 수집 공고 수
- **Success Rate**: API 성공률

#### 중간 그래프 (Time Series)
- **Request Rate by Endpoint**: 엔드포인트별 요청률
- **Response Time by Endpoint**: 엔드포인트별 응답 시간 (P50, P95)
- **Crawler Runs (1h)**: 크롤러 실행 현황
- **Announcements by Source (1h)**: 소스별 공고 수집 현황

#### 하단 메트릭 (Gauges & Stats)
- **Cache Hit Rate**: 캐시 히트율 (게이지)
- **Notifications Sent (24h)**: 일일 알림 발송 수
- **Celery Tasks (24h)**: 일일 Celery 작업 완료 수

### 3. 시간 범위 변경
우측 상단 시간 선택기에서 조정:
- Last 6 hours (기본)
- Last 24 hours
- Last 7 days
- Custom range

### 4. 자동 새로고침
우측 상단에서 설정 (기본: 30초)

## Alert 설정 가이드

### 1. 기본 Alert 규칙

#### Critical Alerts (즉시 알림)
- **APIServiceDown**: API 서비스 다운 (1분 이상)
- **PostgreSQLDown**: DB 다운 (1분 이상)
- **RedisDown**: Redis 다운 (1분 이상)
- **HighAPIErrorRate**: API 에러율 > 5% (5분 지속)
- **HighDiskUsage**: 디스크 사용량 > 80% (5분 지속)

#### Warning Alerts (10분 대기 후 알림)
- **HighAPILatency**: P95 응답 시간 > 5초
- **SlowDatabaseQueries**: P95 쿼리 시간 > 1초
- **HighRedisMemory**: Redis 메모리 > 180MB
- **LowCacheHitRate**: 캐시 히트율 < 70%
- **HighCeleryTaskFailureRate**: Celery 실패율 > 10%

### 2. Slack 채널 설정

#### 필수 환경변수
```bash
# .env 파일에 추가
SLACK_WEBHOOK_URL=https://hooks.slack.com/services/YOUR/WEBHOOK/URL
```

#### Slack Webhook 생성
1. Slack 워크스페이스 > Apps > Incoming Webhooks
2. "Add to Slack" 클릭
3. 채널 선택 (예: `#biz-retriever-alerts`)
4. Webhook URL 복사

#### 알림 채널 구성
- `#biz-retriever-alerts`: Critical/Warning 알림
- `#biz-retriever-crawler`: 크롤러 관련 알림

### 3. Alert 테스트

#### 수동 Alert 발생
```bash
# API 서비스 중지 (APIServiceDown 발생)
docker stop biz-retriever-api

# 1분 후 Slack 알림 확인
# 서비스 재시작
docker start biz-retriever-api
```

#### Alert 상태 확인
```bash
# Prometheus Alerts 페이지
http://localhost:9090/alerts

# Alertmanager API
curl http://localhost:9093/api/v2/alerts | jq .
```

### 4. Alert 규칙 커스터마이징

파일: `monitoring/alert_rules.yml`

```yaml
# 예시: API 에러율 임계값 변경 (5% → 10%)
- alert: HighAPIErrorRate
  expr: |
    (sum(rate(http_requests_total{status_code!="200"}[5m])) / sum(rate(http_requests_total[5m]))) > 0.10
  for: 5m
  labels:
    severity: critical
  annotations:
    summary: "API 에러율이 10%를 초과했습니다"
```

변경 후 Prometheus 재로드:
```bash
curl -X POST http://localhost:9090/-/reload
```

## 메트릭 수집 확인

### 1. Prometheus Targets 확인
```bash
curl http://localhost:9090/api/v1/targets | jq '.data.activeTargets[] | {job: .labels.job, health: .health}'
```

**예상 출력**:
```json
{"job": "biz-retriever-api", "health": "up"}
{"job": "postgres", "health": "up"}
{"job": "redis", "health": "up"}
{"job": "prometheus", "health": "up"}
```

### 2. API 메트릭 확인
```bash
# /metrics 엔드포인트 직접 확인
curl http://localhost:8000/metrics | grep http_requests_total

# 예상 출력:
# http_requests_total{method="GET",endpoint="/api/v1/bids",status_code="200"} 1234
```

### 3. Grafana 데이터소스 확인
```bash
curl -s http://localhost:3000/api/health | jq .
```

**예상 출력**:
```json
{
  "database": "ok",
  "version": "10.2.2"
}
```

## 문제 해결 (Troubleshooting)

### 1. Prometheus가 메트릭을 수집하지 못함

**증상**: Targets 페이지에서 "down" 상태

**해결**:
```bash
# 1. API 서비스 상태 확인
docker logs biz-retriever-api | tail -20

# 2. 네트워크 연결 확인
docker exec biz-retriever-prometheus wget -O- http://api:8000/metrics

# 3. Prometheus 설정 확인
docker exec biz-retriever-prometheus cat /etc/prometheus/prometheus.yml
```

### 2. Grafana 대시보드가 비어있음

**증상**: 패널에 "No data" 표시

**해결**:
```bash
# 1. Prometheus 데이터소스 확인
curl http://localhost:3000/api/datasources | jq .

# 2. Prometheus 쿼리 테스트
curl 'http://localhost:9090/api/v1/query?query=up'

# 3. Grafana 로그 확인
docker logs biz-retriever-grafana | tail -20
```

### 3. Slack 알림이 오지 않음

**증상**: Alert는 발생하지만 Slack 메시지 없음

**해결**:
```bash
# 1. Alertmanager 로그 확인
docker logs biz-retriever-alertmanager | grep -i slack

# 2. Webhook URL 확인
docker exec biz-retriever-alertmanager env | grep SLACK

# 3. 수동 테스트
curl -X POST $SLACK_WEBHOOK_URL \
  -H 'Content-Type: application/json' \
  -d '{"text":"Test from Alertmanager"}'
```

### 4. 메모리 부족

**증상**: 컨테이너 재시작 반복

**해결**:
```bash
# 1. 메모리 사용량 확인
docker stats --no-stream

# 2. Prometheus 데이터 정리
docker exec biz-retriever-prometheus rm -rf /prometheus/*

# 3. 리소스 제한 조정 (docker-compose.pi.yml)
# Prometheus memory: 512M → 384M
# Grafana memory: 256M → 192M
```

## 성능 최적화

### 1. Prometheus 쿼리 최적화

**느린 쿼리 식별**:
```bash
# Prometheus 로그에서 느린 쿼리 확인
docker logs biz-retriever-prometheus | grep "slow query"
```

**권장 사항**:
- 시간 범위를 최소화 (`[5m]` 대신 `[1m]`)
- 불필요한 레이블 제거
- Recording Rules 사용 (자주 사용하는 쿼리)

### 2. 메트릭 수집 간격 조정

**파일**: `monitoring/prometheus.yml`

```yaml
# 기본: 15초
scrape_interval: 15s

# 리소스 절약: 30초
scrape_interval: 30s
```

### 3. 데이터 보관 기간 조정

**파일**: `docker-compose.pi.yml`

```yaml
# 기본: 30일
- '--storage.tsdb.retention.time=30d'

# 단축: 15일
- '--storage.tsdb.retention.time=15d'
```

## 백업 및 복구

### 1. Prometheus 데이터 백업
```bash
# 스냅샷 생성
curl -X POST http://localhost:9090/api/v1/admin/tsdb/snapshot

# 백업 디렉토리
./data/prometheus/snapshots/
```

### 2. Grafana 대시보드 백업
```bash
# 대시보드 JSON 내보내기
curl -H "Authorization: Bearer <API_KEY>" \
  http://localhost:3000/api/dashboards/uid/biz-retriever-main \
  > dashboard-backup.json
```

### 3. 설정 파일 백업
```bash
# 모니터링 설정 전체 백업
tar -czf monitoring-backup-$(date +%Y%m%d).tar.gz monitoring/
```

## 추가 리소스

### PromQL 쿼리 예시

```promql
# 1. 최근 5분간 평균 요청률
rate(http_requests_total[5m])

# 2. 엔드포인트별 에러율
sum(rate(http_requests_total{status_code!="200"}[5m])) by (endpoint) 
/ sum(rate(http_requests_total[5m])) by (endpoint)

# 3. 크롤러 성공률
sum(rate(crawler_runs_total{status="success"}[1h])) 
/ sum(rate(crawler_runs_total[1h]))

# 4. 메모리 사용량 (컨테이너별)
container_memory_usage_bytes{name=~"biz-retriever.*"}
```

### 유용한 링크
- [Prometheus 공식 문서](https://prometheus.io/docs/)
- [Grafana 대시보드 갤러리](https://grafana.com/grafana/dashboards/)
- [PromQL 치트시트](https://promlabs.com/promql-cheat-sheet/)
- [Alertmanager 설정 가이드](https://prometheus.io/docs/alerting/latest/configuration/)

## 라이선스 및 지원

- Prometheus: Apache 2.0
- Grafana: AGPL 3.0
- Alertmanager: Apache 2.0

문의: 프로젝트 이슈 트래커
