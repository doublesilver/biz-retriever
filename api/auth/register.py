"""
POST /api/auth/register
회원가입 엔드포인트
"""
from http.server import BaseHTTPRequestHandler
import sys
from pathlib import Path
import json

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from lib.models import RegisterRequest
from lib.auth import hash_password
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
        """회원가입 처리"""
        try:
            # 요청 파싱
            content_length = int(self.headers.get('Content-Length', 0))
            body = self.rfile.read(content_length).decode('utf-8')
            data = json.loads(body)
            register_req = RegisterRequest(**data)
            
            # 동기 DB 연결
            import asyncio
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            result = loop.run_until_complete(self.handle_register(register_req))
            loop.close()
            
            # 응답
            self.send_response(201)
            self.send_header('Content-Type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            self.wfile.write(json.dumps(result).encode())
            
        except ValidationError as e:
            self.send_error_json(422, "Validation error", {"details": e.errors()})
        except ValueError as e:
            self.send_error_json(400, str(e))
        except Exception as e:
            self.send_error_json(500, f"Internal server error: {str(e)}")
    
    async def handle_register(self, register_req: RegisterRequest):
        """회원가입 비즈니스 로직"""
        database_url = os.getenv("NEON_DATABASE_URL")
        if database_url.startswith("postgresql://"):
            database_url = database_url.replace("postgresql://", "")
        
        conn = await asyncpg.connect(f"postgresql://{database_url}")
        
        try:
            # 이메일 중복 체크
            existing = await conn.fetchrow("SELECT id FROM users WHERE email = $1", register_req.email)
            if existing:
                raise ValueError("Email already registered")
            
            # 비밀번호 해싱 (Argon2)
            hashed_password = hash_password(register_req.password)
            
            # 사용자 생성 (provider 필드 포함)
            user_row = await conn.fetchrow("""
                INSERT INTO users (email, hashed_password, name, provider, is_active, failed_login_attempts, is_superuser)
                VALUES ($1, $2, $3, 'email', true, 0, false)
                RETURNING id, email, name, is_active, created_at
            """, register_req.email, hashed_password, register_req.name)
            
            return {
                "id": user_row['id'],
                "email": user_row['email'],
                "name": user_row['name'],
                "is_active": user_row['is_active'],
                "created_at": user_row['created_at'].isoformat(),
                "message": "User registered successfully"
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
