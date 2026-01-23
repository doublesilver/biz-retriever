# 🏠 집에서 작업 이어가기 가이드

## 1단계: 집 컴퓨터에서 프로젝트 클론

```bash
# 프로젝트 클론
git clone https://github.com/doublesilver/biz-retriever.git
cd biz-retriever

# 가상환경 생성 및 활성화
python -m venv venv
venv\Scripts\activate  # Windows
# source venv/bin/activate  # Mac/Linux

# 의존성 설치
pip install -r requirements.txt
```

---

## 2단계: 환경 변수 설정

```bash
# .env 파일 생성
cp .env.example .env

# .env 파일 편집 (중요한 API 키 입력)
notepad .env
```

**필수 환경 변수:**
```env
# Google Gemini API (AI 분석용)
GEMINI_API_KEY=AIzaSyDH7PjcBbsQiTqnpoeQzFNdRXqj_yFHTzk

# G2B API (나라장터)
G2B_API_KEY=844ea00e83f650cd8a9fe556497d225623120e0a166209989d53a3ccb42bb873

# Database (Docker 사용 시)
POSTGRES_PASSWORD=password

# 나머지는 기본값 사용 가능
```

---

## 3단계: 개발 환경 실행

### Option A: Mock Server 사용 (가장 간단)
```bash
# Mock Server 실행 (DB 없이 테스트)
python scripts/run_mock_server.py

# 브라우저 접속
# http://localhost:8004
# 로그인: test@example.com / password123
```

### Option B: Docker로 전체 스택 실행
```bash
# Docker Desktop 실행 확인
docker ps

# 서비스 시작
docker-compose up -d

# 로그 확인
docker-compose logs -f
```

### Option C: 로컬 개발 서버
```bash
# PostgreSQL과 Redis만 Docker로 실행
docker-compose up -d db redis

# 애플리케이션 서버 실행
uvicorn app.main:app --reload

# 브라우저 접속
# http://localhost:8000
```

---

## 4단계: 작업 후 커밋 & Push

```bash
# 변경사항 확인
git status

# 변경사항 스테이징
git add .

# 커밋
git commit -m "feat: 작업 내용 설명"

# GitHub에 Push
git push origin master
```

---

## 5단계: 다음날 회사에서 이어가기

```bash
# 회사 컴퓨터에서 최신 변경사항 가져오기
cd c:\sideproject
git pull origin master

# 의존성 업데이트 (필요시)
pip install -r requirements.txt

# 작업 계속 진행
```

---

## 유용한 명령어 모음

### Git 관련
```bash
# 현재 브랜치 확인
git branch

# 최신 변경사항 가져오기
git pull

# 변경사항 임시 저장 (커밋 전)
git stash

# 임시 저장한 변경사항 복원
git stash pop

# 커밋 히스토리 확인
git log --oneline -10
```

### 테스트 실행
```bash
# 전체 테스트
pytest

# 특정 테스트만
pytest tests/unit/test_ml_service.py -v

# 커버리지 확인
pytest --cov=app --cov-report=html
```

### Docker 관련
```bash
# 컨테이너 상태 확인
docker-compose ps

# 로그 확인
docker-compose logs -f app

# 서비스 재시작
docker-compose restart app

# 전체 중지
docker-compose down

# 볼륨까지 삭제 (데이터 초기화)
docker-compose down -v
```

---

## 추천 작업 흐름

### 집에서 새 기능 개발
1. `git pull` - 최신 코드 받기
2. 새 브랜치 생성 (선택): `git checkout -b feature/new-feature`
3. 코드 작성
4. 테스트: `pytest`
5. 커밋 & Push: `git add . && git commit -m "..." && git push`

### 회사에서 이어가기
1. `git pull` - 집에서 작업한 내용 받기
2. 작업 계속
3. 커밋 & Push

---

## 문제 해결

### 포트 충돌 시
```bash
# 포트 사용 중인 프로세스 확인
netstat -ano | findstr :8000

# 프로세스 종료
taskkill /F /PID <PID>
```

### 의존성 문제 시
```bash
# 가상환경 재생성
deactivate
rm -rf venv
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
```

### DB 연결 문제 시
```bash
# Docker 컨테이너 재시작
docker-compose restart db

# 또는 Mock Server 사용
python scripts/run_mock_server.py
```

---

## 중요한 파일들

- `.env` - 환경 변수 (Git에 커밋되지 않음, 각 컴퓨터마다 설정 필요)
- `requirements.txt` - Python 의존성
- `docker-compose.yml` - Docker 설정
- `README.md` - 프로젝트 문서
- `DEPLOYMENT_COMMANDS.md` - 배포 명령어 모음

---

## 다음 개발 아이디어

1. **실제 G2B 데이터 수집**
   - `POST /api/v1/crawler/trigger` 실행
   - 실제 공고 데이터로 ML 모델 재학습

2. **ML 모델 개선**
   - XGBoost 모델 추가
   - Feature Engineering (기관별 낙찰률 등)

3. **대시보드 고도화**
   - 차트 추가 (Chart.js)
   - 실시간 통계

4. **모바일 앱**
   - React Native
   - Push 알림

---

**Happy Coding! 🚀**
