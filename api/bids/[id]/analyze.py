"""
POST /api/bids/[id]/analyze
입찰 공고 AI 분석 (RAG with Gemini)

Performance Optimized:
- Lazy imports for heavy AI libraries (RAG service)
- Reduced cold start time by ~200ms
"""
from http.server import BaseHTTPRequestHandler
import sys
from pathlib import Path
import json
import re
import asyncio
import os

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

# Essential imports only
from lib.utils import send_json, send_error, handle_cors_preflight
from lib.auth import require_auth


class handler(BaseHTTPRequestHandler):
    def do_OPTIONS(self):
        """CORS preflight"""
        if handle_cors_preflight(self):
            return
    
    def do_POST(self):
        """공고 AI 분석"""
        try:
            # 1. 인증 체크
            user_payload = require_auth(self)
            if not user_payload:
                return  # 이미 401 응답 전송됨
            
            # 2. URL에서 ID 추출 (예: /api/bids/123/analyze)
            match = re.search(r'/api/bids/(\d+)/analyze', self.path)
            if not match:
                send_error(self, 400, "Invalid bid ID format")
                return
            
            bid_id = int(match.group(1))
            
            # 3. 비동기 로직 실행 (타임아웃 50초)
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                result = loop.run_until_complete(
                    asyncio.wait_for(self.handle_analyze(bid_id), timeout=50.0)
                )
            except asyncio.TimeoutError:
                send_error(self, 500, "AI analysis timeout (50s limit)")
                return
            finally:
                loop.close()
            
            # 4. 응답
            send_json(self, 200, result)
            
        except ValueError as e:
            send_error(self, 400, str(e))
        except Exception as e:
            send_error(self, 500, f"Internal server error: {str(e)}")
    
    async def handle_analyze(self, bid_id: int):
        """공고 분석 비즈니스 로직"""
        # Lazy imports (performance optimization)
        import asyncpg
        from datetime import datetime, timezone
        from app.services.rag_service import rag_service
        
        database_url = os.getenv("NEON_DATABASE_URL")
        if not database_url:
            raise ValueError("NEON_DATABASE_URL not configured")
        
        # asyncpg 연결 (postgresql:// 제거)
        if database_url.startswith("postgresql://"):
            database_url = database_url.replace("postgresql://", "")
        
        conn = await asyncpg.connect(f"postgresql://{database_url}")
        
        try:
            # 1. 공고 조회
            query = """
                SELECT id, title, agency, content, estimated_price
                FROM bid_announcements 
                WHERE id = $1
            """
            
            row = await conn.fetchrow(query, bid_id)
            
            if not row:
                raise ValueError(f"Bid with ID {bid_id} not found")
            
            # 2. AI 분석 (RAGService)
            content = f"""공고 제목: {row['title']}
발주 기관: {row['agency']}
추정 금액: {row['estimated_price']}

공고 내용:
{row['content']}"""
            
            # RAGService 호출 (Gemini AI)
            analysis_result = await rag_service.analyze_bid(content)
            
            # 3. 결과 저장
            update_query = """
                UPDATE bid_announcements 
                SET 
                    ai_summary = $1,
                    ai_keywords = $2,
                    region_code = $3,
                    license_requirements = $4,
                    min_performance = $5,
                    processed = TRUE,
                    updated_at = $6
                WHERE id = $7
            """
            
            now = datetime.now(timezone.utc)
            
            await conn.execute(
                update_query,
                analysis_result.get("summary"),
                analysis_result.get("keywords", []),
                analysis_result.get("region_code"),
                analysis_result.get("license_requirements", []),
                analysis_result.get("min_performance", 0.0),
                now,
                bid_id
            )
            
            # 4. 응답 생성
            return {
                "id": bid_id,
                "ai_summary": analysis_result.get("summary"),
                "ai_keywords": analysis_result.get("keywords", []),
                "region_code": analysis_result.get("region_code"),
                "license_requirements": analysis_result.get("license_requirements", []),
                "min_performance": analysis_result.get("min_performance", 0.0),
                "analyzed_at": now.isoformat()
            }
        finally:
            await conn.close()
