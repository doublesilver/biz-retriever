"""
Unified Bids API
- GET /api/bids?action=list - 공고 목록 조회
- GET /api/bids?action=detail&id=123 - 공고 상세 조회
"""
from http.server import BaseHTTPRequestHandler
import sys
from pathlib import Path
import json
import asyncio
from urllib.parse import parse_qs, urlparse

sys.path.insert(0, str(Path(__file__).parent.parent))

import asyncpg
import os


class handler(BaseHTTPRequestHandler):
    def do_OPTIONS(self):
        """CORS preflight"""
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type, Authorization')
        self.end_headers()
    
    def do_GET(self):
        """GET 요청 라우팅"""
        try:
            parsed_url = urlparse(self.path)
            query_params = parse_qs(parsed_url.query)
            action = query_params.get('action', [''])[0]
            
            if action == 'list':
                self.handle_list(query_params)
            elif action == 'detail':
                bid_id = query_params.get('id', [None])[0]
                if not bid_id:
                    self.send_error_json(400, "Missing 'id' parameter")
                    return
                self.handle_detail(int(bid_id))
            else:
                self.send_error_json(400, "Invalid action. Use ?action=list or ?action=detail&id=123")
        except Exception as e:
            self.send_error_json(500, f"Internal server error: {str(e)}")
    
    # ===== LIST =====
    def handle_list(self, query_params):
        """공고 목록 조회"""
        try:
            page = int(query_params.get('page', ['1'])[0])
            page_size = int(query_params.get('page_size', ['20'])[0])
            
            if page < 1:
                page = 1
            if page_size < 1 or page_size > 100:
                page_size = 20
            
            keyword = query_params.get('keyword', [None])[0]
            agency = query_params.get('agency', [None])[0]
            source = query_params.get('source', [None])[0]
            status = query_params.get('status', [None])[0]
            
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            result = loop.run_until_complete(
                self.handle_list_async(page, page_size, keyword, agency, source, status)
            )
            loop.close()
            
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            self.wfile.write(json.dumps(result, default=str).encode())
            
        except ValueError as e:
            self.send_error_json(400, str(e))
    
    async def handle_list_async(
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
            
            count_query = f"SELECT COUNT(*) FROM bid_announcements WHERE {where_clause}"
            total = await conn.fetchval(count_query, *params)
            
            offset = (page - 1) * page_size
            params.extend([page_size, offset])
            
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
    
    # ===== DETAIL =====
    def handle_detail(self, bid_id: int):
        """공고 상세 조회"""
        try:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            result = loop.run_until_complete(self.handle_detail_async(bid_id))
            loop.close()
            
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            self.wfile.write(json.dumps(result, default=str).encode())
            
        except ValueError as e:
            self.send_error_json(400, str(e))
    
    async def handle_detail_async(self, bid_id: int):
        """공고 상세 조회 비즈니스 로직"""
        database_url = os.getenv("NEON_DATABASE_URL")
        if not database_url:
            raise ValueError("NEON_DATABASE_URL not configured")
        if database_url.startswith("postgresql://"):
            database_url = database_url.replace("postgresql://", "")
        
        conn = await asyncpg.connect(f"postgresql://{database_url}")
        
        try:
            query = """
                SELECT 
                    id, title, content, agency, posted_at, url, processed,
                    ai_summary, ai_keywords,
                    source, deadline, estimated_price, importance_score,
                    keywords_matched, is_notified, crawled_at, attachment_content,
                    region_code, min_performance, license_requirements,
                    status, assigned_to, notes,
                    created_at, updated_at
                FROM bid_announcements 
                WHERE id = $1
            """
            
            row = await conn.fetchrow(query, bid_id)
            
            if not row:
                raise ValueError(f"Bid with ID {bid_id} not found")
            
            assignee = None
            if row['assigned_to']:
                assignee_row = await conn.fetchrow(
                    "SELECT id, email, name FROM users WHERE id = $1",
                    row['assigned_to']
                )
                if assignee_row:
                    assignee = {
                        "id": assignee_row['id'],
                        "email": assignee_row['email'],
                        "name": assignee_row['name']
                    }
            
            return {
                "id": row['id'],
                "title": row['title'],
                "content": row['content'],
                "agency": row['agency'],
                "posted_at": row['posted_at'].isoformat() if row['posted_at'] else None,
                "url": row['url'],
                "processed": row['processed'],
                "ai_summary": row['ai_summary'],
                "ai_keywords": row['ai_keywords'],
                "source": row['source'],
                "deadline": row['deadline'].isoformat() if row['deadline'] else None,
                "estimated_price": row['estimated_price'],
                "importance_score": row['importance_score'],
                "keywords_matched": row['keywords_matched'],
                "is_notified": row['is_notified'],
                "crawled_at": row['crawled_at'].isoformat() if row['crawled_at'] else None,
                "attachment_content": row['attachment_content'],
                "region_code": row['region_code'],
                "min_performance": row['min_performance'],
                "license_requirements": row['license_requirements'],
                "status": row['status'],
                "assigned_to": row['assigned_to'],
                "assignee": assignee,
                "notes": row['notes'],
                "created_at": row['created_at'].isoformat() if row['created_at'] else None,
                "updated_at": row['updated_at'].isoformat() if row['updated_at'] else None
            }
        finally:
            await conn.close()
    
    # ===== UTILS =====
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
