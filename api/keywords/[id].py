"""
DELETE /api/keywords/[id] - Delete keyword (verify ownership)
"""
from http.server import BaseHTTPRequestHandler
import sys
from pathlib import Path
import asyncio
import re

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
    
    def do_DELETE(self):
        """키워드 삭제 (소유권 확인)"""
        try:
            # 1. 인증 체크
            user_payload = require_auth(self)
            if not user_payload:
                return  # 이미 401 응답 전송됨
            
            # 2. URL에서 keyword_id 추출
            # URL 형식: /api/keywords/123
            match = re.search(r'/api/keywords/(\d+)', self.path)
            if not match:
                send_error(self, 400, "Invalid URL format")
                return
            
            keyword_id = int(match.group(1))
            
            # 3. 비동기 처리
            result = asyncio.run(self.delete_keyword(user_payload, keyword_id))
            
            # 4. 응답
            if result.get("error"):
                send_error(self, result["status_code"], result["message"])
            else:
                send_json(self, 200, result)
            
        except Exception as e:
            send_error(self, 500, f"Internal server error: {str(e)}")
    
    async def delete_keyword(self, user_payload: dict, keyword_id: int):
        """키워드 삭제 (소유권 확인)"""
        async for db in get_db():
            user_id = user_payload.get("user_id")
            
            if not user_id:
                # 이메일로 조회 (하위 호환성)
                email = user_payload.get("sub")
                query = text("""
                    SELECT u.id FROM users u WHERE u.email = :email
                """)
                result = await db.execute(query, {"email": email})
                user_row = result.fetchone()
                if not user_row:
                    return {"error": True, "status_code": 404, "message": "User not found"}
                user_id = user_row[0]
            
            # 1. 키워드 조회 (소유권 확인)
            select_query = text("""
                SELECT id, user_id FROM user_keywords
                WHERE id = :keyword_id
            """)
            select_result = await db.execute(select_query, {"keyword_id": keyword_id})
            keyword_row = select_result.fetchone()
            
            if not keyword_row:
                return {"error": True, "status_code": 404, "message": "Keyword not found"}
            
            # 2. 소유권 확인
            if keyword_row[1] != user_id:
                return {"error": True, "status_code": 403, "message": "Not authorized to delete this keyword"}
            
            # 3. 삭제
            delete_query = text("""
                DELETE FROM user_keywords WHERE id = :keyword_id
            """)
            await db.execute(delete_query, {"keyword_id": keyword_id})
            await db.commit()
            
            return {"message": "Keyword deleted successfully"}
