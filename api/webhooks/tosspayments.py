"""
POST /api/webhooks/tosspayments
Tosspayments Webhook Handler

Security: HMAC-SHA256 signature verification (NO JWT authentication)
Events: payment.confirmed, payment.failed, payment.canceled, billing.scheduled
Response: 200 immediately (async processing)

Documentation: https://docs.tosspayments.com/guides/webhook

DATABASE REQUIREMENTS:
This webhook requires the following database schema:

1. Create 'payments' table:
   CREATE TABLE payments (
       id SERIAL PRIMARY KEY,
       order_id TEXT UNIQUE NOT NULL,
       payment_key TEXT,
       user_id INTEGER REFERENCES users(id),
       amount INTEGER NOT NULL,
       status TEXT NOT NULL,  -- 'completed', 'failed', 'canceled'
       payment_data JSONB,
       created_at TIMESTAMP DEFAULT NOW(),
       updated_at TIMESTAMP DEFAULT NOW()
   );

2. Add subscription fields to 'users' table:
   ALTER TABLE users ADD COLUMN subscription_plan TEXT DEFAULT 'free';
   ALTER TABLE users ADD COLUMN subscription_status TEXT DEFAULT 'inactive';
   ALTER TABLE users ADD COLUMN subscription_start_date TIMESTAMP;
   ALTER TABLE users ADD COLUMN subscription_end_date TIMESTAMP;

ENVIRONMENT VARIABLES:
- TOSSPAYMENTS_WEBHOOK_SECRET: Secret for HMAC-SHA256 signature verification
- NEON_DATABASE_URL: PostgreSQL connection string
"""
from http.server import BaseHTTPRequestHandler
import sys
from pathlib import Path
import json
import hmac
import hashlib
import os
import asyncio
from datetime import datetime

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

import asyncpg


class handler(BaseHTTPRequestHandler):
    def do_OPTIONS(self):
        """CORS preflight"""
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type, X-Tosspayments-Signature')
        self.end_headers()
    
    def do_POST(self):
        """
        Webhook endpoint for Tosspayments
        
        NO JWT authentication (external webhook from Tosspayments)
        Verifies HMAC-SHA256 signature instead
        """
        try:
            # 1. Read raw body
            content_length = int(self.headers.get('Content-Length', 0))
            raw_body = self.rfile.read(content_length)
            body_str = raw_body.decode('utf-8')
            
            # 2. Verify HMAC-SHA256 signature
            signature_header = self.headers.get('X-Tosspayments-Signature', '')
            webhook_secret = os.getenv('TOSSPAYMENTS_WEBHOOK_SECRET', '')
            
            if not webhook_secret:
                self.log_error("TOSSPAYMENTS_WEBHOOK_SECRET not configured")
                # Return 200 to prevent retries (log error internally)
                self.send_success_response({"status": "ignored", "reason": "webhook_secret_not_configured"})
                return
            
            if not self.verify_signature(body_str, signature_header, webhook_secret):
                self.log_error("Invalid webhook signature")
                # Return 401 for invalid signature (security)
                self.send_error_response(401, "Invalid signature")
                return
            
            # 3. Parse webhook payload
            payload = json.loads(body_str)
            event_type = payload.get('eventType', '')
            
            # 4. Log webhook event (for debugging)
            self.log_webhook_event(event_type, payload)
            
            # 5. Process webhook event (async)
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            loop.run_until_complete(self.process_webhook_event(event_type, payload))
            loop.close()
            
            # 6. Return 200 immediately (Tosspayments expects quick response)
            self.send_success_response({"status": "success", "event": event_type})
            
        except json.JSONDecodeError:
            self.log_error("Invalid JSON payload")
            # Return 200 to prevent retries (log error internally)
            self.send_success_response({"status": "ignored", "reason": "invalid_json"})
        except Exception as e:
            self.log_error(f"Webhook processing error: {str(e)}")
            # Return 200 even on processing errors (prevent Tosspayments retries)
            self.send_success_response({"status": "error", "message": str(e)})
    
    def verify_signature(self, body: str, signature: str, secret: str) -> bool:
        """
        Verify HMAC-SHA256 signature
        
        Args:
            body: Raw request body (string)
            signature: Signature from X-Tosspayments-Signature header
            secret: TOSSPAYMENTS_WEBHOOK_SECRET from environment
        
        Returns:
            True if signature is valid, False otherwise
        """
        if not signature:
            return False
        
        # Calculate expected signature: HMAC-SHA256(secret, body)
        expected_signature = hmac.new(
            secret.encode('utf-8'),
            body.encode('utf-8'),
            hashlib.sha256
        ).hexdigest()
        
        # Constant-time comparison (prevents timing attacks)
        return hmac.compare_digest(expected_signature, signature)
    
    async def process_webhook_event(self, event_type: str, payload: dict):
        """
        Process webhook event based on event type
        
        Event Types:
        - payment.confirmed: Payment successfully completed
        - payment.failed: Payment failed
        - payment.canceled: Payment canceled/refunded
        - billing.scheduled: Auto-renewal scheduled (subscription)
        
        Args:
            event_type: Event type from webhook
            payload: Full webhook payload
        """
        # Extract common fields
        order_id = payload.get('orderId', '')
        payment_key = payload.get('paymentKey', '')
        status = payload.get('status', '')
        amount = payload.get('totalAmount', 0)
        
        # Get database connection
        database_url = os.getenv("NEON_DATABASE_URL", "")
        if not database_url:
            self.log_error("NEON_DATABASE_URL not configured")
            return
        
        if database_url.startswith("postgresql://"):
            database_url = database_url.replace("postgresql://", "")
        
        try:
            conn = await asyncpg.connect(f"postgresql://{database_url}", timeout=5.0)
        except Exception as e:
            self.log_error(f"Database connection failed: {str(e)}")
            return
        
        try:
            if event_type == 'payment.confirmed':
                await self.handle_payment_confirmed(conn, order_id, payment_key, amount, payload)
            elif event_type == 'payment.failed':
                await self.handle_payment_failed(conn, order_id, payload)
            elif event_type == 'payment.canceled':
                await self.handle_payment_canceled(conn, order_id, payment_key, payload)
            elif event_type == 'billing.scheduled':
                await self.handle_billing_scheduled(conn, payload)
            else:
                self.log_webhook_event(f"Unknown event type: {event_type}", payload)
        finally:
            await conn.close()
    
    async def handle_payment_confirmed(self, conn, order_id: str, payment_key: str, amount: int, payload: dict):
        """
        Handle payment.confirmed event
        
        Actions:
        1. Update payment record status to 'completed'
        2. Update user subscription plan
        3. Send confirmation email (optional)
        
        Note: Requires 'payments' table with columns:
        - order_id (TEXT, UNIQUE)
        - payment_key (TEXT)
        - user_id (INTEGER)
        - amount (INTEGER)
        - status (TEXT)
        - payment_data (JSONB)
        - created_at (TIMESTAMP)
        - updated_at (TIMESTAMP)
        
        Also requires users table to have subscription fields:
        - subscription_plan (TEXT)
        - subscription_status (TEXT)
        - subscription_start_date (TIMESTAMP)
        - subscription_end_date (TIMESTAMP)
        """
        # Extract user_id from order_id (format: BIZ-{user_id}-{plan}-{timestamp})
        try:
            parts = order_id.split('-')
            if len(parts) >= 2:
                user_id = int(parts[1])
            else:
                user_id = None
        except (ValueError, IndexError):
            user_id = None
            self.log_error(f"Failed to extract user_id from order_id: {order_id}")
        
        try:
            # Update payment record
            await conn.execute("""
                INSERT INTO payments (order_id, payment_key, user_id, amount, status, payment_data, created_at, updated_at)
                VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
                ON CONFLICT (order_id) DO UPDATE
                SET status = $5, payment_key = $2, updated_at = NOW()
            """, order_id, payment_key, user_id, amount, 'completed', json.dumps(payload), datetime.now(), datetime.now())
            
            # Update user subscription (if user_id exists)
            if user_id:
                # Extract plan from order_id (format: BIZ-{user_id}-{plan}-{timestamp})
                plan_name = parts[2].lower() if len(parts) >= 3 else 'basic'
                
                await conn.execute("""
                    UPDATE users
                    SET subscription_plan = $1,
                        subscription_status = 'active',
                        subscription_start_date = NOW(),
                        subscription_end_date = NOW() + INTERVAL '30 days',
                        updated_at = NOW()
                    WHERE id = $2
                """, plan_name, user_id)
            
            self.log_webhook_event(f"Payment confirmed: {order_id}, amount: {amount}원", payload)
        except Exception as e:
            self.log_error(f"Failed to update payment/subscription in database: {str(e)}")
            self.log_error("Ensure 'payments' table exists and users table has subscription fields")
            # Don't re-raise - we already logged the webhook event
    
    async def handle_payment_failed(self, conn, order_id: str, payload: dict):
        """
        Handle payment.failed event
        
        Actions:
        1. Update payment record status to 'failed'
        2. Log failure reason
        3. Notify user (optional)
        """
        failure_reason = payload.get('failureMessage', 'Unknown error')
        
        try:
            await conn.execute("""
                INSERT INTO payments (order_id, status, payment_data, created_at, updated_at)
                VALUES ($1, $2, $3, $4, $5)
                ON CONFLICT (order_id) DO UPDATE
                SET status = $2, payment_data = $3, updated_at = NOW()
            """, order_id, 'failed', json.dumps(payload), datetime.now(), datetime.now())
        except Exception as e:
            self.log_error(f"Failed to update payment in database: {str(e)}")
        
        self.log_error(f"Payment failed: {order_id}, reason: {failure_reason}")
    
    async def handle_payment_canceled(self, conn, order_id: str, payment_key: str, payload: dict):
        """
        Handle payment.canceled event
        
        Actions:
        1. Update payment record status to 'canceled'
        2. Update user subscription status to 'canceled'
        3. Log cancellation reason
        """
        cancel_reason = payload.get('cancelReason', 'User requested')
        
        try:
            await conn.execute("""
                UPDATE payments
                SET status = $1, payment_data = $2, updated_at = NOW()
                WHERE order_id = $3
            """, 'canceled', json.dumps(payload), order_id)
            
            # Find user_id from payment record
            row = await conn.fetchrow("""
                SELECT user_id FROM payments WHERE order_id = $1
            """, order_id)
            
            if row and row['user_id']:
                await conn.execute("""
                    UPDATE users
                    SET subscription_status = 'canceled',
                        updated_at = NOW()
                    WHERE id = $1
                """, row['user_id'])
        except Exception as e:
            self.log_error(f"Failed to update payment/subscription in database: {str(e)}")
        
        self.log_webhook_event(f"Payment canceled: {order_id}, reason: {cancel_reason}", payload)
    
    async def handle_billing_scheduled(self, conn, payload: dict):
        """
        Handle billing.scheduled event (auto-renewal)
        
        Actions:
        1. Log scheduled billing
        2. Prepare for next payment cycle
        """
        customer_key = payload.get('customerKey', '')
        billing_date = payload.get('billingDate', '')
        
        self.log_webhook_event(f"Billing scheduled: {customer_key}, date: {billing_date}", payload)
    
    def log_webhook_event(self, message: str, payload: dict = None):
        """
        Log webhook event (for debugging)
        
        Note: Do NOT log sensitive data (card numbers, keys)
        """
        safe_payload = self.sanitize_payload(payload) if payload else {}
        log_entry = {
            "timestamp": datetime.now().isoformat(),
            "message": message,
            "payload": safe_payload
        }
        print(f"[WEBHOOK] {json.dumps(log_entry)}")
    
    def log_error(self, message: str):
        """Log error message"""
        print(f"[WEBHOOK ERROR] {message}")
    
    def sanitize_payload(self, payload: dict) -> dict:
        """
        Remove sensitive data from payload before logging
        
        Removes: card numbers, CVV, etc.
        """
        sensitive_keys = ['cardNumber', 'cvv', 'password', 'secret']
        safe_payload = payload.copy()
        
        for key in sensitive_keys:
            if key in safe_payload:
                safe_payload[key] = '***REDACTED***'
        
        return safe_payload
    
    def send_success_response(self, data: dict):
        """Send 200 JSON response"""
        self.send_response(200)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()
        self.wfile.write(json.dumps(data).encode())
    
    def send_error_response(self, status_code: int, message: str):
        """Send error JSON response"""
        self.send_response(status_code)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()
        error_data = {"error": True, "message": message, "status_code": status_code}
        self.wfile.write(json.dumps(error_data).encode())
