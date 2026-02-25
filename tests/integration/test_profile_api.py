"""
Profile API 통합 테스트
- GET /api/v1/profile/ (조회)
- PUT /api/v1/profile/ (수정)
- POST/GET/DELETE /api/v1/profile/licenses
- POST/GET/DELETE /api/v1/profile/performances
"""

from httpx import AsyncClient


class TestGetProfile:
    """프로필 조회"""

    async def test_unauthenticated(self, async_client: AsyncClient):
        response = await async_client.get("/api/v1/profile/")
        assert response.status_code == 401

    async def test_no_profile(self, authenticated_client: AsyncClient):
        response = await authenticated_client.get("/api/v1/profile/")
        assert response.status_code == 200
        data = response.json()
        assert data["id"] is None

    async def test_with_profile(self, authenticated_profile_client: AsyncClient):
        response = await authenticated_profile_client.get("/api/v1/profile/")
        assert response.status_code == 200
        data = response.json()
        assert data["company_name"] == "테스트 기업"
        assert data["brn"] == "123-45-67890"
        assert len(data["licenses"]) >= 1
        assert len(data["performances"]) >= 1


class TestUpdateProfile:
    """프로필 수정"""

    async def test_unauthenticated(self, async_client: AsyncClient):
        response = await async_client.put(
            "/api/v1/profile/",
            json={"company_name": "새 기업"},
        )
        assert response.status_code == 401

    async def test_update_creates_profile(self, authenticated_client: AsyncClient):
        response = await authenticated_client.put(
            "/api/v1/profile/",
            json={"company_name": "신규 기업", "representative": "홍길동"},
        )
        assert response.status_code == 200

    async def test_update_existing(self, authenticated_profile_client: AsyncClient):
        response = await authenticated_profile_client.put(
            "/api/v1/profile/",
            json={"company_name": "업데이트 기업"},
        )
        assert response.status_code == 200


class TestLicenses:
    """면허 관리"""

    async def test_get_empty(self, authenticated_client: AsyncClient):
        response = await authenticated_client.get("/api/v1/profile/licenses")
        assert response.status_code == 200
        assert response.json() == []

    async def test_add_license(self, authenticated_profile_client: AsyncClient):
        response = await authenticated_profile_client.post(
            "/api/v1/profile/licenses",
            json={"license_name": "건축공사업", "license_number": "제2026-001호"},
        )
        assert response.status_code == 201

    async def test_get_licenses(self, authenticated_profile_client: AsyncClient):
        response = await authenticated_profile_client.get("/api/v1/profile/licenses")
        assert response.status_code == 200
        data = response.json()
        assert len(data) >= 1

    async def test_delete_nonexistent(self, authenticated_profile_client: AsyncClient):
        response = await authenticated_profile_client.delete("/api/v1/profile/licenses/99999")
        assert response.status_code == 404

    async def test_add_and_delete_license(self, authenticated_profile_client: AsyncClient):
        """면허 추가 후 삭제 성공"""
        create_resp = await authenticated_profile_client.post(
            "/api/v1/profile/licenses",
            json={"license_name": "전기공사업", "license_number": "제2026-DEL호"},
        )
        assert create_resp.status_code == 201
        license_id = create_resp.json()["id"]

        delete_resp = await authenticated_profile_client.delete(f"/api/v1/profile/licenses/{license_id}")
        assert delete_resp.status_code == 204

    async def test_unauthenticated_add(self, async_client: AsyncClient):
        response = await async_client.post(
            "/api/v1/profile/licenses",
            json={"license_name": "테스트", "license_number": "제001호"},
        )
        assert response.status_code == 401

    async def test_unauthenticated_delete(self, async_client: AsyncClient):
        response = await async_client.delete("/api/v1/profile/licenses/1")
        assert response.status_code == 401


class TestPerformances:
    """실적 관리"""

    async def test_get_empty(self, authenticated_client: AsyncClient):
        response = await authenticated_client.get("/api/v1/profile/performances")
        assert response.status_code == 200
        assert response.json() == []

    async def test_add_performance(self, authenticated_profile_client: AsyncClient):
        response = await authenticated_profile_client.post(
            "/api/v1/profile/performances",
            json={"project_name": "조경 공사", "amount": 500000000},
        )
        assert response.status_code == 201

    async def test_get_performances(self, authenticated_profile_client: AsyncClient):
        response = await authenticated_profile_client.get("/api/v1/profile/performances")
        assert response.status_code == 200
        data = response.json()
        assert len(data) >= 1

    async def test_delete_nonexistent(self, authenticated_profile_client: AsyncClient):
        response = await authenticated_profile_client.delete("/api/v1/profile/performances/99999")
        assert response.status_code == 404

    async def test_add_and_delete_performance(self, authenticated_profile_client: AsyncClient):
        """실적 추가 후 삭제 성공"""
        create_resp = await authenticated_profile_client.post(
            "/api/v1/profile/performances",
            json={"project_name": "삭제 대상 공사", "amount": 200000000},
        )
        assert create_resp.status_code == 201
        perf_id = create_resp.json()["id"]

        delete_resp = await authenticated_profile_client.delete(f"/api/v1/profile/performances/{perf_id}")
        assert delete_resp.status_code == 204

    async def test_unauthenticated_add(self, async_client: AsyncClient):
        response = await async_client.post(
            "/api/v1/profile/performances",
            json={"project_name": "테스트", "amount": 100000},
        )
        assert response.status_code == 401

    async def test_unauthenticated_delete(self, async_client: AsyncClient):
        response = await async_client.delete("/api/v1/profile/performances/1")
        assert response.status_code == 401


class TestUploadCertificate:
    """사업자등록증 업로드"""

    async def test_unauthenticated(self, async_client: AsyncClient):
        response = await async_client.post("/api/v1/profile/upload-certificate")
        assert response.status_code in [401, 422]

    async def test_invalid_file_type(self, authenticated_client: AsyncClient):
        """지원하지 않는 파일 형식"""
        files = {"file": ("test.txt", b"plain text", "text/plain")}
        response = await authenticated_client.post(
            "/api/v1/profile/upload-certificate",
            files=files,
        )
        assert response.status_code == 400
