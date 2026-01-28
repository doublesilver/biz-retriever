# Biz-Retriever 라즈베리파이 배포 가이드

## 📋 배포 전 체크리스트

### ✅ 완료된 작업
- [x] Docker Compose 설정 파일 작성 (`docker-compose.pi.yml`)
- [x] 환경 변수 템플릿 작성 (`.env.pi.example`)
- [x] 배포 스크립트 작성 (`scripts/deploy-pi.sh`)
- [x] 백업 스크립트 작성 (`scripts/backup-db.sh`)
- [x] 모니터링 스크립트 작성 (`scripts/monitor.sh`)
- [x] 리소스 최적화 (4GB RAM 기준)
- [x] 프로젝트 파일 정리 완료

### 📦 생성된 파일
```
c:\sideproject/
├── docker-compose.pi.yml          # 라즈베리파이용 Docker Compose
├── .env.pi.example                # 환경 변수 템플릿
├── RASPBERRY_PI_DEPLOYMENT_SPEC.md # 배포 사양서
└── scripts/
    ├── deploy-pi.sh               # 자동 배포
    ├── backup-db.sh               # DB 백업
    └── monitor.sh                 # 리소스 모니터링
```

---

## 🚀 배포 절차

### 1단계: 라즈베리파이 환경 확인

#### 필수 요구사항
- [ ] 라즈베리파이 4 (4GB RAM)
- [ ] Raspberry Pi OS 64-bit 또는 Ubuntu Server 22.04
- [ ] 2.0GHz 오버클럭 설정 완료
- [ ] 2GB Swap 설정 완료
- [ ] Tailscale 설치 및 연결 완료
- [ ] 인터넷 연결 확인

#### 확인 명령어
```bash
# OS 확인
uname -a

# RAM 확인
free -h

# CPU 확인
lscpu | grep "Model name"

# Swap 확인
swapon --show

# Tailscale 확인
tailscale status
```

---

### 2단계: 프로젝트 파일 전송

#### 방법 1: Tailscale을 통한 SCP 전송
```bash
# Windows에서 실행 (PowerShell)
scp -r c:\sideproject\* admin@<TAILSCALE_IP>:/home/admin/projects/biz-retriever/
```

#### 방법 2: Git Clone (권장)
```bash
# 라즈베리파이에서 실행
cd /home/admin/projects
git clone https://github.com/doublesilver/biz-retriever.git
cd biz-retriever
```

---

### 3단계: Docker 설치 (미설치 시)

```bash
# Docker 설치
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh

# 현재 사용자를 docker 그룹에 추가
sudo usermod -aG docker $USER

# 재로그인 또는 다음 명령어 실행
newgrp docker

# Docker Compose 설치
sudo apt-get update
sudo apt-get install -y docker-compose

# 설치 확인
docker --version
docker-compose --version
```

---

### 4단계: 환경 변수 설정

```bash
cd /home/admin/projects/biz-retriever

# .env 파일 생성
cp .env.pi.example .env

# .env 파일 편집
nano .env
```

#### 필수 설정 항목
```bash
# 강력한 비밀번호로 변경
POSTGRES_PASSWORD=<강력한_비밀번호>

# 랜덤 시크릿 키 생성
SECRET_KEY=$(python3 -c "import secrets; print(secrets.token_urlsafe(32))")

# API 키 입력
GEMINI_API_KEY=<your_gemini_api_key>
G2B_API_KEY=<your_g2b_api_key>
SLACK_WEBHOOK_URL=<your_slack_webhook_url>
```

---

### 5단계: 배포 실행

```bash
# 스크립트 실행 권한 부여
chmod +x scripts/*.sh

# 배포 스크립트 실행
./scripts/deploy-pi.sh
```

#### 수동 배포 (스크립트 사용 안 할 경우)
```bash
# 필요한 디렉토리 생성
mkdir -p data/{postgres,redis,nginx-proxy-manager,letsencrypt,backups}
mkdir -p logs

# Docker 이미지 빌드 및 컨테이너 시작
docker-compose -f docker-compose.pi.yml up -d --build

# 로그 확인
docker-compose -f docker-compose.pi.yml logs -f
```

---

### 6단계: 서비스 확인

#### 컨테이너 상태 확인
```bash
docker-compose -f docker-compose.pi.yml ps
```

#### 예상 출력
```
NAME                        STATUS              PORTS
biz-retriever-api           Up (healthy)        0.0.0.0:8000->8000/tcp
biz-retriever-worker        Up                  
biz-retriever-beat          Up                  
biz-retriever-db            Up (healthy)        5432/tcp
biz-retriever-redis         Up (healthy)        6379/tcp
nginx-proxy-manager         Up                  0.0.0.0:80-81->80-81/tcp, 0.0.0.0:443->443/tcp
```

#### 헬스 체크
```bash
# API 서버 확인
curl http://localhost:8000/health

# 예상 응답: {"status":"healthy"}
```

#### 웹 브라우저 접속
- API: `http://<TAILSCALE_IP>:8000`
- API Docs: `http://<TAILSCALE_IP>:8000/docs`
- Nginx PM: `http://<TAILSCALE_IP>:81`

---

### 7단계: 리소스 모니터링

```bash
# 리소스 사용량 확인
./scripts/monitor.sh

# 실시간 모니터링
docker stats

# 특정 컨테이너 로그
docker-compose -f docker-compose.pi.yml logs -f api
```

---

## 🔧 문제 해결

### 메모리 부족 오류
```bash
# Swap 사용량 확인
free -h

# 컨테이너 재시작
docker-compose -f docker-compose.pi.yml restart
```

### 컨테이너 시작 실패
```bash
# 로그 확인
docker-compose -f docker-compose.pi.yml logs <container_name>

# 컨테이너 재빌드
docker-compose -f docker-compose.pi.yml up -d --build --force-recreate
```

### 포트 충돌
```bash
# 포트 사용 확인
sudo netstat -tulpn | grep LISTEN

# 충돌 시 docker-compose.pi.yml에서 포트 변경
```

---

## 📊 일일 운영

### 백업
```bash
# 수동 백업
./scripts/backup-db.sh

# Cron으로 자동 백업 설정 (매일 새벽 3시)
crontab -e
# 추가: 0 3 * * * /home/admin/projects/biz-retriever/scripts/backup-db.sh
```

### 로그 관리
```bash
# 로그 확인
tail -f logs/*.log

# 로그 정리 (7일 이상 된 로그 삭제)
find logs/ -name "*.log" -mtime +7 -delete
```

### 업데이트
```bash
# Git Pull
git pull origin master

# 재빌드 및 재시작
docker-compose -f docker-compose.pi.yml up -d --build
```

---

### 7.5 Soft Match 및 AI 분석 검증 (Phase 3)
```bash
# 매칭 서비스 로그 확인 (새로운 공고 처리 시)
docker-compose -f docker-compose.pi.yml logs -f api | grep "분석"

# 예상 출력
# INFO: 매칭 분석 완료: 공고ID=123, 점수=75, 추천가=1.2억
```

---

## 🎯 다음 단계

### 선택 사항
1. **도메인 연결**
   - Nginx Proxy Manager에서 도메인 설정
   - Let's Encrypt SSL 인증서 자동 발급

2. **모니터링 강화**
   - Prometheus + Grafana 추가
   - 알림 설정 (Slack/Email)

3. **성능 최적화**
   - 리소스 사용량 분석
   - 메모리/CPU 제한 조정

---

**작성일**: 2026-01-27
**상태**: Phase 3 완료 & 배포 준비 완료 ✅
**다음**: 라즈베리파이에서 배포 실행
