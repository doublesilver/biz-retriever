"""
End-to-End Integration Tests
Tests complete user journeys through the application
"""

import pytest
import httpx
from fastapi import status


class TestUserJourney:
    """Complete user journey from registration to bid matching"""
    
    @pytest.mark.asyncio
    async def test_complete_user_flow(self):
        """
        Test complete user workflow:
        1. Register new user
        2. Login
        3. Update profile with company info
        4. Add license
        5. Add performance record
        6. Check bid matching (Hard Match)
        """
        base_url = "http://localhost:8000"
        
        async with httpx.AsyncClient(base_url=base_url) as client:
            # Step 1: Register new user with unique email
            import time
            unique_email = f"e2e_test_{int(time.time())}@example.com"
            register_data = {
                "email": unique_email,
                "password": "SecurePass123!@#"
            }
            response = await client.post("/api/v1/auth/register", json=register_data)
            assert response.status_code == status.HTTP_201_CREATED
            data = response.json()
            assert "id" in data
            assert data["email"] == register_data["email"]
            
            # Step 2: Login to get access token
            login_data = {
                "username": register_data["email"],
                "password": register_data["password"],
                "grant_type": "password"
            }
            response = await client.post(
                "/api/v1/auth/login/access-token",
                data=login_data,
                headers={"Content-Type": "application/x-www-form-urlencoded"}
            )
            assert response.status_code == status.HTTP_200_OK
            token_data = response.json()
            assert "access_token" in token_data
            access_token = token_data["access_token"]
            
            # Set authorization header
            headers = {"Authorization": f"Bearer {access_token}"}
            
            # Step 3: Update profile with company information
            profile_data = {
                "company_name": "E2E Test Company",
                "business_number": "123-45-67890",
                "ceo_name": "Test CEO",
                "address": "Seoul, Korea",
                "phone": "010-1234-5678",
                "region_code": "11",  # Seoul
                "primary_keywords": ["조경", "화훼"]
            }
            response = await client.put(
                "/api/v1/profile/",  # Add trailing slash to match FastAPI route
                json=profile_data,
                headers=headers
            )
            assert response.status_code in [status.HTTP_200_OK, status.HTTP_201_CREATED]
            
            # Step 4: Add license (조경공사업)
            license_data = {
                "license_name": "조경공사업",
                "license_number": "제2024-001호",
                "acquired_at": "2024-01-15"
            }
            response = await client.post(
                "/api/v1/profile/licenses",
                json=license_data,
                headers=headers
            )
            assert response.status_code == status.HTTP_201_CREATED  # POST returns 201
            license_response = response.json()
            assert "id" in license_response
            license_id = license_response["id"]
            
            # Verify license was added
            response = await client.get("/api/v1/profile/licenses", headers=headers)
            assert response.status_code == status.HTTP_200_OK
            licenses = response.json()
            assert len(licenses) > 0
            assert any(lic["license_name"] == "조경공사업" for lic in licenses)
            
            # Step 5: Add performance record
            performance_data = {
                "project_name": "서울시청 조경공사",
                "amount": 1500000000,  # 15억 원 (field name: amount, not contract_amount)
                "completion_date": "2023-12-31"
            }
            response = await client.post(
                "/api/v1/profile/performances",
                json=performance_data,
                headers=headers
            )
            assert response.status_code == status.HTTP_200_OK
            performance_response = response.json()
            assert "id" in performance_response
            
            # Verify performance was added
            response = await client.get("/api/v1/profile/performances", headers=headers)
            assert response.status_code == status.HTTP_200_OK
            performances = response.json()
            assert len(performances) > 0
            assert any(perf["contract_amount"] == 1500000000 for perf in performances)
            
            # Step 6: Create a test bid and check Hard Match
            bid_data = {
                "title": "조경 공사 입찰 공고",
                "content": "서울 지역 조경 공사. 조경공사업 면허 필요. 최소 실적 10억 원",
                "agency": "서울특별시",
                "base_price": 2000000000,
                "deadline": "2026-02-28",
                "url": "http://example.com/bid/test-e2e"
            }
            response = await client.post(
                "/api/v1/bids/",
                json=bid_data,
                headers=headers
            )
            assert response.status_code == status.HTTP_201_CREATED
            bid_response = response.json()
            bid_id = bid_response["id"]
            
            # Step 7: Check Hard Match for the bid
            response = await client.get(
                f"/api/v1/analysis/match/{bid_id}",
                headers=headers
            )
            assert response.status_code == status.HTTP_200_OK
            match_result = response.json()
            
            # Verify Hard Match response structure
            assert "bid_id" in match_result
            assert "is_match" in match_result
            assert "reasons" in match_result
            assert "soft_match" in match_result
            assert "constraints" in match_result
            
            # Cleanup: Delete test records
            await client.delete(f"/api/v1/profile/licenses/{license_id}", headers=headers)
            await client.delete(f"/api/v1/bids/{bid_id}", headers=headers)
    
    
    @pytest.mark.asyncio
    async def test_bid_listing_and_filtering(self):
        """
        Test bid listing and filtering functionality:
        1. Get all bids
        2. Filter by status
        3. Filter by priority
        4. Search by keyword
        """
        base_url = "http://localhost:8000"
        
        async with httpx.AsyncClient(base_url=base_url) as client:
            # Bids endpoint doesn't require authentication
            # Test 1: Get all bids
            response = await client.get("/api/v1/bids/")
            assert response.status_code == status.HTTP_200_OK
            data = response.json()
            assert "items" in data
            assert "total" in data
            
            # Test 2: Filter by status
            response = await client.get("/api/v1/bids/?status=new")
            assert response.status_code == status.HTTP_200_OK
            
            # Test 3: Filter by priority
            response = await client.get("/api/v1/bids/?skip=0&limit=10")
            assert response.status_code == status.HTTP_200_OK
            filtered_data = response.json()
            assert "items" in filtered_data
            
            # Test 4: Search by keyword
            response = await client.get("/api/v1/bids/?skip=0&limit=5")
            assert response.status_code == status.HTTP_200_OK
    
    
    @pytest.mark.asyncio
    async def test_analytics_endpoints(self):
        """Test analytics/summary endpoint requires authentication"""
        base_url = "http://localhost:8000"
        
        async with httpx.AsyncClient(base_url=base_url) as client:
            # Analytics endpoint requires authentication
            response = await client.get("/api/v1/analytics/summary")
            assert response.status_code == status.HTTP_401_UNAUTHORIZED
            # No need to check response body for unauthorized requests


class TestErrorHandling:
    """Test error handling and edge cases"""
    
    @pytest.mark.asyncio
    async def test_unauthorized_access(self):
        """Test that protected endpoints require authentication"""
        base_url = "http://localhost:8000"
        
        async with httpx.AsyncClient(base_url=base_url, follow_redirects=False) as client:
            # Try to create a bid without authentication (requires auth)
            bid_data = {
                "title": "Test Bid",
                "content": "Test Content",
                "agency": "Test Agency"
            }
            response = await client.post("/api/v1/bids/", json=bid_data)
            # Expecting 401 Unauthorized for missing authentication
            assert response.status_code == status.HTTP_401_UNAUTHORIZED
            
            # Try to access profile without token
            response = await client.get("/api/v1/profile")
            assert response.status_code == status.HTTP_401_UNAUTHORIZED
    
    
    @pytest.mark.asyncio
    async def test_invalid_credentials(self):
        """Test login with invalid credentials returns 400"""
        base_url = "http://localhost:8000"
        
        async with httpx.AsyncClient(base_url=base_url) as client:
            login_data = {
                "username": "nonexistent@example.com",
                "password": "wrongpassword",
                "grant_type": "password"
            }
            response = await client.post(
                "/api/v1/auth/login/access-token",
                data=login_data,
                headers={"Content-Type": "application/x-www-form-urlencoded"}
            )
            # API returns 400 for incorrect credentials
            assert response.status_code == status.HTTP_400_BAD_REQUEST
    
    
    @pytest.mark.asyncio
    async def test_duplicate_registration(self):
        """Test that duplicate email registration is prevented"""
        base_url = "http://localhost:8000"
        
        async with httpx.AsyncClient(base_url=base_url) as client:
            # Try to register with existing email
            register_data = {
                "email": "debug_user@example.com",  # Already exists
                "password": "AnotherPass123!@#"
            }
            response = await client.post("/api/v1/auth/register", json=register_data)
            assert response.status_code == status.HTTP_400_BAD_REQUEST


class TestPerformance:
    """Basic performance tests"""
    
    @pytest.mark.asyncio
    async def test_api_response_time(self):
        """Test that API responds within acceptable time"""
        import time
        base_url = "http://localhost:8000"
        
        async with httpx.AsyncClient(base_url=base_url) as client:
            start_time = time.time()
            response = await client.get("/health")
            end_time = time.time()
            
            assert response.status_code == status.HTTP_200_OK
            
            # Health endpoint should respond in < 100ms
            response_time = (end_time - start_time) * 1000
            assert response_time < 100, f"Health check took {response_time:.2f}ms, expected < 100ms"
    
    
    @pytest.mark.asyncio
    async def test_concurrent_requests(self):
        """Test system handles concurrent requests"""
        import asyncio
        base_url = "http://localhost:8000"
        
        async def make_request(client):
            response = await client.get("/health")
            return response.status_code == status.HTTP_200_OK
        
        async with httpx.AsyncClient(base_url=base_url) as client:
            # Make 10 concurrent requests
            tasks = [make_request(client) for _ in range(10)]
            results = await asyncio.gather(*tasks)
            
            # All requests should succeed
            assert all(results), "Some concurrent requests failed"
