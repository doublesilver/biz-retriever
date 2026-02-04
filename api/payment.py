"""
Unified Payment API
- GET /api/payment?action=subscription - 구독 정보 조회
- GET /api/payment?action=history - 결제 내역 조회
- GET /api/payment?action=status&payment_id=xxx - 결제 상태 조회
"""
from http.server import BaseHTTPRequestHandler
import sys
from pathlib import Path
import json
import asyncio
from urllib.parse import parse_qs, urlparse

sys.path.insert(0, str(Path(__file__).parent.parent))

from lib.auth import require_auth
from lib.utils import send_json, send_error
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
            user = require_auth(self)
            if not user:
                return
            
            parsed_url = urlparse(self.path)
            query_params = parse_qs(parsed_url.query)
            action = query_params.get('action', ['subscription'])[0]
            
            if action == 'subscription':
                self.handle_subscription(user)
            elif action == 'history':
                page = int(query_params.get('page', ['1'])[0])
                page_size = int(query_params.get('page_size', ['20'])[0])
                self.handle_history(user, page, page_size)
            elif action == 'status':
                payment_id = query_params.get('payment_id', [None])[0]
                if not payment_id:
                    send_error(self, 400, "Missing payment_id parameter")
                    return
                self.handle_status(user, payment_id)
            else:
                send_error(self, 400, "Invalid action. Use ?action=subscription, ?action=history, or ?action=status&payment_id=xxx")
        except Exception as e:
            send_error(self, 500, f"Internal server error: {str(e)}")
    
    # ===== SUBSCRIPTION =====
    def handle_subscription(self, user: dict):
        """구독 정보 조회"""
        try:
            result = asyncio.run(self.get_subscription(user['user_id']))
            send_json(self, 200, result)
        except Exception as e:
            send_error(self, 500, f"Failed to fetch subscription: {str(e)}")
    
    async def get_subscription(self, user_id: int):
        """구독 정보 조회 (DB)"""
        database_url = os.getenv("NEON_DATABASE_URL")
        if not database_url:
            raise ValueError("NEON_DATABASE_URL not configured")
        if database_url.startswith("postgresql://"):
            database_url = database_url.replace("postgresql://", "")
        
        conn = await asyncpg.connect(f"postgresql://{database_url}")
        
        try:
            query = """
                SELECT 
                    id, plan_name, is_active, 
                    stripe_subscription_id, stripe_customer_id,
                    current_period_start, current_period_end,
                    cancel_at_period_end, canceled_at,
                    created_at, updated_at
                FROM subscriptions
                WHERE user_id = $1
                ORDER BY created_at DESC
                LIMIT 1
            """
            row = await conn.fetchrow(query, user_id)
            
            if not row:
                # 구독이 없으면 Free 플랜 반환
                return {
                    "plan_name": "free",
                    "is_active": True,
                    "current_period_start": None,
                    "current_period_end": None,
                    "cancel_at_period_end": False,
                    "message": "No active subscription. Using free plan."
                }
            
            return {
                "id": row['id'],
                "plan_name": row['plan_name'],
                "is_active": row['is_active'],
                "stripe_subscription_id": row['stripe_subscription_id'],
                "stripe_customer_id": row['stripe_customer_id'],
                "current_period_start": row['current_period_start'].isoformat() if row['current_period_start'] else None,
                "current_period_end": row['current_period_end'].isoformat() if row['current_period_end'] else None,
                "cancel_at_period_end": row['cancel_at_period_end'],
                "canceled_at": row['canceled_at'].isoformat() if row['canceled_at'] else None,
                "created_at": row['created_at'].isoformat() if row['created_at'] else None,
                "updated_at": row['updated_at'].isoformat() if row['updated_at'] else None
            }
        finally:
            await conn.close()
    
    # ===== HISTORY =====
    def handle_history(self, user: dict, page: int, page_size: int):
        """결제 내역 조회"""
        try:
            if page < 1:
                page = 1
            if page_size < 1 or page_size > 100:
                page_size = 20
            
            result = asyncio.run(self.get_payment_history(user['user_id'], page, page_size))
            send_json(self, 200, result)
        except Exception as e:
            send_error(self, 500, f"Failed to fetch payment history: {str(e)}")
    
    async def get_payment_history(self, user_id: int, page: int, page_size: int):
        """결제 내역 조회 (DB)"""
        database_url = os.getenv("NEON_DATABASE_URL")
        if not database_url:
            raise ValueError("NEON_DATABASE_URL not configured")
        if database_url.startswith("postgresql://"):
            database_url = database_url.replace("postgresql://", "")
        
        conn = await asyncpg.connect(f"postgresql://{database_url}")
        
        try:
            # 총 개수 조회
            count_query = "SELECT COUNT(*) FROM payment_history WHERE user_id = $1"
            total = await conn.fetchval(count_query, user_id)
            
            # 페이지네이션
            offset = (page - 1) * page_size
            
            query = """
                SELECT 
                    id, amount, currency, status, payment_method,
                    transaction_id, description,
                    created_at, updated_at
                FROM payment_history
                WHERE user_id = $1
                ORDER BY created_at DESC
                LIMIT $2 OFFSET $3
            """
            rows = await conn.fetch(query, user_id, page_size, offset)
            
            items = []
            for row in rows:
                items.append({
                    "id": row['id'],
                    "amount": row['amount'],
                    "currency": row['currency'],
                    "status": row['status'],
                    "payment_method": row['payment_method'],
                    "transaction_id": row['transaction_id'],
                    "description": row['description'],
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
    
    # ===== STATUS =====
    def handle_status(self, user: dict, payment_id: str):
        """결제 상태 조회 (transaction_id 기준)"""
        try:
            result = asyncio.run(self.get_payment_status(user['user_id'], payment_id))
            send_json(self, 200, result)
        except Exception as e:
            send_error(self, 500, f"Failed to fetch payment status: {str(e)}")
    
    async def get_payment_status(self, user_id: int, payment_id: str):
        """결제 상태 조회 (DB)"""
        database_url = os.getenv("NEON_DATABASE_URL")
        if not database_url:
            raise ValueError("NEON_DATABASE_URL not configured")
        if database_url.startswith("postgresql://"):
            database_url = database_url.replace("postgresql://", "")
        
        conn = await asyncpg.connect(f"postgresql://{database_url}")
        
        try:
            query = """
                SELECT 
                    id, amount, currency, status, payment_method,
                    transaction_id, description,
                    created_at, updated_at
                FROM payment_history
                WHERE user_id = $1 AND transaction_id = $2
            """
            row = await conn.fetchrow(query, user_id, payment_id)
            
            if not row:
                raise ValueError(f"Payment not found: {payment_id}")
            
            return {
                "id": row['id'],
                "amount": row['amount'],
                "currency": row['currency'],
                "status": row['status'],
                "payment_method": row['payment_method'],
                "transaction_id": row['transaction_id'],
                "description": row['description'],
                "created_at": row['created_at'].isoformat() if row['created_at'] else None,
                "updated_at": row['updated_at'].isoformat() if row['updated_at'] else None
            }
        finally:
            await conn.close()
