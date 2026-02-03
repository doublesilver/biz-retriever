# Tosspayments Webhook Handler

## Overview

This webhook endpoint receives payment notifications from Tosspayments and processes them securely using HMAC-SHA256 signature verification.

**Endpoint:** `POST /api/webhooks/tosspayments`

**Security:** NO JWT authentication (external webhook) - Uses HMAC-SHA256 signature verification

## Supported Events

| Event Type | Description | Actions |
|------------|-------------|---------|
| `payment.confirmed` | Payment successfully completed | Update payment status, activate subscription, send confirmation email |
| `payment.failed` | Payment failed | Log failure reason, notify user |
| `payment.canceled` | Payment canceled/refunded | Update payment status, cancel subscription |
| `billing.scheduled` | Auto-renewal scheduled | Log scheduled billing, prepare for next cycle |

## Setup

### 1. Environment Variables

Add to your `.env` file:

```bash
# Tosspayments Webhook Secret (for signature verification)
TOSSPAYMENTS_WEBHOOK_SECRET=your_webhook_secret_here

# Database (already configured)
NEON_DATABASE_URL=postgresql://user:pass@host/db
```

### 2. Database Schema

Run these SQL commands to create required tables:

```sql
-- Create payments table
CREATE TABLE IF NOT EXISTS payments (
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

CREATE INDEX idx_payments_order_id ON payments(order_id);
CREATE INDEX idx_payments_user_id ON payments(user_id);
CREATE INDEX idx_payments_status ON payments(status);

-- Add subscription fields to users table
ALTER TABLE users ADD COLUMN IF NOT EXISTS subscription_plan TEXT DEFAULT 'free';
ALTER TABLE users ADD COLUMN IF NOT EXISTS subscription_status TEXT DEFAULT 'inactive';
ALTER TABLE users ADD COLUMN IF NOT EXISTS subscription_start_date TIMESTAMP;
ALTER TABLE users ADD COLUMN IF NOT EXISTS subscription_end_date TIMESTAMP;
```

### 3. Configure Tosspayments Dashboard

1. Go to [Tosspayments Dashboard](https://dashboard.tosspayments.com/)
2. Navigate to **개발자 센터** > **웹훅 설정**
3. Add webhook URL:
   - **Production:** `https://your-domain.com/api/webhooks/tosspayments`
   - **Development:** `https://your-vercel-url.vercel.app/api/webhooks/tosspayments`
4. Copy the **웹훅 시크릿 키** to `TOSSPAYMENTS_WEBHOOK_SECRET`
5. Select events to receive:
   - ✅ 결제 승인 (payment.confirmed)
   - ✅ 결제 실패 (payment.failed)
   - ✅ 결제 취소 (payment.canceled)
   - ✅ 자동결제 예약 (billing.scheduled)

## Testing

### Manual Test with curl

```bash
# Generate HMAC-SHA256 signature
WEBHOOK_SECRET="your_webhook_secret"
PAYLOAD='{"eventType":"payment.confirmed","orderId":"BIZ-123-PRO-20260203","paymentKey":"test_payment_key","totalAmount":30000,"status":"DONE"}'
SIGNATURE=$(echo -n "$PAYLOAD" | openssl dgst -sha256 -hmac "$WEBHOOK_SECRET" | awk '{print $2}')

# Send test webhook
curl -X POST https://your-domain.com/api/webhooks/tosspayments \
  -H "Content-Type: application/json" \
  -H "X-Tosspayments-Signature: $SIGNATURE" \
  -d "$PAYLOAD"
```

### Expected Response

```json
{
  "status": "success",
  "event": "payment.confirmed"
}
```

### Error Responses

| Status | Response | Reason |
|--------|----------|--------|
| 401 | `{"error": true, "message": "Invalid signature"}` | HMAC signature mismatch |
| 200 | `{"status": "ignored", "reason": "webhook_secret_not_configured"}` | Environment variable not set |
| 200 | `{"status": "ignored", "reason": "invalid_json"}` | Malformed JSON payload |
| 200 | `{"status": "error", "message": "..."}` | Processing error (still returns 200 to prevent retries) |

## Webhook Payload Examples

### payment.confirmed

```json
{
  "eventType": "payment.confirmed",
  "orderId": "BIZ-123-PRO-20260203120000",
  "paymentKey": "tviva20240203120000ABC123",
  "orderName": "프로 플랜 - 월간 구독",
  "status": "DONE",
  "totalAmount": 30000,
  "method": "카드",
  "approvedAt": "2026-02-03T12:00:00+09:00",
  "card": {
    "issuerCode": "61",
    "acquirerCode": "11",
    "number": "433012******1234",
    "installmentPlanMonths": 0,
    "isInterestFree": false,
    "cardType": "신용"
  }
}
```

### payment.failed

```json
{
  "eventType": "payment.failed",
  "orderId": "BIZ-123-PRO-20260203120000",
  "status": "FAILED",
  "failureCode": "PAY_PROCESS_CANCELED",
  "failureMessage": "사용자가 결제를 취소하였습니다."
}
```

### payment.canceled

```json
{
  "eventType": "payment.canceled",
  "orderId": "BIZ-123-PRO-20260203120000",
  "paymentKey": "tviva20240203120000ABC123",
  "status": "CANCELED",
  "cancelReason": "고객 변심",
  "canceledAt": "2026-02-03T13:00:00+09:00",
  "cancels": [
    {
      "cancelAmount": 30000,
      "cancelReason": "고객 변심",
      "canceledAt": "2026-02-03T13:00:00+09:00"
    }
  ]
}
```

## Security Features

1. **HMAC-SHA256 Signature Verification**
   - Prevents unauthorized webhook calls
   - Uses constant-time comparison to prevent timing attacks

2. **NO JWT Authentication**
   - Webhooks are external requests from Tosspayments
   - Authentication via signature instead of JWT

3. **Sanitized Logging**
   - Sensitive data (card numbers, CVV) are redacted from logs
   - Full payload stored in database for debugging

4. **Immediate 200 Response**
   - Returns 200 even on processing errors
   - Prevents Tosspayments from retrying on internal errors

## Monitoring

Check webhook logs:

```bash
# View webhook events
tail -f /var/log/webhooks.log | grep "WEBHOOK"

# View errors only
tail -f /var/log/webhooks.log | grep "WEBHOOK ERROR"
```

## Troubleshooting

### Issue: Invalid signature error

**Cause:** TOSSPAYMENTS_WEBHOOK_SECRET mismatch

**Solution:**
1. Check `.env` file has correct `TOSSPAYMENTS_WEBHOOK_SECRET`
2. Verify secret matches Tosspayments dashboard
3. Ensure no extra whitespace in secret key

### Issue: Database connection failed

**Cause:** NEON_DATABASE_URL not configured or invalid

**Solution:**
1. Verify `NEON_DATABASE_URL` in `.env`
2. Test connection: `psql $NEON_DATABASE_URL`
3. Check Vercel environment variables

### Issue: Payments table does not exist

**Cause:** Database migration not run

**Solution:**
Run the SQL schema from Setup section above

## Development

### Local Testing with Ngrok

```bash
# Start ngrok tunnel
ngrok http 3000

# Update Tosspayments dashboard with ngrok URL
# https://abc123.ngrok.io/api/webhooks/tosspayments

# Watch logs
npm run dev
```

### Vercel Deployment

Webhook is automatically deployed when pushing to `main` branch.

**Webhook URL:** `https://your-vercel-url.vercel.app/api/webhooks/tosspayments`

## References

- [Tosspayments Webhook Documentation](https://docs.tosspayments.com/guides/webhook)
- [Tosspayments Dashboard](https://dashboard.tosspayments.com/)
- [HMAC-SHA256 Verification](https://docs.tosspayments.com/guides/webhook#webhook-signature-verification)
