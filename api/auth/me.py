"""
GET /api/auth/me
현재 인증된 사용자 정보 조회
"""
from http.server import BaseHTTPRequestHandler
import sys
from pathlib import Path
import asyncio

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from lib.utils import send_json, send_error, handle_cors_preflight
from lib.auth import require_auth
from lib.db import get_db
from sqlalchemy import text


class handler(BaseHTTPRequestHandler):
    def do_OPTIONS(self):
        """CORS preflight 처리"""
        if handle_cors_preflight(self):
            return
    
    def do_GET(self):
        """인증된 사용자 정보 조회"""
        try:
            # 1. 인증 체크
            user_payload = require_auth(self)
            if not user_payload:
                return  # 이미 401 응답 전송됨
            
            # 2. 비동기 처리
            result = asyncio.run(self.get_user_info(user_payload))
            
            # 3. 응답
            send_json(self, 200, result)
            
        except Exception as e:
            send_error(self, 500, f"Internal server error: {str(e)}")
    
    async def get_user_info(self, user_payload: dict):
        """사용자 정보 조회"""
        async for db in get_db():
            # 토큰에서 사용자 ID 추출
            user_id = user_payload.get("user_id")
            
            if not user_id:
                # 이메일로 조회 (하위 호환성)
                email = user_payload.get("sub")
                query = text("""
                    SELECT id, email, name, is_active, created_at
                    FROM users
                    WHERE email = :email
                """)
                result = await db.execute(query, {"email": email})
            else:
                query = text("""
                    SELECT id, email, name, is_active, created_at
                    FROM users
                    WHERE id = :user_id
                """)
                result = await db.execute(query, {"user_id": user_id})
            
            user_row = result.fetchone()
            
            if not user_row:
                raise ValueError("User not found")
            
            # 응답 생성
            return {
                "id": user_row[0],
                "email": user_row[1],
                "name": user_row[2],
                "is_active": user_row[3],
                "created_at": user_row[4].isoformat()
            }
