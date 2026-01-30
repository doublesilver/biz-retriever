# Monitoring Stack Deployment Summary

## ✅ 작업 완료 내역

### 1. 생성된 파일

#### 설정 파일 (monitoring/)
- ✅ `monitoring/prometheus.yml` - Prometheus 메트릭 수집 설정
- ✅ `monitoring/alert_rules.yml` - Alert 규칙 (11개 알림)
- ✅ `monitoring/alertmanager.yml` - Slack 연동 알림 관리
- ✅ `monitoring/grafana-datasource.yml` - Grafana 데이터소스 프로비저닝
- ✅ `monitoring/grafana-dashboard-provisioning.yml` - 대시보드 자동 로드
- ✅ `monitoring/grafana-dashboard.json` - 기존 대시보드 (재사용)

#### 문서
- ✅ `docs/MONITORING_SETUP.md` - 상세 설정 가이드 (한글)

#### Docker Compose
- ✅ `docker-compose.pi.yml` - 모니터링 서비스 5개 추가

### 2. 추가된 Docker 서비스

| 서비스 | 포트 | 메모리 | CPU | 역할 |
|--------|------|--------|-----|------|
| prometheus | 9090 | 512M | 0.5 | 메트릭 수집/저장 |
| grafana | 3000 | 256M | 0.5 | 대시보드 |
| alertmanager | 9093 | 128M | 0.25 | 알림 관리 |
| postgres_exporter | 9187 | 64M | 0.1 | DB 메트릭 |
| redis_exporter | 9121 | 32M | 0.1 | 캐시 메트릭 |

**총 리소스**: 992MB RAM, 1.45 CPU cores

### 3. 메트릭 수집 대상

- **biz-retriever-api** (api:8000/metrics) - 15초 간격
- **postgres_exporter** (9187) - 30초 간격
- **redis_exporter** (9121) - 30초 간격
- **prometheus** (9090) - 30초 간격 (자체 모니터링)

### 4. Alert 규칙 (11개)

#### Critical (즉시 알림)
1. APIServiceDown - API 다운 (1분)
2. PostgreSQLDown - DB 다운 (1분)
3. RedisDown - Redis 다운 (1분)
4. HighAPIErrorRate - 에러율 >5% (5분)
5. HighDiskUsage - 디스크 >80% (5분)

#### Warning (10분 대기)
6. HighAPILatency - P95 >5초
7. SlowDatabaseQueries - P95 >1초
8. HighRedisMemory - >180MB
9. LowCacheHitRate - <70%
10. HighCeleryTaskFailureRate - >10%
11. CrawlerNotRunning - 2시간 미실행

## 🚀 배포 방법

### 1. 환경변수 설정

`.env` 파일에 추가:
```bash
# Slack Webhook (필수)
SLACK_WEBHOOK_URL=https://hooks.slack.com/services/YOUR/WEBHOOK/URL

# Grafana 비밀번호 (선택, 기본값: admin)
GRAFANA_ADMIN_PASSWORD=your_secure_password
```

### 2. 디렉토리 생성

```bash
cd /path/to/sideproject

# 데이터 디렉토리 생성
mkdir -p data/prometheus data/grafana data/alertmanager

# 권한 설정 (Grafana는 UID 472 필요)
sudo chown -R 472:472 data/grafana
```

### 3. 서비스 시작

```bash
# 모니터링 스택만 시작
docker-compose -f docker-compose.pi.yml up -d prometheus grafana alertmanager postgres_exporter redis_exporter

# 또는 전체 스택 재시작
docker-compose -f docker-compose.pi.yml up -d
```

### 4. 접속 확인

```bash
# Prometheus
curl http://localhost:9090/-/healthy
# 예상: Prometheus is Healthy.

# Grafana
curl http://localhost:3000/api/health
# 예상: {"database":"ok"}

# Alertmanager
curl http://localhost:9093/-/healthy
# 예상: OK
```

## 📊 검증 명령어

### Prometheus 타겟 확인
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

### 메트릭 수집 확인
```bash
curl http://localhost:8000/metrics | grep http_requests_total
```

**예상 출력**:
```
http_requests_total{method="GET",endpoint="/api/v1/bids",status_code="200"} 1234
```

### Grafana 접속
```bash
# 브라우저에서 접속
http://localhost:3000

# 로그인
Username: admin
Password: admin (또는 GRAFANA_ADMIN_PASSWORD)
```

## 🔧 Grafana 초기 설정

### 1. 첫 로그인
- URL: `http://localhost:3000`
- Username: `admin`
- Password: `admin`
- 비밀번호 변경 요구 → 새 비밀번호 설정

### 2. 대시보드 확인
- 좌측 메뉴 > Dashboards
- "Biz-Retriever Dashboard" 자동 로드됨
- 데이터가 표시되지 않으면 시간 범위 조정 (우측 상단)

### 3. 데이터소스 확인
- 좌측 메뉴 > Connections > Data sources
- "Prometheus" 데이터소스 자동 설정됨
- "Test" 버튼 클릭 → "Data source is working" 확인

## 📱 Slack 연동 테스트

### 1. Webhook URL 설정 확인
```bash
docker exec biz-retriever-alertmanager env | grep SLACK_WEBHOOK_URL
```

### 2. 수동 Alert 발생
```bash
# API 서비스 중지 (APIServiceDown 발생)
docker stop biz-retriever-api

# 1분 대기 후 Slack 확인
# 예상: #biz-retriever-alerts 채널에 알림

# 서비스 재시작
docker start biz-retriever-api

# Resolved 알림 확인
```

### 3. Alert 상태 확인
```bash
# Prometheus Alerts
http://localhost:9090/alerts

# Alertmanager API
curl http://localhost:9093/api/v2/alerts | jq .
```

## 📈 리소스 사용량 모니터링

```bash
# 컨테이너별 리소스 사용량
docker stats --no-stream | grep biz-retriever

# 예상 출력:
# biz-retriever-prometheus    ~200MB / 512MB   ~10% CPU
# biz-retriever-grafana       ~150MB / 256MB   ~5% CPU
# biz-retriever-alertmanager  ~30MB / 128MB    ~2% CPU
```

## 🐛 문제 해결

### Prometheus가 메트릭을 수집하지 못함
```bash
# 1. API /metrics 엔드포인트 확인
curl http://localhost:8000/metrics

# 2. Prometheus 로그 확인
docker logs biz-retriever-prometheus | tail -50

# 3. 네트워크 연결 테스트
docker exec biz-retriever-prometheus wget -O- http://api:8000/metrics
```

### Grafana 대시보드가 비어있음
```bash
# 1. Prometheus 쿼리 테스트
curl 'http://localhost:9090/api/v1/query?query=up'

# 2. Grafana 로그 확인
docker logs biz-retriever-grafana | tail -50

# 3. 시간 범위 조정 (Grafana 우측 상단)
# Last 6 hours → Last 24 hours
```

### Slack 알림이 오지 않음
```bash
# 1. Alertmanager 로그 확인
docker logs biz-retriever-alertmanager | grep -i slack

# 2. Webhook 테스트
curl -X POST $SLACK_WEBHOOK_URL \
  -H 'Content-Type: application/json' \
  -d '{"text":"Test from Alertmanager"}'

# 3. Alert 규칙 확인
curl http://localhost:9090/api/v1/rules
```

## 📚 추가 문서

- **상세 가이드**: `docs/MONITORING_SETUP.md`
- **Prometheus 설정**: `monitoring/prometheus.yml`
- **Alert 규칙**: `monitoring/alert_rules.yml`
- **Alertmanager 설정**: `monitoring/alertmanager.yml`

## 🎯 다음 단계

1. ✅ Slack Webhook URL 설정
2. ✅ Grafana 비밀번호 변경
3. ✅ 대시보드 확인 및 커스터마이징
4. ✅ Alert 테스트
5. ✅ 리소스 사용량 모니터링

## 📞 지원

문제 발생 시:
1. `docs/MONITORING_SETUP.md` 문제 해결 섹션 참조
2. 로그 확인: `docker logs <container-name>`
3. 설정 검증: `docker-compose -f docker-compose.pi.yml config`

---

**작업 완료일**: 2026-01-30
**작성자**: Sisyphus-Junior (OhMyClaude Code)
