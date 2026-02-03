"""
GET /api/profile/performances - List all performances
POST /api/profile/performances - Add new performance
DELETE /api/profile/performances/[id] - Delete performance
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


class PerformanceCreateRequest(BaseModel):
    """Performance creation request schema"""
    project_name: str = Field(..., min_length=1, max_length=500)
    amount: float = Field(..., ge=0)
    completion_date: Optional[str] = Field(None)  # ISO format date string


class handler(BaseHTTPRequestHandler):
    def do_OPTIONS(self):
        """CORS preflight 처리"""
        if handle_cors_preflight(self):
            return
    
    def do_GET(self):
        """List all performances for current user"""
        try:
            # 1. 인증 체크
            user_payload = require_auth(self)
            if not user_payload:
                return  # 이미 401 응답 전송됨
            
            # 2. 비동기 처리
            result = asyncio.run(self.list_performances(user_payload))
            
            # 3. 응답
            send_json(self, 200, result)
            
        except Exception as e:
            send_error(self, 500, f"Internal server error: {str(e)}")
    
    def do_POST(self):
        """Add new performance"""
        try:
            # 1. 인증 체크
            user_payload = require_auth(self)
            if not user_payload:
                return  # 이미 401 응답 전송됨
            
            # 2. 요청 body 파싱
            performance_data = parse_json_body(self, PerformanceCreateRequest)
            if not performance_data:
                return  # 이미 에러 응답 전송됨
            
            # 3. 비동기 처리
            result = asyncio.run(self.create_performance(user_payload, performance_data))
            
            # 4. 응답
            send_json(self, 201, result)
            
        except Exception as e:
            send_error(self, 500, f"Internal server error: {str(e)}")
    
    def do_DELETE(self):
        """Delete performance by ID"""
        try:
            # 1. 인증 체크
            user_payload = require_auth(self)
            if not user_payload:
                return  # 이미 401 응답 전송됨
            
            # 2. Extract performance_id from path
            # Path format: /api/profile/performances/123
            match = re.match(r'/api/profile/performances/(\d+)', self.path)
            if not match:
                send_error(self, 400, "Invalid path format. Expected: /api/profile/performances/{id}")
                return
            
            performance_id = int(match.group(1))
            
            # 3. 비동기 처리
            result = asyncio.run(self.delete_performance(user_payload, performance_id))
            
            # 4. 응답
            if result:
                send_json(self, 200, {"message": "Performance deleted successfully"})
            else:
                send_error(self, 404, "Performance not found or access denied")
            
        except ValueError:
            send_error(self, 400, "Invalid performance ID")
        except Exception as e:
            send_error(self, 500, f"Internal server error: {str(e)}")
    
    async def list_performances(self, user_payload: dict):
        """사용자 실적 목록 조회"""
        async for db in get_db():
            user_id = user_payload.get("user_id")
            
            # Get or create profile
            profile = await profile_service.get_or_create_profile(db, user_id)
            
            # Return performances
            return {
                "performances": [
                    {
                        "id": perf.id,
                        "project_name": perf.project_name,
                        "amount": perf.amount,
                        "completion_date": perf.completion_date.isoformat() if perf.completion_date else None,
                        "created_at": perf.created_at.isoformat(),
                    }
                    for perf in profile.performances
                ]
            }
    
    async def create_performance(self, user_payload: dict, performance_data: PerformanceCreateRequest):
        """실적 추가"""
        async for db in get_db():
            user_id = user_payload.get("user_id")
            
            # Get or create profile
            profile = await profile_service.get_or_create_profile(db, user_id)
            
            # Parse completion_date if provided
            completion_date = None
            if performance_data.completion_date:
                try:
                    completion_date = datetime.fromisoformat(performance_data.completion_date.replace('Z', '+00:00'))
                except ValueError:
                    raise ValueError("Invalid date format. Expected ISO 8601 format (YYYY-MM-DD)")
            
            # Create performance
            performance_dict = {
                "project_name": performance_data.project_name,
                "amount": performance_data.amount,
                "completion_date": completion_date,
            }
            
            new_performance = await profile_service.add_performance(db, profile.id, performance_dict)
            
            # Return created performance
            return {
                "id": new_performance.id,
                "project_name": new_performance.project_name,
                "amount": new_performance.amount,
                "completion_date": new_performance.completion_date.isoformat() if new_performance.completion_date else None,
                "created_at": new_performance.created_at.isoformat(),
            }
    
    async def delete_performance(self, user_payload: dict, performance_id: int) -> bool:
        """실적 삭제"""
        async for db in get_db():
            user_id = user_payload.get("user_id")
            
            # Get or create profile
            profile = await profile_service.get_or_create_profile(db, user_id)
            
            # Delete performance (service checks ownership)
            return await profile_service.delete_performance(db, profile.id, performance_id)
