"""
Jobs API 통합 테스트

Job+Polling pattern for serverless async tasks.
Replaces Celery/WebSocket approach for Vercel compatibility.
"""

from unittest.mock import AsyncMock, patch

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession


class TestJobsAPI:
    """Jobs API 통합 테스트"""

    # ============================================
    # GET /api/v1/jobs/{job_id} 테스트
    # ============================================

    @pytest.mark.asyncio
    async def test_get_job_unauthenticated(self, async_client: AsyncClient):
        """미인증 시 401 응답"""
        response = await async_client.get("/api/v1/jobs/test-job-id")

        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_get_job_not_found(self, authenticated_client: AsyncClient):
        """존재하지 않는 Job - 404 응답"""
        response = await authenticated_client.get(
            "/api/v1/jobs/nonexistent-job-id-12345"
        )

        assert response.status_code == 404
        data = response.json()
        # Response may have 'detail' or 'message' depending on exception handler
        error_msg = data.get("detail", "") or data.get("message", "")
        assert "not found" in error_msg.lower()

    @pytest.mark.asyncio
    async def test_get_job_success(
        self, authenticated_client: AsyncClient, test_db: AsyncSession, test_user
    ):
        """Job 조회 성공"""
        from datetime import datetime, timedelta

        from app.db.models import Job

        # Create a test job
        job = Job(
            id="test-job-123",
            user_id=test_user.id,
            task_type="test_task",
            status="PENDING",
            progress=0,
            expires_at=datetime.utcnow() + timedelta(days=7),
        )
        test_db.add(job)
        await test_db.commit()

        response = await authenticated_client.get("/api/v1/jobs/test-job-123")

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == "test-job-123"
        assert data["status"] == "PENDING"
        assert data["task_type"] == "test_task"
        assert data["progress"] == 0

    @pytest.mark.asyncio
    async def test_get_job_wrong_user(
        self, authenticated_client: AsyncClient, test_db: AsyncSession
    ):
        """다른 사용자의 Job 접근 - 404 응답 (보안상 존재여부 숨김)"""
        from datetime import datetime, timedelta

        from app.db.models import Job

        # Create a job owned by different user (user_id=99999)
        job = Job(
            id="other-user-job-456",
            user_id=99999,  # Different user
            task_type="test_task",
            status="PENDING",
            progress=0,
            expires_at=datetime.utcnow() + timedelta(days=7),
        )
        test_db.add(job)
        await test_db.commit()

        response = await authenticated_client.get("/api/v1/jobs/other-user-job-456")

        # Should return 404 to hide existence of other user's jobs
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_get_job_with_result(
        self, authenticated_client: AsyncClient, test_db: AsyncSession, test_user
    ):
        """완료된 Job 조회 (result 포함)"""
        from datetime import datetime, timedelta

        from app.db.models import Job

        # Create a completed job with result
        job = Job(
            id="completed-job-789",
            user_id=test_user.id,
            task_type="rag_analysis",
            status="SUCCESS",
            progress=100,
            result={"summary": "Test summary", "keywords": ["test", "keywords"]},
            started_at=datetime.utcnow() - timedelta(minutes=5),
            completed_at=datetime.utcnow(),
            expires_at=datetime.utcnow() + timedelta(days=7),
        )
        test_db.add(job)
        await test_db.commit()

        response = await authenticated_client.get("/api/v1/jobs/completed-job-789")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "SUCCESS"
        assert data["progress"] == 100
        assert data["result"] is not None
        assert "summary" in data["result"]

    @pytest.mark.asyncio
    async def test_get_job_with_error(
        self, authenticated_client: AsyncClient, test_db: AsyncSession, test_user
    ):
        """실패한 Job 조회 (error_message 포함)"""
        from datetime import datetime, timedelta

        from app.db.models import Job

        # Create a failed job
        job = Job(
            id="failed-job-101",
            user_id=test_user.id,
            task_type="rag_analysis",
            status="FAILURE",
            progress=50,
            error_message="Gemini API rate limit exceeded",
            started_at=datetime.utcnow() - timedelta(minutes=2),
            completed_at=datetime.utcnow(),
            expires_at=datetime.utcnow() + timedelta(days=7),
        )
        test_db.add(job)
        await test_db.commit()

        response = await authenticated_client.get("/api/v1/jobs/failed-job-101")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "FAILURE"
        assert data["error_message"] is not None
        assert "rate limit" in data["error_message"].lower()

    # ============================================
    # POST /api/v1/analysis/analyze/{bid_id} 테스트
    # Job 생성 (분석 요청 → job_id 반환)
    # ============================================

    @pytest.mark.asyncio
    async def test_analyze_bid_unauthenticated(self, async_client: AsyncClient):
        """미인증 시 401"""
        response = await async_client.post("/api/v1/analysis/analyze/1")

        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_analyze_bid_not_found(self, authenticated_client: AsyncClient):
        """존재하지 않는 공고 - 404"""
        response = await authenticated_client.post("/api/v1/analysis/analyze/99999")

        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_analyze_bid_invalid_id(self, authenticated_client: AsyncClient):
        """잘못된 ID - 422"""
        response = await authenticated_client.post("/api/v1/analysis/analyze/0")

        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_analyze_bid_success(
        self, authenticated_client: AsyncClient, sample_bid
    ):
        """
        분석 요청 성공 - 202 Accepted + job_id 반환

        Note: This test requires taskiq to be installed for the actual
        background task processing. If taskiq is not available, we skip
        the test as the endpoint will fail on import.
        """
        # Check if taskiq is available
        try:
            import taskiq  # noqa: F401
        except ImportError:
            pytest.skip("taskiq not installed - required for background tasks")

        response = await authenticated_client.post(
            f"/api/v1/analysis/analyze/{sample_bid.id}"
        )

        assert response.status_code == 202
        data = response.json()

        # Verify job_id is returned
        assert "job_id" in data
        assert data["job_id"] is not None
        assert len(data["job_id"]) > 0

        # Verify status is PENDING
        assert data["status"] == "PENDING"


class TestJobPollingPattern:
    """Job+Polling 패턴 통합 테스트"""

    @pytest.mark.asyncio
    async def test_job_lifecycle_pending_to_success(
        self, authenticated_client: AsyncClient, test_db: AsyncSession, test_user
    ):
        """Job 상태 전이 테스트: PENDING → PROCESSING → SUCCESS"""
        from datetime import datetime, timedelta

        from app.db.models import Job

        # 1. Create PENDING job
        job = Job(
            id="lifecycle-test-001",
            user_id=test_user.id,
            task_type="test_task",
            status="PENDING",
            progress=0,
            expires_at=datetime.utcnow() + timedelta(days=7),
        )
        test_db.add(job)
        await test_db.commit()

        # Verify PENDING state
        response = await authenticated_client.get("/api/v1/jobs/lifecycle-test-001")
        assert response.json()["status"] == "PENDING"
        assert response.json()["progress"] == 0

        # 2. Simulate job starting (PROCESSING)
        job.status = "PROCESSING"
        job.progress = 25
        job.started_at = datetime.utcnow()
        await test_db.commit()
        await test_db.refresh(job)

        response = await authenticated_client.get("/api/v1/jobs/lifecycle-test-001")
        assert response.json()["status"] == "PROCESSING"
        assert response.json()["progress"] == 25

        # 3. Simulate job completion (SUCCESS)
        job.status = "SUCCESS"
        job.progress = 100
        job.result = {"summary": "Analysis complete"}
        job.completed_at = datetime.utcnow()
        await test_db.commit()
        await test_db.refresh(job)

        response = await authenticated_client.get("/api/v1/jobs/lifecycle-test-001")
        data = response.json()
        assert data["status"] == "SUCCESS"
        assert data["progress"] == 100
        assert data["result"]["summary"] == "Analysis complete"

    @pytest.mark.asyncio
    async def test_job_response_schema(
        self, authenticated_client: AsyncClient, test_db: AsyncSession, test_user
    ):
        """JobResponse 스키마 검증"""
        from datetime import datetime, timedelta

        from app.db.models import Job

        job = Job(
            id="schema-test-001",
            user_id=test_user.id,
            task_type="rag_analysis",
            status="PROCESSING",
            progress=50,
            input_data={"bid_id": 123},
            started_at=datetime.utcnow() - timedelta(minutes=1),
            expires_at=datetime.utcnow() + timedelta(days=7),
        )
        test_db.add(job)
        await test_db.commit()

        response = await authenticated_client.get("/api/v1/jobs/schema-test-001")

        assert response.status_code == 200
        data = response.json()

        # Verify all expected fields exist
        assert "id" in data
        assert "status" in data
        assert "task_type" in data
        assert "progress" in data
        assert "created_at" in data

        # Verify optional fields
        assert "input_data" in data
        assert "result" in data  # Can be null
        assert "error_message" in data  # Can be null
        assert "started_at" in data
        assert "completed_at" in data  # Can be null
