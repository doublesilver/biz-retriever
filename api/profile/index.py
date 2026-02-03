"""
GET /api/profile - Get user profile
PUT /api/profile - Update user profile
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
from typing import Optional


class ProfileUpdateRequest(BaseModel):
    """Profile update request schema"""
    company_name: Optional[str] = Field(None, max_length=200)
    brn: Optional[str] = Field(None, max_length=20)
    representative: Optional[str] = Field(None, max_length=100)
    address: Optional[str] = Field(None, max_length=500)
    location_code: Optional[str] = Field(None, max_length=10)
    company_type: Optional[str] = Field(None, max_length=100)
    credit_rating: Optional[str] = Field(None, max_length=10)
    employee_count: Optional[int] = Field(None, ge=0)
    founding_year: Optional[int] = Field(None, ge=1900, le=2100)
    main_bank: Optional[str] = Field(None, max_length=100)


class handler(BaseHTTPRequestHandler):
    def do_OPTIONS(self):
        """CORS preflight 처리"""
        if handle_cors_preflight(self):
            return
    
    def do_GET(self):
        """Get user profile with all relations"""
        try:
            # 1. 인증 체크
            user_payload = require_auth(self)
            if not user_payload:
                return  # 이미 401 응답 전송됨
            
            # 2. 비동기 처리
            result = asyncio.run(self.get_profile(user_payload))
            
            # 3. 응답
            send_json(self, 200, result)
            
        except Exception as e:
            send_error(self, 500, f"Internal server error: {str(e)}")
    
    def do_PUT(self):
        """Update user profile"""
        try:
            # 1. 인증 체크
            user_payload = require_auth(self)
            if not user_payload:
                return  # 이미 401 응답 전송됨
            
            # 2. 요청 body 파싱
            update_data = parse_json_body(self, ProfileUpdateRequest)
            if not update_data:
                return  # 이미 에러 응답 전송됨
            
            # 3. 비동기 처리
            result = asyncio.run(self.update_profile(user_payload, update_data))
            
            # 4. 응답
            send_json(self, 200, result)
            
        except Exception as e:
            send_error(self, 500, f"Internal server error: {str(e)}")
    
    async def get_profile(self, user_payload: dict):
        """사용자 프로필 조회"""
        async for db in get_db():
            user_id = user_payload.get("user_id")
            
            # Get or create profile
            profile = await profile_service.get_or_create_profile(db, user_id)
            
            # Build response with all relations
            return {
                "id": profile.id,
                "user_id": profile.user_id,
                "company_name": profile.company_name,
                "brn": profile.brn,
                "representative": profile.representative,
                "address": profile.address,
                "location_code": profile.location_code,
                "company_type": profile.company_type,
                "credit_rating": profile.credit_rating,
                "employee_count": profile.employee_count,
                "founding_year": profile.founding_year,
                "main_bank": profile.main_bank,
                "keywords": profile.keywords or [],
                "standard_industry_codes": profile.standard_industry_codes or [],
                "slack_webhook_url": profile.slack_webhook_url,
                "is_email_enabled": profile.is_email_enabled,
                "is_slack_enabled": profile.is_slack_enabled,
                "licenses": [
                    {
                        "id": lic.id,
                        "license_name": lic.license_name,
                        "license_number": lic.license_number,
                        "issue_date": lic.issue_date.isoformat() if lic.issue_date else None,
                    }
                    for lic in profile.licenses
                ],
                "performances": [
                    {
                        "id": perf.id,
                        "project_name": perf.project_name,
                        "amount": perf.amount,
                        "completion_date": perf.completion_date.isoformat() if perf.completion_date else None,
                    }
                    for perf in profile.performances
                ],
                "created_at": profile.created_at.isoformat(),
                "updated_at": profile.updated_at.isoformat(),
            }
    
    async def update_profile(self, user_payload: dict, update_data: ProfileUpdateRequest):
        """사용자 프로필 업데이트"""
        async for db in get_db():
            user_id = user_payload.get("user_id")
            
            # Filter out None values
            profile_data = {
                k: v for k, v in update_data.model_dump().items() if v is not None
            }
            
            # Update profile
            profile = await profile_service.create_or_update_profile(
                db, user_id, profile_data
            )
            
            # Return updated profile
            return {
                "id": profile.id,
                "user_id": profile.user_id,
                "company_name": profile.company_name,
                "brn": profile.brn,
                "representative": profile.representative,
                "address": profile.address,
                "location_code": profile.location_code,
                "company_type": profile.company_type,
                "credit_rating": profile.credit_rating,
                "employee_count": profile.employee_count,
                "founding_year": profile.founding_year,
                "main_bank": profile.main_bank,
                "updated_at": profile.updated_at.isoformat(),
            }
