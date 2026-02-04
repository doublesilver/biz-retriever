"""
Unified Keywords API
- GET /api/keywords?action=list - 사용자 키워드 목록 조회
- POST /api/keywords?action=create - 키워드 생성
- DELETE /api/keywords?action=delete&id=123 - 키워드 삭제
- GET /api/keywords?action=exclude - 제외 키워드 목록 조회
"""
from http.server import BaseHTTPRequestHandler
import sys
from pathlib import Path
import json
import asyncio
from urllib.parse import parse_qs, urlparse

sys.path.insert(0, str(Path(__file__).parent.parent))

from lib.auth import require_auth
from lib.utils import send_json, send_error, parse_json_body
from lib.models import BaseModel
import asyncpg
import os
from pydantic import Field


class CreateKeywordRequest(BaseModel):
    """키워드 생성 요청"""
    keyword: str = Field(..., min_length=1, max_length=100)
    category: str = Field(default="include")  # include or exclude
    is_active: bool = Field(default=True)


class handler(BaseHTTPRequestHandler):
    def do_OPTIONS(self):
        """CORS preflight"""
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, DELETE, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type, Authorization')
        self.end_headers()
    
    def do_GET(self):
        """GET 요청 라우팅 (list, exclude)"""
        try:
            user = require_auth(self)
            if not user:
                return
            
            parsed_url = urlparse(self.path)
            query_params = parse_qs(parsed_url.query)
            action = query_params.get('action', ['list'])[0]
            
            if action == 'list':
                self.handle_list(user)
            elif action == 'exclude':
                self.handle_exclude_list()
            else:
                send_error(self, 400, "Invalid action. Use ?action=list or ?action=exclude")
        except Exception as e:
            send_error(self, 500, f"Internal server error: {str(e)}")
    
    def do_POST(self):
        """POST 요청 라우팅 (create)"""
        try:
            user = require_auth(self)
            if not user:
                return
            
            parsed_url = urlparse(self.path)
            query_params = parse_qs(parsed_url.query)
            action = query_params.get('action', [''])[0]
            
            if action == 'create':
                self.handle_create(user)
            else:
                send_error(self, 400, "Invalid action. Use ?action=create")
        except Exception as e:
            send_error(self, 500, f"Internal server error: {str(e)}")
    
    def do_DELETE(self):
        """DELETE 요청 라우팅 (delete)"""
        try:
            user = require_auth(self)
            if not user:
                return
            
            parsed_url = urlparse(self.path)
            query_params = parse_qs(parsed_url.query)
            action = query_params.get('action', [''])[0]
            keyword_id = query_params.get('id', [None])[0]
            
            if action == 'delete' and keyword_id:
                self.handle_delete(user, int(keyword_id))
            else:
                send_error(self, 400, "Invalid action or missing id. Use ?action=delete&id=123")
        except Exception as e:
            send_error(self, 500, f"Internal server error: {str(e)}")
    
    # ===== LIST =====
    def handle_list(self, user: dict):
        """사용자 키워드 목록 조회"""
        try:
            result = asyncio.run(self.get_user_keywords(user['user_id']))
            send_json(self, 200, result)
        except Exception as e:
            send_error(self, 500, f"Failed to fetch keywords: {str(e)}")
    
    async def get_user_keywords(self, user_id: int):
        """사용자 키워드 조회 (DB)"""
        database_url = os.getenv("NEON_DATABASE_URL")
        if not database_url:
            raise ValueError("NEON_DATABASE_URL not configured")
        if database_url.startswith("postgresql://"):
            database_url = database_url.replace("postgresql://", "")
        
        conn = await asyncpg.connect(f"postgresql://{database_url}")
        
        try:
            query = """
                SELECT id, keyword, category, is_active, created_at
                FROM user_keywords
                WHERE user_id = $1
                ORDER BY created_at DESC
            """
            rows = await conn.fetch(query, user_id)
            
            items = []
            for row in rows:
                items.append({
                    "id": row['id'],
                    "keyword": row['keyword'],
                    "category": row['category'],
                    "is_active": row['is_active'],
                    "created_at": row['created_at'].isoformat() if row['created_at'] else None
                })
            
            return {"items": items, "total": len(items)}
        finally:
            await conn.close()
    
    # ===== EXCLUDE LIST =====
    def handle_exclude_list(self):
        """전역 제외 키워드 목록 조회"""
        try:
            result = asyncio.run(self.get_exclude_keywords())
            send_json(self, 200, result)
        except Exception as e:
            send_error(self, 500, f"Failed to fetch exclude keywords: {str(e)}")
    
    async def get_exclude_keywords(self):
        """제외 키워드 조회 (DB)"""
        database_url = os.getenv("NEON_DATABASE_URL")
        if not database_url:
            raise ValueError("NEON_DATABASE_URL not configured")
        if database_url.startswith("postgresql://"):
            database_url = database_url.replace("postgresql://", "")
        
        conn = await asyncpg.connect(f"postgresql://{database_url}")
        
        try:
            query = """
                SELECT id, word, is_active, created_at
                FROM exclude_keywords
                WHERE is_active = true
                ORDER BY created_at DESC
            """
            rows = await conn.fetch(query)
            
            items = []
            for row in rows:
                items.append({
                    "id": row['id'],
                    "word": row['word'],
                    "is_active": row['is_active'],
                    "created_at": row['created_at'].isoformat() if row['created_at'] else None
                })
            
            return {"items": items, "total": len(items)}
        finally:
            await conn.close()
    
    # ===== CREATE =====
    def handle_create(self, user: dict):
        """키워드 생성"""
        try:
            req = parse_json_body(self, CreateKeywordRequest)
            if not req:
                return
            
            result = asyncio.run(self.create_keyword(user['user_id'], req))
            send_json(self, 201, result)
        except Exception as e:
            send_error(self, 500, f"Failed to create keyword: {str(e)}")
    
    async def create_keyword(self, user_id: int, req: CreateKeywordRequest):
        """키워드 생성 (DB)"""
        database_url = os.getenv("NEON_DATABASE_URL")
        if not database_url:
            raise ValueError("NEON_DATABASE_URL not configured")
        if database_url.startswith("postgresql://"):
            database_url = database_url.replace("postgresql://", "")
        
        conn = await asyncpg.connect(f"postgresql://{database_url}")
        
        try:
            # 중복 확인
            existing = await conn.fetchrow(
                "SELECT id FROM user_keywords WHERE user_id = $1 AND keyword = $2",
                user_id, req.keyword
            )
            if existing:
                raise ValueError("Keyword already exists")
            
            # 키워드 생성
            query = """
                INSERT INTO user_keywords (user_id, keyword, category, is_active)
                VALUES ($1, $2, $3, $4)
                RETURNING id, keyword, category, is_active, created_at
            """
            row = await conn.fetchrow(query, user_id, req.keyword, req.category, req.is_active)
            
            return {
                "id": row['id'],
                "keyword": row['keyword'],
                "category": row['category'],
                "is_active": row['is_active'],
                "created_at": row['created_at'].isoformat(),
                "message": "Keyword created successfully"
            }
        finally:
            await conn.close()
    
    # ===== DELETE =====
    def handle_delete(self, user: dict, keyword_id: int):
        """키워드 삭제"""
        try:
            result = asyncio.run(self.delete_keyword(user['user_id'], keyword_id))
            send_json(self, 200, result)
        except Exception as e:
            send_error(self, 500, f"Failed to delete keyword: {str(e)}")
    
    async def delete_keyword(self, user_id: int, keyword_id: int):
        """키워드 삭제 (DB)"""
        database_url = os.getenv("NEON_DATABASE_URL")
        if not database_url:
            raise ValueError("NEON_DATABASE_URL not configured")
        if database_url.startswith("postgresql://"):
            database_url = database_url.replace("postgresql://", "")
        
        conn = await asyncpg.connect(f"postgresql://{database_url}")
        
        try:
            # 권한 확인
            existing = await conn.fetchrow(
                "SELECT id FROM user_keywords WHERE id = $1 AND user_id = $2",
                keyword_id, user_id
            )
            if not existing:
                raise ValueError("Keyword not found or access denied")
            
            # 삭제
            await conn.execute("DELETE FROM user_keywords WHERE id = $1", keyword_id)
            
            return {"message": "Keyword deleted successfully", "id": keyword_id}
        finally:
            await conn.close()
