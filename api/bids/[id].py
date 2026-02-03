"""
GET /api/bids/[id]
개별 입찰 공고 상세 조회
"""
from http.server import BaseHTTPRequestHandler
import sys
from pathlib import Path
import json
import re

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
        """공고 상세 조회"""
        try:
            # URL에서 ID 추출 (예: /api/bids/123?bypass=...)
            match = re.search(r'/api/bids/(\d+)', self.path)
            if not match:
                self.send_error_json(400, "Invalid bid ID format")
                return
            
            bid_id = int(match.group(1))
            
            # 비동기 로직 실행
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            result = loop.run_until_complete(self.handle_detail(bid_id))
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
    
    async def handle_detail(self, bid_id: int):
        """공고 상세 조회 비즈니스 로직"""
        database_url = os.getenv("NEON_DATABASE_URL")
        if not database_url:
            raise ValueError("NEON_DATABASE_URL not configured")
        if database_url.startswith("postgresql://"):
            database_url = database_url.replace("postgresql://", "")
        
        conn = await asyncpg.connect(f"postgresql://{database_url}")
        
        try:
            # 전체 필드 조회
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
            
            # 담당자 정보 조회 (있을 경우)
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
