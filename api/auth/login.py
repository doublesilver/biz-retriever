"""
POST /api/auth/login  
로그인 엔드포인트
"""
from http.server import BaseHTTPRequestHandler
import sys
from pathlib import Path
import json

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from lib.models import LoginRequest
from lib.auth import verify_password, create_access_token
from pydantic import ValidationError
import asyncpg
import os


class handler(BaseHTTPRequestHandler):
    def do_OPTIONS(self):
        """CORS preflight"""
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type, Authorization')
        self.end_headers()
    
    def do_POST(self):
        """로그인 처리 (동기 버전)"""
        try:
            # 1. 요청 파싱
            content_length = int(self.headers.get('Content-Length', 0))
            body = self.rfile.read(content_length).decode('utf-8')
            data = json.loads(body)
            login_req = LoginRequest(**data)
            
            # 2. 동기 DB 연결
            import asyncio
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            result = loop.run_until_complete(self.handle_login(login_req))
            loop.close()
            
            # 3. 응답
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            self.wfile.write(json.dumps(result).encode())
            
        except ValidationError as e:
            self.send_error_json(422, "Validation error", {"details": e.errors()})
        except ValueError as e:
            self.send_error_json(401, str(e))
        except Exception as e:
            self.send_error_json(500, f"Internal server error: {str(e)}")
    
    async def handle_login(self, login_req: LoginRequest):
        """로그인 비즈니스 로직"""
        # Database URL
        database_url = os.getenv("NEON_DATABASE_URL")
        if database_url.startswith("postgresql://"):
            database_url = database_url.replace("postgresql://", "")
        
        conn = await asyncpg.connect(f"postgresql://{database_url}")
        
        try:
            # 사용자 조회
            user_row = await conn.fetchrow("""
                SELECT id, email, hashed_password, name, is_active
                FROM users
                WHERE email = $1
            """, login_req.email)
            
            if not user_row:
                raise ValueError("Invalid email or password")
            
            if not user_row['is_active']:
                raise ValueError("Account is inactive")
            
            # 비밀번호 검증
            if not verify_password(login_req.password, user_row['hashed_password']):
                raise ValueError("Invalid email or password")
            
            # JWT 토큰 생성
            token_data = {
                "sub": user_row['email'],
                "user_id": user_row['id'],
                "name": user_row.get('name', '')
            }
            access_token = create_access_token(token_data)
            
            return {
                "access_token": access_token,
                "token_type": "bearer",
                "user": {
                    "id": user_row['id'],
                    "email": user_row['email'],
                    "name": user_row.get('name', '')
                }
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
