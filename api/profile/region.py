"""
GET /api/profile/region - Get region_code
PUT /api/profile/region - Update region_code
"""
from http.server import BaseHTTPRequestHandler
import sys
from pathlib import Path
import asyncio

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from lib.utils import send_json, send_error, handle_cors_preflight, parse_json_body
from lib.auth import require_auth
from lib.db import get_db
from app.services.profile_service import profile_service
from pydantic import BaseModel, Field


class RegionUpdateRequest(BaseModel):
    """Region update request schema"""
    location_code: str = Field(..., min_length=2, max_length=10)


class handler(BaseHTTPRequestHandler):
    def do_OPTIONS(self):
        """CORS preflight 처리"""
        if handle_cors_preflight(self):
            return
    
    def do_GET(self):
        """Get region_code for current user"""
        try:
            # 1. 인증 체크
            user_payload = require_auth(self)
            if not user_payload:
                return  # 이미 401 응답 전송됨
            
            # 2. 비동기 처리
            result = asyncio.run(self.get_region(user_payload))
            
            # 3. 응답
            send_json(self, 200, result)
            
        except Exception as e:
            send_error(self, 500, f"Internal server error: {str(e)}")
    
    def do_PUT(self):
        """Update region_code"""
        try:
            # 1. 인증 체크
            user_payload = require_auth(self)
            if not user_payload:
                return  # 이미 401 응답 전송됨
            
            # 2. 요청 body 파싱
            region_data = parse_json_body(self, RegionUpdateRequest)
            if not region_data:
                return  # 이미 에러 응답 전송됨
            
            # 3. 비동기 처리
            result = asyncio.run(self.update_region(user_payload, region_data))
            
            # 4. 응답
            send_json(self, 200, result)
            
        except Exception as e:
            send_error(self, 500, f"Internal server error: {str(e)}")
    
    async def get_region(self, user_payload: dict):
        """지역 코드 조회"""
        async for db in get_db():
            user_id = user_payload.get("user_id")
            
            # Get or create profile
            profile = await profile_service.get_or_create_profile(db, user_id)
            
            # Return region code
            return {
                "location_code": profile.location_code,
                "address": profile.address,
            }
    
    async def update_region(self, user_payload: dict, region_data: RegionUpdateRequest):
        """지역 코드 업데이트"""
        async for db in get_db():
            user_id = user_payload.get("user_id")
            
            # Update profile with new location_code
            profile = await profile_service.create_or_update_profile(
                db, user_id, {"location_code": region_data.location_code}
            )
            
            # Return updated region
            return {
                "location_code": profile.location_code,
                "address": profile.address,
                "updated_at": profile.updated_at.isoformat(),
            }
