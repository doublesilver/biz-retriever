"""
GET /api/keywords - List user's keywords
POST /api/keywords - Add keyword (with plan limit check)
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
from sqlalchemy import text, select, func
from pydantic import BaseModel, Field


class KeywordCreateRequest(BaseModel):
    keyword: str = Field(..., min_length=1, max_length=100)
    category: str = Field(default="include", pattern="^(include|exclude)$")
    is_active: bool = True


class handler(BaseHTTPRequestHandler):
    def do_OPTIONS(self):
        """CORS preflight 처리"""
        if handle_cors_preflight(self):
            return
    
    def do_GET(self):
        """사용자 키워드 목록 조회"""
        try:
            # 1. 인증 체크
            user_payload = require_auth(self)
            if not user_payload:
                return  # 이미 401 응답 전송됨
            
            # 2. 비동기 처리
            result = asyncio.run(self.get_keywords(user_payload))
            
            # 3. 응답
            send_json(self, 200, result)
            
        except Exception as e:
            send_error(self, 500, f"Internal server error: {str(e)}")
    
    def do_POST(self):
        """키워드 추가 (플랜 제한 체크)"""
        try:
            # 1. 인증 체크
            user_payload = require_auth(self)
            if not user_payload:
                return
            
            # 2. 요청 body 파싱
            keyword_req = parse_json_body(self, KeywordCreateRequest)
            if not keyword_req:
                return  # 이미 에러 응답 전송됨
            
            # 3. 비동기 처리
            result = asyncio.run(self.create_keyword(user_payload, keyword_req))
            
            # 4. 응답
            if result.get("error"):
                send_error(self, result["status_code"], result["message"])
            else:
                send_json(self, 201, result)
            
        except Exception as e:
            send_error(self, 500, f"Internal server error: {str(e)}")
    
    async def get_keywords(self, user_payload: dict):
        """사용자 키워드 목록 조회"""
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
                    raise ValueError("User not found")
                user_id = user_row[0]
            
            # 키워드 조회
            query = text("""
                SELECT id, user_id, keyword, category, is_active, created_at, updated_at
                FROM user_keywords
                WHERE user_id = :user_id
                ORDER BY created_at DESC
            """)
            result = await db.execute(query, {"user_id": user_id})
            rows = result.fetchall()
            
            keywords = []
            for row in rows:
                keywords.append({
                    "id": row[0],
                    "user_id": row[1],
                    "keyword": row[2],
                    "category": row[3],
                    "is_active": row[4],
                    "created_at": row[5].isoformat(),
                    "updated_at": row[6].isoformat()
                })
            
            return {"items": keywords}
    
    async def create_keyword(self, user_payload: dict, keyword_req: KeywordCreateRequest):
        """키워드 추가 (플랜 제한 체크)"""
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
            
            # 1. 플랜 조회
            plan_query = text("""
                SELECT s.plan_name, s.is_active
                FROM subscriptions s
                WHERE s.user_id = :user_id
            """)
            plan_result = await db.execute(plan_query, {"user_id": user_id})
            plan_row = plan_result.fetchone()
            
            # 플랜이 없거나 비활성화면 Free 플랜
            plan_name = "free"
            if plan_row and plan_row[1]:  # is_active
                plan_name = plan_row[0]
            
            # 2. 플랜별 제한
            plan_limits = {
                "free": 5,
                "basic": 20,
                "pro": 100
            }
            limit = plan_limits.get(plan_name, 5)
            
            # 3. 현재 키워드 개수 조회
            count_query = text("""
                SELECT COUNT(*) FROM user_keywords WHERE user_id = :user_id
            """)
            count_result = await db.execute(count_query, {"user_id": user_id})
            current_count = count_result.scalar()
            
            # 4. 제한 체크
            if current_count >= limit:
                return {
                    "error": True,
                    "status_code": 403,
                    "message": f"Keyword limit reached for {plan_name.capitalize()} plan. Limit: {limit}"
                }
            
            # 5. 중복 체크
            duplicate_query = text("""
                SELECT id FROM user_keywords
                WHERE user_id = :user_id AND keyword = :keyword
            """)
            duplicate_result = await db.execute(duplicate_query, {
                "user_id": user_id,
                "keyword": keyword_req.keyword
            })
            if duplicate_result.fetchone():
                return {
                    "error": True,
                    "status_code": 400,
                    "message": "Keyword already exists"
                }
            
            # 6. 키워드 추가
            insert_query = text("""
                INSERT INTO user_keywords (user_id, keyword, category, is_active, created_at, updated_at)
                VALUES (:user_id, :keyword, :category, :is_active, NOW(), NOW())
                RETURNING id, user_id, keyword, category, is_active, created_at, updated_at
            """)
            insert_result = await db.execute(insert_query, {
                "user_id": user_id,
                "keyword": keyword_req.keyword,
                "category": keyword_req.category,
                "is_active": keyword_req.is_active
            })
            await db.commit()
            
            row = insert_result.fetchone()
            return {
                "id": row[0],
                "user_id": row[1],
                "keyword": row[2],
                "category": row[3],
                "is_active": row[4],
                "created_at": row[5].isoformat(),
                "updated_at": row[6].isoformat()
            }
