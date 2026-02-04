"""
Unified Auth API
- POST /api/auth?action=login - 로그인
- POST /api/auth?action=register - 회원가입
- GET /api/auth?action=me - 내 정보 조회
"""
from http.server import BaseHTTPRequestHandler
import sys
from pathlib import Path
import json
import asyncio
from urllib.parse import parse_qs, urlparse

sys.path.insert(0, str(Path(__file__).parent.parent))

from lib.models import LoginRequest, RegisterRequest
from lib.auth import verify_password, create_access_token, hash_password, require_auth
from lib.utils import send_json, send_error
from lib.db import get_db
from sqlalchemy import text
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
        """POST 요청 라우팅 (login, register)"""
        try:
            # Query parameter에서 action 추출
            parsed_url = urlparse(self.path)
            query_params = parse_qs(parsed_url.query)
            action = query_params.get('action', [''])[0]
            
            if action == 'login':
                self.handle_login_post()
            elif action == 'register':
                self.handle_register_post()
            else:
                self.send_error_json(400, "Invalid action. Use ?action=login or ?action=register")
        except Exception as e:
            self.send_error_json(500, f"Internal server error: {str(e)}")
    
    def do_GET(self):
        """GET 요청 라우팅 (me)"""
        try:
            # Query parameter에서 action 추출
            parsed_url = urlparse(self.path)
            query_params = parse_qs(parsed_url.query)
            action = query_params.get('action', [''])[0]
            
            if action == 'me':
                self.handle_me_get()
            else:
                self.send_error_json(400, "Invalid action. Use ?action=me")
        except Exception as e:
            self.send_error_json(500, f"Internal server error: {str(e)}")
    
    # ===== LOGIN =====
    def handle_login_post(self):
        """로그인 처리"""
        try:
            content_length = int(self.headers.get('Content-Length', 0))
            body = self.rfile.read(content_length).decode('utf-8')
            data = json.loads(body)
            login_req = LoginRequest(**data)
            
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            result = loop.run_until_complete(self.handle_login(login_req))
            loop.close()
            
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            self.wfile.write(json.dumps(result).encode())
            
        except ValidationError as e:
            self.send_error_json(422, "Validation error", {"details": e.errors()})
        except ValueError as e:
            self.send_error_json(401, str(e))
    
    async def handle_login(self, login_req: LoginRequest):
        """로그인 비즈니스 로직"""
        database_url = os.getenv("NEON_DATABASE_URL")
        if database_url.startswith("postgresql://"):
            database_url = database_url.replace("postgresql://", "")
        
        conn = await asyncpg.connect(f"postgresql://{database_url}")
        
        try:
            user_row = await conn.fetchrow("""
                SELECT id, email, hashed_password, name, is_active
                FROM users
                WHERE email = $1
            """, login_req.email)
            
            if not user_row:
                raise ValueError("Invalid email or password")
            
            if not user_row['is_active']:
                raise ValueError("Account is inactive")
            
            if not verify_password(login_req.password, user_row['hashed_password']):
                raise ValueError("Invalid email or password")
            
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
    
    # ===== REGISTER =====
    def handle_register_post(self):
        """회원가입 처리"""
        try:
            content_length = int(self.headers.get('Content-Length', 0))
            body = self.rfile.read(content_length).decode('utf-8')
            data = json.loads(body)
            register_req = RegisterRequest(**data)
            
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            result = loop.run_until_complete(self.handle_register(register_req))
            loop.close()
            
            self.send_response(201)
            self.send_header('Content-Type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            self.wfile.write(json.dumps(result).encode())
            
        except ValidationError as e:
            self.send_error_json(422, "Validation error", {"details": e.errors()})
        except ValueError as e:
            self.send_error_json(400, str(e))
    
    async def handle_register(self, register_req: RegisterRequest):
        """회원가입 비즈니스 로직"""
        database_url = os.getenv("NEON_DATABASE_URL")
        if database_url.startswith("postgresql://"):
            database_url = database_url.replace("postgresql://", "")
        
        conn = await asyncpg.connect(f"postgresql://{database_url}")
        
        try:
            existing = await conn.fetchrow("SELECT id FROM users WHERE email = $1", register_req.email)
            if existing:
                raise ValueError("Email already registered")
            
            hashed_password = hash_password(register_req.password)
            
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
    
    # ===== ME =====
    def handle_me_get(self):
        """내 정보 조회"""
        try:
            user_payload = require_auth(self)
            if not user_payload:
                return
            
            result = asyncio.run(self.get_user_info(user_payload))
            send_json(self, 200, result)
            
        except Exception as e:
            send_error(self, 500, f"Internal server error: {str(e)}")
    
    async def get_user_info(self, user_payload: dict):
        """사용자 정보 조회"""
        async for db in get_db():
            user_id = user_payload.get("user_id")
            
            if not user_id:
                email = user_payload.get("sub")
                query = text("""
                    SELECT id, email, name, is_active, created_at
                    FROM users
                    WHERE email = :email
                """)
                result = await db.execute(query, {"email": email})
            else:
                query = text("""
                    SELECT id, email, name, is_active, created_at
                    FROM users
                    WHERE id = :user_id
                """)
                result = await db.execute(query, {"user_id": user_id})
            
            user_row = result.fetchone()
            
            if not user_row:
                raise ValueError("User not found")
            
            return {
                "id": user_row[0],
                "email": user_row[1],
                "name": user_row[2],
                "is_active": user_row[3],
                "created_at": user_row[4].isoformat()
            }
    
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
