"""
GET /api/keywords/exclude - List exclude keywords
POST /api/keywords/exclude - Add exclude keyword
DELETE /api/keywords/exclude/[id] - Delete exclude keyword
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
from sqlalchemy import text
from pydantic import BaseModel, Field


class ExcludeKeywordCreateRequest(BaseModel):
    word: str = Field(..., min_length=1, max_length=100)
    is_active: bool = True


class handler(BaseHTTPRequestHandler):
    def do_OPTIONS(self):
        """CORS preflight 처리"""
        if handle_cors_preflight(self):
            return
    
    def do_GET(self):
        """제외 키워드 목록 조회"""
        try:
            # 1. 인증 체크
            user_payload = require_auth(self)
            if not user_payload:
                return  # 이미 401 응답 전송됨
            
            # 2. 비동기 처리
            result = asyncio.run(self.get_exclude_keywords())
            
            # 3. 응답
            send_json(self, 200, result)
            
        except Exception as e:
            send_error(self, 500, f"Internal server error: {str(e)}")
    
    def do_POST(self):
        """제외 키워드 추가"""
        try:
            # 1. 인증 체크
            user_payload = require_auth(self)
            if not user_payload:
                return
            
            # 2. 요청 body 파싱
            keyword_req = parse_json_body(self, ExcludeKeywordCreateRequest)
            if not keyword_req:
                return  # 이미 에러 응답 전송됨
            
            # 3. 비동기 처리
            result = asyncio.run(self.create_exclude_keyword(keyword_req))
            
            # 4. 응답
            if result.get("error"):
                send_error(self, result["status_code"], result["message"])
            else:
                send_json(self, 201, result)
            
        except Exception as e:
            send_error(self, 500, f"Internal server error: {str(e)}")
    
    def do_DELETE(self):
        """제외 키워드 삭제"""
        try:
            # 1. 인증 체크
            user_payload = require_auth(self)
            if not user_payload:
                return  # 이미 401 응답 전송됨
            
            # 2. URL에서 keyword_id 추출
            # URL 형식: /api/keywords/exclude/123
            match = re.search(r'/api/keywords/exclude/(\d+)', self.path)
            if not match:
                send_error(self, 400, "Invalid URL format")
                return
            
            keyword_id = int(match.group(1))
            
            # 3. 비동기 처리
            result = asyncio.run(self.delete_exclude_keyword(keyword_id))
            
            # 4. 응답
            if result.get("error"):
                send_error(self, result["status_code"], result["message"])
            else:
                send_json(self, 200, result)
            
        except Exception as e:
            send_error(self, 500, f"Internal server error: {str(e)}")
    
    async def get_exclude_keywords(self):
        """제외 키워드 목록 조회"""
        async for db in get_db():
            query = text("""
                SELECT id, word, is_active, created_at, updated_at
                FROM exclude_keywords
                ORDER BY created_at DESC
            """)
            result = await db.execute(query)
            rows = result.fetchall()
            
            keywords = []
            for row in rows:
                keywords.append({
                    "id": row[0],
                    "word": row[1],
                    "is_active": row[2],
                    "created_at": row[3].isoformat(),
                    "updated_at": row[4].isoformat()
                })
            
            return {"items": keywords}
    
    async def create_exclude_keyword(self, keyword_req: ExcludeKeywordCreateRequest):
        """제외 키워드 추가"""
        async for db in get_db():
            # 1. 중복 체크
            duplicate_query = text("""
                SELECT id FROM exclude_keywords WHERE word = :word
            """)
            duplicate_result = await db.execute(duplicate_query, {"word": keyword_req.word.strip()})
            if duplicate_result.fetchone():
                return {
                    "error": True,
                    "status_code": 400,
                    "message": "Exclude keyword already exists"
                }
            
            # 2. 키워드 추가
            insert_query = text("""
                INSERT INTO exclude_keywords (word, is_active, created_at, updated_at)
                VALUES (:word, :is_active, NOW(), NOW())
                RETURNING id, word, is_active, created_at, updated_at
            """)
            insert_result = await db.execute(insert_query, {
                "word": keyword_req.word.strip(),
                "is_active": keyword_req.is_active
            })
            await db.commit()
            
            row = insert_result.fetchone()
            return {
                "id": row[0],
                "word": row[1],
                "is_active": row[2],
                "created_at": row[3].isoformat(),
                "updated_at": row[4].isoformat()
            }
    
    async def delete_exclude_keyword(self, keyword_id: int):
        """제외 키워드 삭제"""
        async for db in get_db():
            # 1. 키워드 존재 확인
            select_query = text("""
                SELECT id FROM exclude_keywords WHERE id = :keyword_id
            """)
            select_result = await db.execute(select_query, {"keyword_id": keyword_id})
            keyword_row = select_result.fetchone()
            
            if not keyword_row:
                return {"error": True, "status_code": 404, "message": "Exclude keyword not found"}
            
            # 2. 삭제
            delete_query = text("""
                DELETE FROM exclude_keywords WHERE id = :keyword_id
            """)
            await db.execute(delete_query, {"keyword_id": keyword_id})
            await db.commit()
            
            return {"message": "Exclude keyword deleted successfully"}
