# Redis 캐시 전략 문서

## 개요
Biz-Retriever는 **FastAPI-Cache2**와 **Redis**를 사용하여 API 응답 캐싱을 구현합니다. 이를 통해 데이터베이스 부하를 줄이고 응답 속도를 향상시킵니다.

## 캐시 아키텍처

```
┌─────────────┐
│   Client    │
└──────┬──────┘
       │
       ▼
┌─────────────────┐
│  FastAPI 서버   │
│  ┌──────────┐   │
│  │ Cache    │◄──┼─── Redis (캐시 백엔드)
│  │ Decorator│   │
│  └──────────┘   │
│       │         │
│       ▼         │
│  ┌──────────┐   │
│  │ Service  │   │
│  │ Layer    │   │
│  └──────────┘   │
│       │         │
│       ▼         │
│  ┌──────────┐   │
│  │PostgreSQL│   │
│  └──────────┘   │
└─────────────────┘
```

## 캐시 키 네이밍 규칙

### 1. 패턴
```
<namespace>:<resource>:<identifier>:<query_params>
```

### 2. 예시
```python
# 공고 목록
cache:bids:list:page=1&limit=10&source=G2B

# 특정 공고
cache:bids:detail:123

# Analytics 요약
cache:analytics:summary:start_date=2024-01-01&end_date=2024-01-31

# 필터 검색
cache:bids:search:keyword=software&importance=3
```

### 3. 구현
```python
from fastapi_cache.decorator import cache

@router.get("/bids/")
@cache(
    expire=300,  # TTL: 5분
    namespace="bids",
    key_builder=lambda func, *args, **kwargs: f"list:{kwargs.get('page', 1)}:{kwargs.get('limit', 10)}"
)
async def get_bids(...):
    pass
```

## TTL (Time-To-Live) 전략

### 캐시 유효 시간 정책

| 엔드포인트 | TTL | 이유 |
|-----------|-----|------|
| `GET /bids/` | **5분 (300초)** | 공고 목록은 자주 변경되지만, 실시간성이 필수는 아님 |
| `GET /bids/{id}` | **10분 (600초)** | 개별 공고는 변경이 적음 |
| `GET /analytics/summary` | **1시간 (3600초)** | 통계 데이터는 실시간 갱신 불필요 |
| `GET /analytics/trends` | **30분 (1800초)** | 트렌드 데이터는 시간대별 변화 반영 |
| `GET /filters/` | **15분 (900초)** | 필터 설정은 변경이 적음 |
| `POST /export/excel` | **캐시 안함** | 파일 생성은 매번 새로 수행 |
| `POST /crawler/trigger` | **캐시 안함** | 크롤링은 항상 실행 |

### TTL 설정 가이드라인

#### ✅ 긴 TTL (30분 ~ 1시간)
- 자주 변경되지 않는 데이터
- 통계/분석 데이터
- 설정 정보

#### ⚠️ 중간 TTL (5 ~ 15분)
- 목록 데이터
- 검색 결과
- 필터링된 데이터

#### 🔥 짧은 TTL (1 ~ 3분)
- 실시간성이 중요한 데이터
- 사용자별 데이터
- 자주 변경되는 데이터

#### 🚫 캐시 안함
- 쓰기 작업 (POST, PUT, DELETE)
- 파일 다운로드/생성
- 민감한 개인정보

## 캐시 무효화 (Cache Invalidation)

### 1. 자동 무효화 (TTL 기반)
```python
# 가장 일반적인 방법
@cache(expire=300)  # 5분 후 자동 삭제
async def get_data():
    pass
```

### 2. 수동 무효화 (명시적 삭제)

#### a. 특정 키 삭제
```python
from fastapi_cache import FastAPICache

# 공고 생성 시 목록 캐시 무효화
@router.post("/bids/")
async def create_bid(bid: BidCreate):
    # 공고 생성
    new_bid = await service.create_bid(bid)
    
    # 목록 캐시 무효화
    await FastAPICache.clear(namespace="bids:list")
    
    return new_bid
```

#### b. 네임스페이스 전체 삭제
```python
# 모든 공고 관련 캐시 삭제
await FastAPICache.clear(namespace="bids")
```

#### c. 패턴 기반 삭제
```python
from app.core.cache import redis_client

# Redis 패턴 매칭으로 삭제
async def invalidate_bid_caches(bid_id: int):
    pattern = f"cache:bids:*:{bid_id}*"
    keys = await redis_client.keys(pattern)
    if keys:
        await redis_client.delete(*keys)
```

### 3. 무효화 시나리오

#### 공고 생성 시
```python
@router.post("/bids/")
async def create_bid(bid: BidCreate):
    new_bid = await service.create_bid(bid)
    
    # 모든 목록 캐시 무효화
    await FastAPICache.clear(namespace="bids:list")
    await FastAPICache.clear(namespace="analytics")  # 통계도 업데이트
    
    return new_bid
```

#### 공고 수정 시
```python
@router.put("/bids/{bid_id}")
async def update_bid(bid_id: int, bid: BidUpdate):
    updated_bid = await service.update_bid(bid_id, bid)
    
    # 특정 공고 캐시 무효화
    await FastAPICache.clear(namespace=f"bids:detail:{bid_id}")
    # 목록 캐시도 무효화
    await FastAPICache.clear(namespace="bids:list")
    
    return updated_bid
```

#### 공고 삭제 시
```python
@router.delete("/bids/{bid_id}")
async def delete_bid(bid_id: int):
    await service.delete_bid(bid_id)
    
    # 모든 관련 캐시 무효화
    await FastAPICache.clear(namespace="bids")
    await FastAPICache.clear(namespace="analytics")
    
    return {"message": "Deleted"}
```

## 캐시 워밍 (Cache Warming)

자주 사용되는 데이터를 미리 캐시에 로드하여 첫 요청 응답 속도를 개선합니다.

```python
# app/core/cache.py
async def warm_up_cache():
    """애플리케이션 시작 시 캐시 워밍"""
    from app.api.endpoints.bids import get_bids
    from app.api.endpoints.analytics import get_summary
    
    # 인기 쿼리 미리 로드
    await get_bids(page=1, limit=10, importance_score=3)
    await get_summary()
    
    logger.info("Cache warmed up successfully")

# app/main.py
@app.on_event("startup")
async def startup():
    await init_redis_cache()
    await warm_up_cache()  # 캐시 워밍
```

## 캐시 모니터링

### 1. 캐시 히트율 측정
```python
from app.core.metrics import cache_hit_counter, cache_miss_counter

@cache(expire=300)
async def get_data():
    # 캐시 미스 시 카운터 증가
    cache_miss_counter.inc()
    return data

# 캐시 히트 시 (decorator 내부에서 자동)
# cache_hit_counter.inc()
```

### 2. Redis 메모리 사용량 확인
```bash
# Redis CLI
redis-cli INFO memory
redis-cli INFO stats
```

### 3. 캐시 키 확인
```bash
# 모든 캐시 키 조회
redis-cli KEYS "cache:*"

# 특정 패턴 조회
redis-cli KEYS "cache:bids:*"

# 키 TTL 확인
redis-cli TTL "cache:bids:list:1:10"
```

## 모범 사례

### ✅ DO
1. **적절한 TTL 설정**: 데이터 특성에 맞는 TTL 사용
2. **namespace 일관성**: 명확한 네이밍 규칙 준수
3. **캐시 무효화**: 데이터 변경 시 관련 캐시 즉시 삭제
4. **캐시 워밍**: 자주 사용되는 데이터 미리 로드
5. **모니터링**: 캐시 히트율 및 메모리 사용량 추적

### ❌ DON'T
1. **과도한 캐싱**: 모든 엔드포인트를 캐싱하지 말 것
2. **긴 TTL on 동적 데이터**: 자주 변경되는 데이터에 긴 TTL 사용 금지
3. **개인정보 캐싱**: 민감한 사용자 데이터 캐싱 금지
4. **쓰기 작업 캐싱**: POST/PUT/DELETE는 캐싱하지 말 것
5. **캐시 키 충돌**: 고유하지 않은 키 사용 금지

## 환경별 설정

### 개발 환경
```python
# .env.development
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_PASSWORD=
CACHE_ENABLED=True
CACHE_DEFAULT_TTL=60  # 짧은 TTL로 빠른 테스트
```

### 프로덕션 환경
```python
# .env.production
REDIS_HOST=redis-cluster.example.com
REDIS_PORT=6379
REDIS_PASSWORD=<strong-password>
CACHE_ENABLED=True
CACHE_DEFAULT_TTL=300  # 적절한 TTL
REDIS_MAX_CONNECTIONS=50
```

### 테스트 환경
```python
# tests/conftest.py
@pytest.fixture
async def client():
    # 테스트 시 In-Memory 캐시 사용
    FastAPICache.init(InMemoryBackend())
    yield client
```

## 트러블슈팅

### 문제: 캐시가 작동하지 않음
**해결**:
1. Redis 연결 확인: `redis-cli PING`
2. `fastapi-cache2` 초기화 확인
3. `@cache` 데코레이터 올바른 위치에 적용

### 문제: 캐시가 업데이트되지 않음
**해결**:
1. 무효화 로직 확인
2. TTL 값 확인
3. 수동으로 캐시 클리어: `await FastAPICache.clear()`

### 문제: Redis 메모리 부족
**해결**:
1. TTL 값 줄이기
2. `maxmemory-policy` 설정: `allkeys-lru`
3. 불필요한 캐시 삭제

## 참고 자료
- [FastAPI-Cache2 문서](https://github.com/long2ice/fastapi-cache)
- [Redis Best Practices](https://redis.io/docs/manual/patterns/)
- [Caching Strategies](https://docs.aws.amazon.com/AmazonElastiCache/latest/mem-ug/Strategies.html)
