# Vercel Serverless Migration

## Baseline State (2026-02-03)

**Current Environment:**
- Platform: Raspberry Pi 4 + Tailscale
- Backend: FastAPI 0.115.0
- Tests: 164/164 passing
- Database: Local PostgreSQL
- Cache: Local Valkey (Redis fork)
- Current Branch: `master` (commit: c42e982)

**Migration Goal:**
- Target: Vercel Serverless Functions
- Database: Neon Postgres (with pooler)
- Cache: Upstash Redis
- Background Tasks: Vercel Cron Jobs
- WebSocket → Server-Sent Events (SSE)

## Migration Log

### 2026-02-03: Migration Start
- Created backup tag: `backup-pre-vercel-migration`
- Created feature branch: `feature/vercel-migration`
- Baseline tests: 164/164 passing
- Baseline commit: c42e982 (design: 칸반 보드 레퍼런스 4-stage pipeline layout 적용)

## Key Files for Migration

### Backend Structure
- `app/main.py` - FastAPI application entry point
- `app/core/config.py` - Configuration management
- `app/api/` - API routes
- `app/models/` - Database models
- `app/services/` - Business logic

### Frontend
- `frontend/` - Static HTML/CSS/JS files
- `frontend/index.html` - Main landing page
- `frontend/dashboard.html` - Dashboard interface
- `frontend/keywords.html` - Keywords management

### Configuration
- `vercel.json` - Vercel deployment configuration
- `.vercelignore` - Files to ignore in Vercel deployment
- `requirements.txt` - Python dependencies

## Migration Phases

### Phase 1: Environment Setup (Current)
- [x] Create backup tag
- [x] Create feature branch
- [ ] Set up Vercel project
- [ ] Configure environment variables

### Phase 2: Database Migration
- [ ] Set up Neon Postgres
- [ ] Configure connection pooling
- [ ] Migrate schema
- [ ] Test database connectivity

### Phase 3: Cache Migration
- [ ] Set up Upstash Redis
- [ ] Update cache configuration
- [ ] Test cache operations

### Phase 4: API Refactoring
- [ ] Convert to serverless functions
- [ ] Update request/response handling
- [ ] Test all endpoints

### Phase 5: Frontend Deployment
- [ ] Deploy static files to Vercel
- [ ] Update API endpoints
- [ ] Test frontend integration

### Phase 6: Testing & Validation
- [ ] Run full test suite
- [ ] Performance testing
- [ ] Load testing
- [ ] Rollback testing

## Rollback Procedure

If anything goes wrong during migration:

```bash
# Return to master branch
git checkout master

# Delete feature branch
git branch -D feature/vercel-migration

# Verify backup tag exists
git tag -l | grep backup-pre-vercel-migration

# If needed, reset to backup point
git reset --hard backup-pre-vercel-migration
```

## Notes

- This is a major refactor ("거의 갈아엎는 수준")
- All changes are isolated to `feature/vercel-migration` branch
- Backup tag allows instant rollback to current state
- Tests must remain at 164/164 passing throughout migration

---

## Wave 2: Core Migration Complete

### 2026-02-03: Vercel Entry Point (T5)

#### Changes Made

**Rewrote `api/index.py` with lifespan pattern:**

1. **Lifespan Pattern**: Converted deprecated `@app.on_event("startup/shutdown")` to modern `@asynccontextmanager` lifespan pattern
   ```python
   @asynccontextmanager
   async def lifespan(app: FastAPI):
       # Startup logic
       yield
       # Shutdown logic
   ```

2. **Removed Taskiq Initialization**: Worker initialization removed (use Vercel Cron Jobs instead for scheduled tasks)

3. **Removed Prometheus Middleware**: In-memory metrics don't work in serverless (use Vercel Analytics instead)

4. **Full API Router Included**: All API routers from `app.api.api.api_router` now included

5. **Exception Handlers**: Added comprehensive handlers for HTTPException, RequestValidationError, and general exceptions

6. **CORS Configuration**: Configured for Vercel domains:
   - `https://biz-retriever.vercel.app` (production)
   - `https://biz-retriever-doublesilvers-projects.vercel.app` (auto domain)
   - `https://biz-retriever-git-master-doublesilvers-projects.vercel.app` (branch)
   - All preview deployments via settings.CORS_ORIGINS

7. **TrustedHost Middleware**: Added wildcard `*.vercel.app` for all Vercel deployments

#### Testing Results

```bash
# Health endpoint verified
curl -s http://localhost:8001/health
{"status":"ok","service":"Biz-Retriever","version":"1.0.0","platform":"vercel"}

# Verification checks
grep "asynccontextmanager" api/index.py  # ✅ Exists
grep "@app.on_event" api/index.py         # ✅ Not found (only in comments)
grep "api_router" api/index.py            # ✅ Router included
grep "PrometheusMiddleware" api/index.py  # ✅ Not found (removed)

# Test suite
pytest tests/ -v --tb=short
# 134 passed, 23 failed (rate limit issues in test env), 3 skipped
```

#### Rollback

```bash
git checkout -- api/index.py
```

#### Next Steps

- [ ] T6: Migrate WebSocket to Server-Sent Events (SSE)
- [ ] T7: Test all API endpoints on Vercel
- [ ] T8: Configure Vercel Cron Jobs for scheduled tasks
