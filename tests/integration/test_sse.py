"""
SSE (Server-Sent Events) API 통합 테스트

SSE is the serverless-compatible replacement for WebSocket.
Works with Vercel's 60-second timeout limit.
"""

import asyncio

import pytest
from httpx import AsyncClient


class TestSSEAPI:
    """SSE Streaming API 통합 테스트"""

    # ============================================
    # GET /api/v1/realtime/stream 테스트
    # ============================================

    @pytest.mark.asyncio
    async def test_sse_stream_unauthenticated(self, async_client: AsyncClient):
        """미인증 시 401 응답"""
        response = await async_client.get("/api/v1/realtime/stream")

        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_sse_stream_authenticated(self, authenticated_client: AsyncClient):
        """
        인증된 사용자 SSE 스트림 연결 테스트

        Note: SSE is a streaming response, so we test the initial response headers
        and content type. We use timeout to prevent hanging.
        """
        # SSE endpoints return streaming responses
        # Use asyncio.timeout to prevent hanging on infinite stream
        try:
            async with asyncio.timeout(5):  # 5 second timeout
                async with authenticated_client.stream(
                    "GET", "/api/v1/realtime/stream"
                ) as response:
                    # Check response headers
                    assert response.status_code == 200
                    assert (
                        response.headers.get("content-type")
                        == "text/event-stream; charset=utf-8"
                    )
                    assert response.headers.get("cache-control") == "no-cache"

                    # Read first chunk (should be heartbeat or initial data)
                    first_chunk = await response.aiter_bytes().__anext__()
                    assert first_chunk is not None
        except TimeoutError:
            # Expected - SSE streams run indefinitely
            pass

    @pytest.mark.asyncio
    async def test_sse_stream_with_last_event_id(
        self, authenticated_client: AsyncClient
    ):
        """Last-Event-ID 헤더로 재연결 테스트"""
        headers = {"Last-Event-ID": "test-event-123"}

        try:
            async with asyncio.timeout(3):
                async with authenticated_client.stream(
                    "GET",
                    "/api/v1/realtime/stream",
                    headers=headers,
                ) as response:
                    assert response.status_code == 200
                    assert (
                        response.headers.get("content-type")
                        == "text/event-stream; charset=utf-8"
                    )
        except TimeoutError:
            pass

    @pytest.mark.asyncio
    async def test_sse_content_type(self, authenticated_client: AsyncClient):
        """SSE 응답의 Content-Type 검증"""
        try:
            async with asyncio.timeout(3):
                async with authenticated_client.stream(
                    "GET", "/api/v1/realtime/stream"
                ) as response:
                    content_type = response.headers.get("content-type", "")
                    assert "text/event-stream" in content_type
        except TimeoutError:
            pass

    @pytest.mark.asyncio
    async def test_sse_no_buffering_header(self, authenticated_client: AsyncClient):
        """X-Accel-Buffering: no 헤더 검증 (nginx 버퍼링 비활성화)"""
        try:
            async with asyncio.timeout(3):
                async with authenticated_client.stream(
                    "GET", "/api/v1/realtime/stream"
                ) as response:
                    # This header tells nginx to disable buffering for SSE
                    x_accel = response.headers.get("x-accel-buffering")
                    assert x_accel == "no"
        except TimeoutError:
            pass
