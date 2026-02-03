# Job+Polling Pattern for Async Tasks

## Problem

Vercel Functions have 60-second timeout. Long-running tasks (Gemini AI analysis, file processing) exceed this limit.

## Solution: Job+Polling Pattern

1. **Client** → POST `/api/v1/analyze/` with input
2. **Server** → Create Job in database, return `job_id` immediately
3. **Background** → Process task asynchronously (triggered separately)
4. **Client** → Poll GET `/api/v1/jobs/{job_id}` every 2s
5. **Server** → Return status: PENDING → PROCESSING → SUCCESS/FAILURE

## Flow Diagram

```
Client              Server               Background Worker
|                   |                    |
|-- POST /analyze ->|                    |
|<-- 202 {job_id} --|                    |
|                   |-- Create Job ----->DB
|                   |                    |
|                   |                    |-- Trigger task
|-- GET /jobs/123 ->|                    |-- Processing...
|<-- 200 PENDING ---|                    |
|   (wait 2s)       |                    |
|-- GET /jobs/123 ->|                    |
|<-- 200 PROCESSING-|                    |-- Complete!
|   (wait 2s)       |                    |-- Update DB
|-- GET /jobs/123 ->|                    |
|<-- 200 SUCCESS ---|<-- result ---------DB
|   + result        |                    |
```

## Implementation

### Step 1: Create Job

```python
from app.services.job_service import JobService
from app.schemas.job import JobCreate

@router.post("/analyze/", status_code=202)
async def analyze_bid(
    input: AnalysisInput,
    db: DbSession,
    current_user: CurrentUser,
):
    # Create job immediately
    job = await JobService.create_job(
        db,
        user_id=current_user.id,
        job_data=JobCreate(task_type="gemini_analysis", input_data=input.model_dump())
    )
    
    # Trigger background processing (Vercel Cron, separate function, etc.)
    # await trigger_analysis_task(job.id)  # Implementation depends on architecture
    
    return {"job_id": job.id, "status": "PENDING", "message": "Analysis started"}
```

### Step 2: Poll Status

```python
@router.get("/jobs/{job_id}")
async def get_job_status(job_id: str, ...):
    job = await JobService.get_job(db, job_id, current_user.id)
    return job
```

### Step 3: Background Worker Updates Job

```python
from app.services.job_service import JobService
from app.schemas.job import JobUpdate

async def process_analysis(job_id: str, db: AsyncSession):
    # Mark as processing
    await JobService.mark_processing(db, job_id)
    
    try:
        # Do the actual work
        result = await gemini_analyze(...)
        
        # Mark success
        await JobService.mark_success(db, job_id, result)
    except Exception as e:
        # Mark failure
        await JobService.mark_failure(db, job_id, str(e))
```

### Step 4: Frontend Polling

```javascript
async function analyzeWithPolling(input) {
    // Start job
    const response = await fetch('/api/v1/analyze/', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'Authorization': `Bearer ${token}`,
        },
        body: JSON.stringify(input),
    });
    const { job_id } = await response.json();
    
    // Poll until complete
    while (true) {
        const job = await fetch(`/api/v1/jobs/${job_id}`, {
            headers: { 'Authorization': `Bearer ${token}` },
        }).then(r => r.json());
        
        if (job.status === 'SUCCESS') {
            return job.result;
        } else if (job.status === 'FAILURE') {
            throw new Error(job.error_message);
        }
        
        // Update progress bar if available
        if (job.progress > 0) {
            updateProgressBar(job.progress);
        }
        
        // Wait 2 seconds before next poll
        await new Promise(resolve => setTimeout(resolve, 2000));
    }
}
```

## Job Lifecycle

| Status | Description | Terminal |
|--------|-------------|----------|
| PENDING | Created, waiting for processing | No |
| PROCESSING | Task in progress | No |
| SUCCESS | Task completed successfully | Yes |
| FAILURE | Task failed with error | Yes |
| CANCELLED | Task cancelled by user | Yes |

## Database Schema

```sql
CREATE TABLE jobs (
    id VARCHAR(36) PRIMARY KEY,           -- UUID
    status VARCHAR(20) NOT NULL,          -- PENDING, PROCESSING, SUCCESS, FAILURE, CANCELLED
    task_type VARCHAR(50) NOT NULL,       -- gemini_analysis, file_export, etc.
    input_data JSON,                      -- Task input
    result JSON,                          -- Task output (on success)
    error_message TEXT,                   -- Error details (on failure)
    progress INTEGER DEFAULT 0,           -- 0-100 percentage
    user_id INTEGER NOT NULL REFERENCES users(id),
    created_at TIMESTAMP WITH TIME ZONE,
    started_at TIMESTAMP WITH TIME ZONE,
    completed_at TIMESTAMP WITH TIME ZONE,
    expires_at TIMESTAMP WITH TIME ZONE   -- For cleanup
);

CREATE INDEX idx_jobs_status ON jobs(status);
CREATE INDEX idx_jobs_user_id ON jobs(user_id);
CREATE INDEX idx_jobs_expires_at ON jobs(expires_at);
```

## Database Cleanup

Jobs have `expires_at` timestamp (default 7 days). Use Vercel Cron or Taskiq scheduler to cleanup:

```python
# app/tasks/cleanup.py
from datetime import datetime
from sqlalchemy import delete

async def cleanup_expired_jobs(db: AsyncSession):
    """Delete jobs older than 7 days"""
    await db.execute(
        delete(Job).where(Job.expires_at < datetime.utcnow())
    )
    await db.commit()
```

Add to Taskiq scheduler:

```python
# app/worker/taskiq_app.py
@broker.task(schedule=CronSpec(hour=3, minute=0))  # Daily at 3 AM
async def cleanup_jobs_task():
    async with async_session_maker() as db:
        await cleanup_expired_jobs(db)
```

## API Reference

### GET /api/v1/jobs/{job_id}

Get job status by ID.

**Response:**
```json
{
    "id": "550e8400-e29b-41d4-a716-446655440000",
    "status": "PROCESSING",
    "task_type": "gemini_analysis",
    "progress": 45,
    "input_data": {"bid_id": 123},
    "result": null,
    "error_message": null,
    "created_at": "2026-02-03T10:00:00Z",
    "started_at": "2026-02-03T10:00:05Z",
    "completed_at": null
}
```

**Status Codes:**
- `200 OK` - Job found
- `404 Not Found` - Job not found or belongs to another user

## Benefits

- ✅ Works within 60s timeout
- ✅ Client gets immediate response (202 Accepted)
- ✅ Progress tracking (0-100%)
- ✅ Error handling with details
- ✅ Scalable (DB-backed, not in-memory)
- ✅ User-scoped (can only see own jobs)
- ✅ Auto-cleanup (expires after 7 days)

## Best Practices

1. **Polling Interval**: Start with 2 seconds, consider exponential backoff for long tasks
2. **Timeout**: Client should give up after ~5 minutes of polling
3. **Idempotency**: Same input should return existing job, not create duplicate
4. **Progress Updates**: Update progress regularly for better UX
5. **Error Details**: Include actionable error messages for debugging
