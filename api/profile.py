"""
Unified Profile API
- GET /api/profile?action=get - 프로필 조회
- POST /api/profile?action=create - 프로필 생성
- PUT /api/profile?action=update - 프로필 수정
- GET /api/profile?action=licenses - 보유 면허 조회
- GET /api/profile?action=performances - 시공 실적 조회
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
from typing import Optional, List


class CreateProfileRequest(BaseModel):
    """프로필 생성 요청"""
    company_name: str = Field(..., min_length=1, max_length=200)
    brn: Optional[str] = Field(None, max_length=20)  # 사업자등록번호
    location_code: Optional[str] = Field(None, max_length=10)
    keywords: Optional[str] = Field(None, max_length=500)
    credit_rating: Optional[str] = Field(None, max_length=10)


class UpdateProfileRequest(BaseModel):
    """프로필 수정 요청"""
    company_name: Optional[str] = Field(None, min_length=1, max_length=200)
    brn: Optional[str] = Field(None, max_length=20)
    location_code: Optional[str] = Field(None, max_length=10)
    keywords: Optional[str] = Field(None, max_length=500)
    credit_rating: Optional[str] = Field(None, max_length=10)


class handler(BaseHTTPRequestHandler):
    def do_OPTIONS(self):
        """CORS preflight"""
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, PUT, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type, Authorization')
        self.end_headers()
    
    def do_GET(self):
        """GET 요청 라우팅 (get, licenses, performances)"""
        try:
            user = require_auth(self)
            if not user:
                return
            
            parsed_url = urlparse(self.path)
            query_params = parse_qs(parsed_url.query)
            action = query_params.get('action', ['get'])[0]
            
            if action == 'get':
                self.handle_get(user)
            elif action == 'licenses':
                self.handle_licenses(user)
            elif action == 'performances':
                self.handle_performances(user)
            else:
                send_error(self, 400, "Invalid action. Use ?action=get, ?action=licenses, or ?action=performances")
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
    
    def do_PUT(self):
        """PUT 요청 라우팅 (update)"""
        try:
            user = require_auth(self)
            if not user:
                return
            
            parsed_url = urlparse(self.path)
            query_params = parse_qs(parsed_url.query)
            action = query_params.get('action', [''])[0]
            
            if action == 'update':
                self.handle_update(user)
            else:
                send_error(self, 400, "Invalid action. Use ?action=update")
        except Exception as e:
            send_error(self, 500, f"Internal server error: {str(e)}")
    
    # ===== GET =====
    def handle_get(self, user: dict):
        """프로필 조회"""
        try:
            result = asyncio.run(self.get_profile(user['user_id']))
            send_json(self, 200, result)
        except Exception as e:
            send_error(self, 500, f"Failed to fetch profile: {str(e)}")
    
    async def get_profile(self, user_id: int):
        """프로필 조회 (DB)"""
        database_url = os.getenv("NEON_DATABASE_URL")
        if not database_url:
            raise ValueError("NEON_DATABASE_URL not configured")
        if database_url.startswith("postgresql://"):
            database_url = database_url.replace("postgresql://", "")
        
        conn = await asyncpg.connect(f"postgresql://{database_url}")
        
        try:
            query = """
                SELECT 
                    id, company_name, brn, location_code, keywords, credit_rating,
                    created_at, updated_at
                FROM user_profiles
                WHERE user_id = $1
            """
            row = await conn.fetchrow(query, user_id)
            
            if not row:
                return {"profile": None, "message": "Profile not found. Please create a profile first."}
            
            return {
                "id": row['id'],
                "company_name": row['company_name'],
                "brn": row['brn'],
                "location_code": row['location_code'],
                "keywords": row['keywords'],
                "credit_rating": row['credit_rating'],
                "created_at": row['created_at'].isoformat() if row['created_at'] else None,
                "updated_at": row['updated_at'].isoformat() if row['updated_at'] else None
            }
        finally:
            await conn.close()
    
    # ===== CREATE =====
    def handle_create(self, user: dict):
        """프로필 생성"""
        try:
            req = parse_json_body(self, CreateProfileRequest)
            if not req:
                return
            
            result = asyncio.run(self.create_profile(user['user_id'], req))
            send_json(self, 201, result)
        except Exception as e:
            send_error(self, 500, f"Failed to create profile: {str(e)}")
    
    async def create_profile(self, user_id: int, req: CreateProfileRequest):
        """프로필 생성 (DB)"""
        database_url = os.getenv("NEON_DATABASE_URL")
        if not database_url:
            raise ValueError("NEON_DATABASE_URL not configured")
        if database_url.startswith("postgresql://"):
            database_url = database_url.replace("postgresql://", "")
        
        conn = await asyncpg.connect(f"postgresql://{database_url}")
        
        try:
            # 기존 프로필 확인
            existing = await conn.fetchrow("SELECT id FROM user_profiles WHERE user_id = $1", user_id)
            if existing:
                raise ValueError("Profile already exists. Use ?action=update to modify.")
            
            # 프로필 생성
            query = """
                INSERT INTO user_profiles (
                    user_id, company_name, brn, location_code, keywords, credit_rating
                )
                VALUES ($1, $2, $3, $4, $5, $6)
                RETURNING id, company_name, brn, location_code, keywords, credit_rating, created_at
            """
            row = await conn.fetchrow(
                query, user_id, req.company_name, req.brn, 
                req.location_code, req.keywords, req.credit_rating
            )
            
            return {
                "id": row['id'],
                "company_name": row['company_name'],
                "brn": row['brn'],
                "location_code": row['location_code'],
                "keywords": row['keywords'],
                "credit_rating": row['credit_rating'],
                "created_at": row['created_at'].isoformat(),
                "message": "Profile created successfully"
            }
        finally:
            await conn.close()
    
    # ===== UPDATE =====
    def handle_update(self, user: dict):
        """프로필 수정"""
        try:
            req = parse_json_body(self, UpdateProfileRequest)
            if not req:
                return
            
            result = asyncio.run(self.update_profile(user['user_id'], req))
            send_json(self, 200, result)
        except Exception as e:
            send_error(self, 500, f"Failed to update profile: {str(e)}")
    
    async def update_profile(self, user_id: int, req: UpdateProfileRequest):
        """프로필 수정 (DB)"""
        database_url = os.getenv("NEON_DATABASE_URL")
        if not database_url:
            raise ValueError("NEON_DATABASE_URL not configured")
        if database_url.startswith("postgresql://"):
            database_url = database_url.replace("postgresql://", "")
        
        conn = await asyncpg.connect(f"postgresql://{database_url}")
        
        try:
            # 기존 프로필 확인
            existing = await conn.fetchrow("SELECT id FROM user_profiles WHERE user_id = $1", user_id)
            if not existing:
                raise ValueError("Profile not found. Use ?action=create first.")
            
            # 업데이트할 필드만 동적으로 구성
            update_fields = []
            params = [user_id]
            param_index = 2
            
            if req.company_name is not None:
                update_fields.append(f"company_name = ${param_index}")
                params.append(req.company_name)
                param_index += 1
            
            if req.brn is not None:
                update_fields.append(f"brn = ${param_index}")
                params.append(req.brn)
                param_index += 1
            
            if req.location_code is not None:
                update_fields.append(f"location_code = ${param_index}")
                params.append(req.location_code)
                param_index += 1
            
            if req.keywords is not None:
                update_fields.append(f"keywords = ${param_index}")
                params.append(req.keywords)
                param_index += 1
            
            if req.credit_rating is not None:
                update_fields.append(f"credit_rating = ${param_index}")
                params.append(req.credit_rating)
                param_index += 1
            
            if not update_fields:
                raise ValueError("No fields to update")
            
            update_fields.append(f"updated_at = NOW()")
            
            query = f"""
                UPDATE user_profiles
                SET {', '.join(update_fields)}
                WHERE user_id = $1
                RETURNING id, company_name, brn, location_code, keywords, credit_rating, updated_at
            """
            
            row = await conn.fetchrow(query, *params)
            
            return {
                "id": row['id'],
                "company_name": row['company_name'],
                "brn": row['brn'],
                "location_code": row['location_code'],
                "keywords": row['keywords'],
                "credit_rating": row['credit_rating'],
                "updated_at": row['updated_at'].isoformat(),
                "message": "Profile updated successfully"
            }
        finally:
            await conn.close()
    
    # ===== LICENSES =====
    def handle_licenses(self, user: dict):
        """보유 면허 조회"""
        try:
            result = asyncio.run(self.get_licenses(user['user_id']))
            send_json(self, 200, result)
        except Exception as e:
            send_error(self, 500, f"Failed to fetch licenses: {str(e)}")
    
    async def get_licenses(self, user_id: int):
        """보유 면허 조회 (DB)"""
        database_url = os.getenv("NEON_DATABASE_URL")
        if not database_url:
            raise ValueError("NEON_DATABASE_URL not configured")
        if database_url.startswith("postgresql://"):
            database_url = database_url.replace("postgresql://", "")
        
        conn = await asyncpg.connect(f"postgresql://{database_url}")
        
        try:
            # 먼저 프로필 ID 조회
            profile = await conn.fetchrow("SELECT id FROM user_profiles WHERE user_id = $1", user_id)
            if not profile:
                return {"items": [], "total": 0, "message": "Profile not found"}
            
            query = """
                SELECT 
                    id, license_name, license_number, issue_date, 
                    expiry_date, issuing_agency, created_at
                FROM user_licenses
                WHERE profile_id = $1
                ORDER BY issue_date DESC
            """
            rows = await conn.fetch(query, profile['id'])
            
            items = []
            for row in rows:
                items.append({
                    "id": row['id'],
                    "license_name": row['license_name'],
                    "license_number": row['license_number'],
                    "issue_date": row['issue_date'].isoformat() if row['issue_date'] else None,
                    "expiry_date": row['expiry_date'].isoformat() if row['expiry_date'] else None,
                    "issuing_agency": row['issuing_agency'],
                    "created_at": row['created_at'].isoformat() if row['created_at'] else None
                })
            
            return {"items": items, "total": len(items)}
        finally:
            await conn.close()
    
    # ===== PERFORMANCES =====
    def handle_performances(self, user: dict):
        """시공 실적 조회"""
        try:
            result = asyncio.run(self.get_performances(user['user_id']))
            send_json(self, 200, result)
        except Exception as e:
            send_error(self, 500, f"Failed to fetch performances: {str(e)}")
    
    async def get_performances(self, user_id: int):
        """시공 실적 조회 (DB)"""
        database_url = os.getenv("NEON_DATABASE_URL")
        if not database_url:
            raise ValueError("NEON_DATABASE_URL not configured")
        if database_url.startswith("postgresql://"):
            database_url = database_url.replace("postgresql://", "")
        
        conn = await asyncpg.connect(f"postgresql://{database_url}")
        
        try:
            # 먼저 프로필 ID 조회
            profile = await conn.fetchrow("SELECT id FROM user_profiles WHERE user_id = $1", user_id)
            if not profile:
                return {"items": [], "total": 0, "message": "Profile not found"}
            
            query = """
                SELECT 
                    id, project_name, client_name, amount, 
                    start_date, completion_date, project_type, 
                    location, description, created_at
                FROM user_performances
                WHERE profile_id = $1
                ORDER BY completion_date DESC
            """
            rows = await conn.fetch(query, profile['id'])
            
            items = []
            for row in rows:
                items.append({
                    "id": row['id'],
                    "project_name": row['project_name'],
                    "client_name": row['client_name'],
                    "amount": row['amount'],
                    "start_date": row['start_date'].isoformat() if row['start_date'] else None,
                    "completion_date": row['completion_date'].isoformat() if row['completion_date'] else None,
                    "project_type": row['project_type'],
                    "location": row['location'],
                    "description": row['description'],
                    "created_at": row['created_at'].isoformat() if row['created_at'] else None
                })
            
            return {"items": items, "total": len(items)}
        finally:
            await conn.close()
