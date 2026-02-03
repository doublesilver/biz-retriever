"""
GET /api/profile/licenses - List all licenses
POST /api/profile/licenses - Add new license
DELETE /api/profile/licenses/[id] - Delete license
"""
from http.server import BaseHTTPRequestHandler
import sys
from pathlib import Path
import asyncio
import re

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from lib.utils import send_json, send_error, handle_cors_preflight, parse_json_body
from lib.auth import require_auth
from lib.db import get_db
from app.services.profile_service import profile_service
from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime


class LicenseCreateRequest(BaseModel):
    """License creation request schema"""
    license_name: str = Field(..., min_length=1, max_length=200)
    license_number: Optional[str] = Field(None, max_length=100)
    issue_date: Optional[str] = Field(None)  # ISO format date string


class handler(BaseHTTPRequestHandler):
    def do_OPTIONS(self):
        """CORS preflight 처리"""
        if handle_cors_preflight(self):
            return
    
    def do_GET(self):
        """List all licenses for current user"""
        try:
            # 1. 인증 체크
            user_payload = require_auth(self)
            if not user_payload:
                return  # 이미 401 응답 전송됨
            
            # 2. 비동기 처리
            result = asyncio.run(self.list_licenses(user_payload))
            
            # 3. 응답
            send_json(self, 200, result)
            
        except Exception as e:
            send_error(self, 500, f"Internal server error: {str(e)}")
    
    def do_POST(self):
        """Add new license"""
        try:
            # 1. 인증 체크
            user_payload = require_auth(self)
            if not user_payload:
                return  # 이미 401 응답 전송됨
            
            # 2. 요청 body 파싱
            license_data = parse_json_body(self, LicenseCreateRequest)
            if not license_data:
                return  # 이미 에러 응답 전송됨
            
            # 3. 비동기 처리
            result = asyncio.run(self.create_license(user_payload, license_data))
            
            # 4. 응답
            send_json(self, 201, result)
            
        except Exception as e:
            send_error(self, 500, f"Internal server error: {str(e)}")
    
    def do_DELETE(self):
        """Delete license by ID"""
        try:
            # 1. 인증 체크
            user_payload = require_auth(self)
            if not user_payload:
                return  # 이미 401 응답 전송됨
            
            # 2. Extract license_id from path
            # Path format: /api/profile/licenses/123
            match = re.match(r'/api/profile/licenses/(\d+)', self.path)
            if not match:
                send_error(self, 400, "Invalid path format. Expected: /api/profile/licenses/{id}")
                return
            
            license_id = int(match.group(1))
            
            # 3. 비동기 처리
            result = asyncio.run(self.delete_license(user_payload, license_id))
            
            # 4. 응답
            if result:
                send_json(self, 200, {"message": "License deleted successfully"})
            else:
                send_error(self, 404, "License not found or access denied")
            
        except ValueError:
            send_error(self, 400, "Invalid license ID")
        except Exception as e:
            send_error(self, 500, f"Internal server error: {str(e)}")
    
    async def list_licenses(self, user_payload: dict):
        """사용자 면허 목록 조회"""
        async for db in get_db():
            user_id = user_payload.get("user_id")
            
            # Get or create profile
            profile = await profile_service.get_or_create_profile(db, user_id)
            
            # Return licenses
            return {
                "licenses": [
                    {
                        "id": lic.id,
                        "license_name": lic.license_name,
                        "license_number": lic.license_number,
                        "issue_date": lic.issue_date.isoformat() if lic.issue_date else None,
                        "created_at": lic.created_at.isoformat(),
                    }
                    for lic in profile.licenses
                ]
            }
    
    async def create_license(self, user_payload: dict, license_data: LicenseCreateRequest):
        """면허 추가"""
        async for db in get_db():
            user_id = user_payload.get("user_id")
            
            # Get or create profile
            profile = await profile_service.get_or_create_profile(db, user_id)
            
            # Parse issue_date if provided
            issue_date = None
            if license_data.issue_date:
                try:
                    issue_date = datetime.fromisoformat(license_data.issue_date.replace('Z', '+00:00'))
                except ValueError:
                    raise ValueError("Invalid date format. Expected ISO 8601 format (YYYY-MM-DD)")
            
            # Create license
            license_dict = {
                "license_name": license_data.license_name,
                "license_number": license_data.license_number,
                "issue_date": issue_date,
            }
            
            new_license = await profile_service.add_license(db, profile.id, license_dict)
            
            # Return created license
            return {
                "id": new_license.id,
                "license_name": new_license.license_name,
                "license_number": new_license.license_number,
                "issue_date": new_license.issue_date.isoformat() if new_license.issue_date else None,
                "created_at": new_license.created_at.isoformat(),
            }
    
    async def delete_license(self, user_payload: dict, license_id: int) -> bool:
        """면허 삭제"""
        async for db in get_db():
            user_id = user_payload.get("user_id")
            
            # Get or create profile
            profile = await profile_service.get_or_create_profile(db, user_id)
            
            # Delete license (service checks ownership)
            return await profile_service.delete_license(db, profile.id, license_id)
