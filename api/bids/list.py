"""
GET /api/bids/list
입찰 공고 목록 조회 (페이지네이션 + 필터링)
"""
from http.server import BaseHTTPRequestHandler
import sys
from pathlib import Path
import json
from urllib.parse import parse_qs, urlparse

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

import asyncpg
import os
import asyncio


class handler(BaseHTTPRequestHandler):
    def do_OPTIONS(self):
        """CORS preflight"""
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type, Authorization')
        self.end_headers()
    
    def do_GET(self):
        """공고 목록 조회"""
        try:
            # 쿼리 파라미터 파싱
            parsed_url = urlparse(self.path)
            query_params = parse_qs(parsed_url.query)
            
            # 페이지네이션 파라미터
            page = int(query_params.get('page', ['1'])[0])
            page_size = int(query_params.get('page_size', ['20'])[0])
            
            # 검증
            if page < 1:
                page = 1
            if page_size < 1 or page_size > 100:
                page_size = 20
            
            # 필터링 파라미터
            keyword = query_params.get('keyword', [None])[0]
            agency = query_params.get('agency', [None])[0]
            source = query_params.get('source', [None])[0]
            status = query_params.get('status', [None])[0]
            
            # 비동기 로직 실행
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            result = loop.run_until_complete(
                self.handle_list(page, page_size, keyword, agency, source, status)
            )
            loop.close()
            
            # 응답
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            self.wfile.write(json.dumps(result, default=str).encode())
            
        except ValueError as e:
            self.send_error_json(400, str(e))
        except Exception as e:
            self.send_error_json(500, f"Internal server error: {str(e)}")
    
    async def handle_list(
        self, 
        page: int, 
        page_size: int, 
        keyword: str | None = None, 
        agency: str | None = None,
        source: str | None = None,
        status: str | None = None
    ):
        """공고 목록 조회 비즈니스 로직"""
        database_url = os.getenv("NEON_DATABASE_URL")
        if not database_url:
            raise ValueError("NEON_DATABASE_URL not configured")
        if database_url.startswith("postgresql://"):
            database_url = database_url.replace("postgresql://", "")
        
        conn = await asyncpg.connect(f"postgresql://{database_url}")
        
        try:
            # SQL 빌드 (WHERE 조건 동적 생성)
            where_conditions = []
            params = []
            param_index = 1
            
            if keyword:
                where_conditions.append(f"(title ILIKE ${param_index} OR content ILIKE ${param_index})")
                params.append(f"%{keyword}%")
                param_index += 1
            
            if agency:
                where_conditions.append(f"agency ILIKE ${param_index}")
                params.append(f"%{agency}%")
                param_index += 1
            
            if source:
                where_conditions.append(f"source = ${param_index}")
                params.append(source)
                param_index += 1
            
            if status:
                where_conditions.append(f"status = ${param_index}")
                params.append(status)
                param_index += 1
            
            where_clause = " AND ".join(where_conditions) if where_conditions else "1=1"
            
            # Total count
            count_query = f"SELECT COUNT(*) FROM bid_announcements WHERE {where_clause}"
            total = await conn.fetchval(count_query, *params)
            
            # 페이지네이션
            offset = (page - 1) * page_size
            params.extend([page_size, offset])
            
            # 데이터 조회
            list_query = f"""
                SELECT 
                    id, title, content, agency, posted_at, url, 
                    source, deadline, estimated_price, importance_score,
                    status, created_at, updated_at
                FROM bid_announcements 
                WHERE {where_clause}
                ORDER BY posted_at DESC, id DESC
                LIMIT ${param_index} OFFSET ${param_index + 1}
            """
            
            rows = await conn.fetch(list_query, *params)
            
            items = []
            for row in rows:
                items.append({
                    "id": row['id'],
                    "title": row['title'],
                    "content": row['content'][:200] + "..." if len(row['content']) > 200 else row['content'],
                    "agency": row['agency'],
                    "posted_at": row['posted_at'].isoformat() if row['posted_at'] else None,
                    "url": row['url'],
                    "source": row['source'],
                    "deadline": row['deadline'].isoformat() if row['deadline'] else None,
                    "estimated_price": row['estimated_price'],
                    "importance_score": row['importance_score'],
                    "status": row['status'],
                    "created_at": row['created_at'].isoformat() if row['created_at'] else None,
                    "updated_at": row['updated_at'].isoformat() if row['updated_at'] else None
                })
            
            return {
                "items": items,
                "total": total,
                "page": page,
                "page_size": page_size,
                "total_pages": (total + page_size - 1) // page_size
            }
        finally:
            await conn.close()
    
    def send_error_json(self, status_code: int, message: str, details=None):
        """에러 응답"""
        self.send_response(status_code)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()
        error_data = {"error": True, "message": message, "status_code": status_code}
        if details:
            error_data["details"] = details
        self.wfile.write(json.dumps(error_data).encode())
