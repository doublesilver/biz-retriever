# Alembic 마이그레이션 가이드

## 개요
Alembic은 SQLAlchemy용 데이터베이스 마이그레이션 도구입니다. 이 프로젝트는 async SQLAlchemy 2.0을 지원하도록 설정되어 있습니다.

## 설정 완료 항목
- ✅ Alembic 설치 및 초기화
- ✅ `alembic/env.py` 설정 (async 지원)
- ✅ 초기 마이그레이션 파일 생성 (`001_initial_schema.py`)
- ✅ 모든 모델 (User, BidAnnouncement) 포함

## 사용법

### 1. 새 마이그레이션 생성
모델을 변경한 후, 자동으로 마이그레이션 파일을 생성합니다:

```bash
# 자동 생성 (권장)
python -m alembic revision --autogenerate -m "마이그레이션 설명"

# 수동 생성 (필요시만)
python -m alembic revision -m "마이그레이션 설명"
```

### 2. 마이그레이션 적용

```bash
# 최신 버전으로 업그레이드
python -m alembic upgrade head

# 특정 버전으로 업그레이드
python -m alembic upgrade <revision_id>

# 한 단계만 업그레이드
python -m alembic upgrade +1
```

### 3. 마이그레이션 롤백

```bash
# 한 단계 롤백
python -m alembic downgrade -1

# 특정 버전으로 롤백
python -m alembic downgrade <revision_id>

# 전체 롤백
python -m alembic downgrade base
```

### 4. 현재 상태 확인

```bash
# 현재 리비전 확인
python -m alembic current

# 마이그레이션 히스토리 확인
python -m alembic history

# 상세 히스토리 확인
python -m alembic history --verbose
```

## 주요 명령어

| 명령어 | 설명 |
|--------|------|
| `revision --autogenerate` | 모델 변경사항 자동 감지 및 마이그레이션 생성 |
| `upgrade head` | 최신 마이그레이션 적용 |
| `downgrade -1` | 이전 마이그레이션으로 롤백 |
| `current` | 현재 적용된 마이그레이션 확인 |
| `history` | 마이그레이션 히스토리 확인 |

## 모범 사례

### ✅ DO
- 프로덕션 배포 전 마이그레이션 테스트
- 명확하고 설명적인 마이그레이션 메시지 작성
- `--autogenerate` 사용 후 생성된 파일 검토
- 마이그레이션 버전 관리 (Git 커밋)

### ❌ DON'T
- 생성된 마이그레이션 파일을 직접 수정하기 전에 확인 없이 적용
- 여러 개의 모델 변경을 하나의 마이그레이션에 몰아넣기
- 이미 배포된 마이그레이션 파일 수정

## 초기 데이터베이스 설정

새로운 환경에서 데이터베이스를 설정할 때:

```bash
# 1. Docker Compose로 DB 시작
docker-compose up -d db

# 2. 마이그레이션 적용
python -m alembic upgrade head
```

## 팀 협업 시 워크플로우

1. **모델 변경**
   ```python
   # app/db/models.py 수정
   ```

2. **마이그레이션 생성**
   ```bash
   python -m alembic revision --autogenerate -m "Add user profile fields"
   ```

3. **생성된 파일 검토**
   ```bash
   # alembic/versions/<timestamp>_add_user_profile_fields.py 확인
   ```

4. **로컬 테스트**
   ```bash
   python -m alembic upgrade head
   # 테스트 실행
   pytest
   ```

5. **Git 커밋 및 푸시**
   ```bash
   git add alembic/versions/
   git commit -m "Add user profile fields migration"
   git push
   ```

6. **팀원들의 적용**
   ```bash
   git pull
   python -m alembic upgrade head
   ```

## 트러블슈팅

### 문제: "Can't locate revision identified by 'xxx'"
**해결**: 히스토리를 확인하고 올바른 revision ID 사용
```bash
python -m alembic history
```

### 문제: "Target database is not up to date"
**해결**: 현재 상태 확인 후 최신으로 업그레이드
```bash
python -m alembic current
python -m alembic upgrade head
```

### 문제: autogenerate가 변경사항을 감지하지 못함
**해결**: 
1. 모델이 `Base.metadata`에 등록되었는지 확인
2. `alembic/env.py`에서 모델을 임포트했는지 확인
3. 수동으로 마이그레이션 생성 후 직접 작성

## CI/CD 통합

`.github/workflows/ci.yml`에 마이그레이션 체크 추가 권장:

```yaml
- name: Check migrations
  run: |
    python -m alembic check
    python -m alembic upgrade head
```

## 참고 자료
- [Alembic 공식 문서](https://alembic.sqlalchemy.org/)
- [SQLAlchemy 2.0 마이그레이션 가이드](https://docs.sqlalchemy.org/en/20/changelog/migration_20.html)
