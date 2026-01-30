# 데이터베이스 백업 자동화 설정 가이드

## 📋 목차
1. [개요](#개요)
2. [백업 스크립트](#백업-스크립트)
3. [검증 스크립트](#검증-스크립트)
4. [복원 테스트](#복원-테스트)
5. [Cron 작업 설정](#cron-작업-설정)
6. [복원 절차](#복원-절차)
7. [트러블슈팅](#트러블슈팅)

---

## 개요

이 가이드는 PostgreSQL 데이터베이스의 자동 백업, 검증, 복원 테스트를 설정하는 방법을 설명합니다.

### 주요 기능
- ✅ **자동 백업**: 매일 정해진 시간에 자동으로 백업 실행
- ✅ **백업 검증**: gzip 무결성, 파일 크기, PostgreSQL 헤더 검증
- ✅ **복원 테스트**: 테스트 DB에서 복원 가능 여부 확인
- ✅ **자동 정리**: 14일 이상 된 백업 파일 자동 삭제
- ✅ **Slack 알림**: 백업 성공/실패 시 Slack으로 알림

### 파일 구조
```
scripts/
├── backup-db.sh          # 메인 백업 스크립트
├── verify-backup.sh      # 백업 검증 스크립트
├── test-restore.sh       # 복원 테스트 스크립트
└── slack-notify.sh       # Slack 알림 함수

data/
└── backups/              # 백업 파일 저장 디렉토리
    ├── db_backup_20260130_030000.sql.gz
    ├── db_backup_20260129_030000.sql.gz
    └── ...
```

---

## 백업 스크립트

### 스크립트 위치
```bash
scripts/backup-db.sh
```

### 기능
1. PostgreSQL 데이터베이스 덤프 생성
2. gzip으로 압축
3. 백업 파일 검증
4. 14일 이상 된 백업 파일 자동 삭제
5. Slack 알림 전송

### 수동 실행
```bash
# 프로젝트 디렉토리에서 실행
bash scripts/backup-db.sh

# 또는 절대 경로로 실행
bash /path/to/sideproject/scripts/backup-db.sh
```

### 출력 예시
```
📦 데이터베이스 백업 중... (2026-01-30 03:00:00)
✅ 백업 완료: /path/to/sideproject/data/backups/db_backup_20260130_030000.sql
✅ 압축 완료: /path/to/sideproject/data/backups/db_backup_20260130_030000.sql.gz
🔍 백업 검증 중...
✅ 백업 검증 통과
🧹 오래된 백업 파일 정리 중...
✅ 백업 프로세스 완료
```

---

## 검증 스크립트

### 스크립트 위치
```bash
scripts/verify-backup.sh
```

### 기능
1. **gzip 무결성 검사**: `gzip -t` 명령으로 파일 무결성 확인
2. **파일 크기 검증**: 최소 1MB 이상 확인
3. **PostgreSQL 헤더 검증**: "PostgreSQL database dump" 문자열 확인
4. **테이블 수 검증**: CREATE TABLE 구문 개수 확인

### 사용법
```bash
# 특정 백업 파일 검증
bash scripts/verify-backup.sh data/backups/db_backup_20260130_030000.sql.gz

# 최신 백업 파일 검증
bash scripts/verify-backup.sh data/backups/$(ls -t data/backups/*.sql.gz | head -1 | xargs basename)
```

### 출력 예시
```
🔍 백업 파일 검증 시작: data/backups/db_backup_20260130_030000.sql.gz
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
1️⃣  파일 크기 검증 중...
   ✅ 파일 크기 검증 통과 (45MB)
2️⃣  gzip 무결성 검증 중...
   ✅ gzip 무결성 검증 통과
3️⃣  PostgreSQL 헤더 검증 중...
   ✅ PostgreSQL 헤더 검증 통과
4️⃣  테이블 검증 중...
   ✅ 테이블 검증 통과: 23 개 테이블 발견
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
✅ 백업 검증 완료!
   파일: data/backups/db_backup_20260130_030000.sql.gz
   크기: 45MB (47185920 bytes)
   테이블: 23
```

### 검증 실패 시
```bash
# 파일이 손상된 경우
❌ gzip 무결성 검증 실패

# 파일이 너무 작은 경우
❌ 파일 크기 검증 실패: 512000 bytes (최소: 1048576 bytes)

# PostgreSQL 헤더가 없는 경우
⚠️  PostgreSQL 헤더를 찾을 수 없습니다 (경고)
```

---

## 복원 테스트

### 스크립트 위치
```bash
scripts/test-restore.sh
```

### 기능
1. 최신 백업 파일 자동 검색
2. 테스트 PostgreSQL 컨테이너 생성 (`biz-retriever-test-db`)
3. 백업 파일을 테스트 DB에 복원
4. 테이블 수 및 레코드 수 검증
5. 테스트 컨테이너 자동 삭제

### 사용법
```bash
# 복원 테스트 실행
bash scripts/test-restore.sh
```

### 출력 예시
```
🔄 복원 테스트 시작...
📦 최신 백업 파일: /path/to/sideproject/data/backups/db_backup_20260130_030000.sql.gz
🧹 기존 테스트 컨테이너 정리...
🚀 테스트 PostgreSQL 컨테이너 생성...
⏳ 컨테이너 준비 대기 중...
✅ 컨테이너 준비 완료
📥 백업 파일 복원 중...
✅ 복원 완료
🔍 복원된 데이터 검증...
✅ 테이블 수: 23
✅ 레코드 수: 9572
📋 주요 테이블 확인...
   테이블: companies, products, services, users, ...
🧹 테스트 컨테이너 정리...

✅ 복원 테스트 완료!
   백업 파일: /path/to/sideproject/data/backups/db_backup_20260130_030000.sql.gz
   테이블 수: 23
   레코드 수: 9572
```

### 복원 테스트 실패 시
```bash
# 백업 파일을 찾을 수 없는 경우
❌ 백업 파일을 찾을 수 없습니다

# 컨테이너 생성 실패
❌ 컨테이너 준비 시간 초과

# 복원 실패
❌ 복원 실패

# 테이블을 찾을 수 없는 경우
❌ 테이블을 찾을 수 없습니다
```

---

## Cron 작업 설정

### 매일 오전 3시에 백업 실행

#### 1. Crontab 편집
```bash
crontab -e
```

#### 2. 다음 라인 추가
```bash
# 매일 오전 3시에 백업 실행
0 3 * * * /path/to/sideproject/scripts/backup-db.sh >> /path/to/sideproject/logs/backup.log 2>&1

# 매일 오전 3:30에 검증 실행 (선택사항)
30 3 * * * bash /path/to/sideproject/scripts/verify-backup.sh /path/to/sideproject/data/backups/$(ls -t /path/to/sideproject/data/backups/*.sql.gz 2>/dev/null | head -1 | xargs basename) >> /path/to/sideproject/logs/verify.log 2>&1

# 매주 월요일 오전 4시에 복원 테스트 실행 (선택사항)
0 4 * * 1 /path/to/sideproject/scripts/test-restore.sh >> /path/to/sideproject/logs/restore-test.log 2>&1
```

### Cron 시간 형식
```
┌───────────── 분 (0 - 59)
│ ┌───────────── 시 (0 - 23)
│ │ ┌───────────── 일 (1 - 31)
│ │ │ ┌───────────── 월 (1 - 12)
│ │ │ │ ┌───────────── 요일 (0 - 6) (0 = 일요일)
│ │ │ │ │
│ │ │ │ │
* * * * * 실행할 명령어
```

### 예시
```bash
# 매일 오전 3시
0 3 * * *

# 매주 월요일 오전 4시
0 4 * * 1

# 매월 1일 오전 2시
0 2 1 * *

# 매 시간 정각
0 * * * *

# 매 15분마다
*/15 * * * *
```

### Crontab 확인
```bash
# 현재 crontab 목록 확인
crontab -l

# 특정 사용자의 crontab 확인 (root 권한 필요)
sudo crontab -l -u username
```

### Crontab 로그 확인
```bash
# 백업 로그 확인
tail -f /path/to/sideproject/logs/backup.log

# 시스템 cron 로그 확인 (Linux)
sudo tail -f /var/log/syslog | grep CRON

# 시스템 cron 로그 확인 (macOS)
log stream --predicate 'process == "cron"' --level debug
```

---

## 복원 절차

### 시나리오 1: 최신 백업에서 복원

#### 1단계: 백업 파일 확인
```bash
# 최신 백업 파일 확인
ls -lh data/backups/*.sql.gz | tail -5
```

#### 2단계: 기존 데이터베이스 백업 (선택사항)
```bash
# 현재 데이터베이스 백업
bash scripts/backup-db.sh
```

#### 3단계: 데이터베이스 삭제 및 재생성
```bash
# Docker Compose를 통해 PostgreSQL 컨테이너 접속
docker-compose -f docker-compose.pi.yml exec postgres psql -U admin -d postgres

# 데이터베이스 삭제
DROP DATABASE biz_retriever;

# 데이터베이스 생성
CREATE DATABASE biz_retriever;

# 종료
\q
```

#### 4단계: 백업 파일 복원
```bash
# 최신 백업 파일 복원
LATEST_BACKUP=$(ls -t data/backups/*.sql.gz | head -1)
gunzip -c "$LATEST_BACKUP" | docker-compose -f docker-compose.pi.yml exec -T postgres psql -U admin -d biz_retriever
```

#### 5단계: 복원 확인
```bash
# 테이블 수 확인
docker-compose -f docker-compose.pi.yml exec postgres psql -U admin -d biz_retriever -c \
  "SELECT COUNT(*) FROM information_schema.tables WHERE table_schema='public';"

# 레코드 수 확인
docker-compose -f docker-compose.pi.yml exec postgres psql -U admin -d biz_retriever -c \
  "SELECT SUM(n_live_tup) FROM pg_stat_user_tables;"
```

### 시나리오 2: 특정 시점의 백업에서 복원

#### 1단계: 백업 파일 목록 확인
```bash
# 백업 파일 목록 (최신순)
ls -lh data/backups/*.sql.gz | tail -20
```

#### 2단계: 특정 백업 파일 선택
```bash
# 예: 2026-01-28의 백업 파일 복원
BACKUP_FILE="data/backups/db_backup_20260128_030000.sql.gz"
```

#### 3단계: 데이터베이스 삭제 및 재생성
```bash
docker-compose -f docker-compose.pi.yml exec postgres psql -U admin -d postgres -c \
  "DROP DATABASE IF EXISTS biz_retriever; CREATE DATABASE biz_retriever;"
```

#### 4단계: 백업 파일 복원
```bash
gunzip -c "$BACKUP_FILE" | docker-compose -f docker-compose.pi.yml exec -T postgres psql -U admin -d biz_retriever
```

### 시나리오 3: 테스트 DB에서 복원 테스트

```bash
# 복원 테스트 실행 (프로덕션 DB에 영향 없음)
bash scripts/test-restore.sh
```

---

## 트러블슈팅

### 문제 1: 백업 스크립트 실행 권한 없음

**증상**
```
bash: scripts/backup-db.sh: Permission denied
```

**해결 방법**
```bash
# 실행 권한 부여
chmod +x scripts/backup-db.sh
chmod +x scripts/verify-backup.sh
chmod +x scripts/test-restore.sh

# 권한 확인
ls -l scripts/*.sh
```

### 문제 2: Docker 컨테이너에 접속할 수 없음

**증상**
```
Error: No such container: biz-retriever-db
```

**해결 방법**
```bash
# Docker Compose 서비스 상태 확인
docker-compose -f docker-compose.pi.yml ps

# PostgreSQL 컨테이너 시작
docker-compose -f docker-compose.pi.yml up -d postgres

# 컨테이너 로그 확인
docker-compose -f docker-compose.pi.yml logs postgres
```

### 문제 3: 백업 파일이 손상됨

**증상**
```
❌ gzip 무결성 검증 실패
```

**해결 방법**
```bash
# 손상된 백업 파일 삭제
rm data/backups/db_backup_corrupted.sql.gz

# 새로운 백업 생성
bash scripts/backup-db.sh

# 백업 검증
bash scripts/verify-backup.sh data/backups/$(ls -t data/backups/*.sql.gz | head -1 | xargs basename)
```

### 문제 4: 복원 테스트 실패

**증상**
```
❌ 복원 실패
```

**해결 방법**
```bash
# 1. 테스트 컨테이너 정리
docker rm -f biz-retriever-test-db

# 2. 백업 파일 검증
bash scripts/verify-backup.sh data/backups/$(ls -t data/backups/*.sql.gz | head -1 | xargs basename)

# 3. 복원 테스트 다시 실행
bash scripts/test-restore.sh

# 4. 테스트 컨테이너 로그 확인
docker logs biz-retriever-test-db
```

### 문제 5: Slack 알림이 전송되지 않음

**증상**
```
백업이 완료되었지만 Slack 알림이 없음
```

**해결 방법**
```bash
# 1. .env 파일에서 SLACK_WEBHOOK_URL 확인
grep SLACK_WEBHOOK_URL .env

# 2. Slack Webhook URL이 올바른지 확인
# https://hooks.slack.com/services/YOUR/WEBHOOK/URL 형식이어야 함

# 3. 수동으로 Slack 알림 테스트
bash scripts/slack-notify.sh "Test Message" "success" "This is a test notification"

# 4. Slack 채널 권한 확인
# Slack 워크스페이스에서 Webhook URL이 올바른 채널로 설정되어 있는지 확인
```

### 문제 6: 디스크 공간 부족

**증상**
```
❌ 백업 실패: No space left on device
```

**해결 방법**
```bash
# 1. 디스크 사용량 확인
df -h

# 2. 오래된 백업 파일 수동 삭제
find data/backups -name "*.sql.gz" -mtime +30 -delete

# 3. 백업 보관 기간 조정 (backup-db.sh에서 14일 -> 7일로 변경)
# scripts/backup-db.sh의 다음 라인 수정:
# find "$BACKUP_DIR" -name "*.sql.gz" -mtime +7 -delete -print
```

### 문제 7: Cron 작업이 실행되지 않음

**증상**
```
예정된 시간에 백업이 실행되지 않음
```

**해결 방법**
```bash
# 1. Cron 데몬 상태 확인
sudo systemctl status cron  # Linux
sudo launchctl list | grep cron  # macOS

# 2. Crontab 문법 확인
crontab -l

# 3. 절대 경로 사용 확인
# 상대 경로 대신 절대 경로 사용: /path/to/scripts/backup-db.sh

# 4. 환경 변수 확인
# Cron은 제한된 환경에서 실행되므로 필요한 환경 변수를 명시적으로 설정

# 5. Cron 로그 확인
sudo tail -f /var/log/syslog | grep CRON  # Linux
log stream --predicate 'process == "cron"' --level debug  # macOS

# 6. 테스트 Cron 작업 추가
* * * * * echo "Cron is working" >> /tmp/cron-test.log

# 7. 1분 후 로그 확인
cat /tmp/cron-test.log
```

### 문제 8: PostgreSQL 버전 호환성

**증상**
```
ERROR: unsupported version "15.0" for pg_dump
```

**해결 방법**
```bash
# 1. PostgreSQL 버전 확인
docker-compose -f docker-compose.pi.yml exec postgres psql -U admin -c "SELECT version();"

# 2. pg_dump 버전 확인
docker-compose -f docker-compose.pi.yml exec postgres pg_dump --version

# 3. 버전 일치 확인
# docker-compose.pi.yml의 postgres 이미지 버전과 pg_dump 버전이 일치해야 함
```

---

## 모니터링 및 유지보수

### 정기적인 확인 사항

#### 주간 점검
```bash
# 최근 백업 파일 확인
ls -lh data/backups/*.sql.gz | tail -10

# 백업 파일 크기 추이 확인
du -sh data/backups/

# 복원 테스트 실행
bash scripts/test-restore.sh
```

#### 월간 점검
```bash
# 백업 파일 개수 확인
ls data/backups/*.sql.gz | wc -l

# 가장 오래된 백업 파일 확인
ls -lh data/backups/*.sql.gz | head -5

# 디스크 사용량 확인
df -h
```

### 백업 통계

```bash
# 백업 파일 개수
echo "백업 파일 개수: $(ls data/backups/*.sql.gz 2>/dev/null | wc -l)"

# 전체 백업 크기
echo "전체 백업 크기: $(du -sh data/backups/ | cut -f1)"

# 평균 백업 크기
echo "평균 백업 크기: $(du -sh data/backups/*.sql.gz 2>/dev/null | awk '{sum+=$1} END {print sum/NR}')"

# 최신 백업 파일
echo "최신 백업: $(ls -lh data/backups/*.sql.gz | tail -1)"
```

---

## 참고 자료

- [PostgreSQL pg_dump 문서](https://www.postgresql.org/docs/current/app-pgdump.html)
- [Docker Compose 문서](https://docs.docker.com/compose/)
- [Cron 작업 가이드](https://en.wikipedia.org/wiki/Cron)
- [Slack Webhook 문서](https://api.slack.com/messaging/webhooks)

---

**마지막 업데이트**: 2026-01-30
**작성자**: Database Automation Team
