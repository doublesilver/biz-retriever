# Vercel Environment Variables

Complete guide to configuring Biz-Retriever for Vercel deployment with serverless functions.

---

## Overview

Biz-Retriever supports multiple deployment platforms with flexible environment variable configuration. This document covers all required and optional environment variables for Vercel deployment.

### Configuration Priority

The application uses a priority-based configuration system:

```
NEON_DATABASE_URL > DATABASE_URL > POSTGRES_URL > Individual Settings
UPSTASH_REDIS_URL > KV_URL > REDIS_URL > Individual Settings
```

This allows seamless switching between local development and cloud deployment.

---

## Required Secrets

### Database (Neon Postgres with Connection Pooling)

**Environment Variables** (choose one):
- `NEON_DATABASE_URL` - Explicit Neon database URL (recommended)
- `DATABASE_URL` - Generic database URL (Vercel Postgres, Neon, etc.)
- `POSTGRES_URL` - Legacy Vercel Postgres URL

**Format**:
```
postgresql://user:password@host.neon.tech/database?pgbouncer=true
```

**Example**:
```
postgresql://neondb_owner:AbCdEfGhIjKlMnOp@ep-cool-moon-123456.us-east-2.aws.neon.tech/neondb?pgbouncer=true
```

**How to Get**:
1. Create a Neon project at [https://console.neon.tech](https://console.neon.tech)
2. Go to **Connection string** → **Pooling enabled**
3. Copy the connection string
4. Set as `NEON_DATABASE_URL` in Vercel environment variables

**Automatic Features**:
- ✅ Automatic `pgbouncer=true` parameter added on Vercel
- ✅ Scheme conversion: `postgres://` → `postgresql+asyncpg://`
- ✅ Async SQLAlchemy support

---

### Cache (Upstash Redis or Vercel KV)

**Environment Variables** (choose one):
- `UPSTASH_REDIS_URL` - Upstash Redis (recommended for serverless)
- `KV_URL` - Vercel KV (Redis-compatible)
- `REDIS_URL` - Generic Redis URL

**Format**:
```
redis://default:password@host:port
```

**Example (Upstash)**:
```
redis://default:AbCdEfGhIjKlMnOpQrStUvWxYz@us1-cool-moose-12345.upstash.io:6379
```

**How to Get**:

**Option A: Upstash Redis** (Recommended)
1. Create account at [https://upstash.com](https://upstash.com)
2. Create a Redis database
3. Copy the **REST URL** or **Redis CLI** connection string
4. Set as `UPSTASH_REDIS_URL` in Vercel environment variables

**Option B: Vercel KV**
1. In Vercel dashboard, go to **Storage** → **KV**
2. Create a new KV store
3. Copy the connection string
4. Set as `KV_URL` in Vercel environment variables

---

### APIs

#### Google Gemini API (AI Analysis)
- **Variable**: `GEMINI_API_KEY`
- **Get it**: [https://aistudio.google.com/app/apikey](https://aistudio.google.com/app/apikey)
- **Free tier**: 1,500 requests/day
- **Required for**: AI-powered bid analysis and summarization

#### G2B API (나라장터 - Korean Government Procurement)
- **Variable**: `G2B_API_KEY`
- **Get it**: [https://www.data.go.kr](https://www.data.go.kr) (공공데이터포털)
- **Steps**:
  1. Sign up and verify email
  2. Search for "데이터셋 개방표준 서비스" (Dataset Open Standard Service)
  3. Request API key
  4. Approval takes 1-2 business days
- **Required for**: Bid announcement crawling

#### Slack Webhook (Notifications)
- **Variable**: `SLACK_WEBHOOK_URL`
- **Get it**: [https://api.slack.com/apps](https://api.slack.com/apps)
- **Steps**:
  1. Create a new Slack App
  2. Enable **Incoming Webhooks**
  3. Create a new webhook for your channel
  4. Copy the webhook URL
- **Optional**: Can be omitted if notifications not needed

---

### Security

#### JWT Secret Key
- **Variable**: `SECRET_KEY`
- **Format**: 32+ character random string (hex)
- **Generate**:
  ```bash
  openssl rand -hex 32
  # Output: a1b2c3d4e5f6g7h8i9j0k1l2m3n4o5p6q7r8s9t0u1v2w3x4y5z6a7b8c9d0e1f2
  ```
- **Required for**: JWT token signing and verification

#### Cron Job Secret
- **Variable**: `CRON_SECRET`
- **Format**: 32+ character random string
- **Generate**: Same as `SECRET_KEY`
- **Required for**: Protecting scheduled tasks from unauthorized access

---

## Optional Secrets

### Email Notifications (SendGrid)
- **Variable**: `SENDGRID_API_KEY`
- **Get it**: [https://sendgrid.com](https://sendgrid.com)
- **Use case**: Email notifications for bid updates
- **Default**: Disabled if not set

### Payment Processing (Tosspayments)
- **Variables**: 
  - `TOSSPAYMENTS_SECRET_KEY`
  - `TOSSPAYMENTS_CLIENT_KEY`
- **Get it**: [https://toss.im/payments](https://toss.im/payments)
- **Use case**: Payment gateway integration
- **Default**: Disabled if not set

### OpenAI API (Fallback AI)
- **Variable**: `OPENAI_API_KEY`
- **Get it**: [https://platform.openai.com/api-keys](https://platform.openai.com/api-keys)
- **Use case**: Fallback when Gemini API is unavailable
- **Default**: Gemini is preferred if both are set

---

## Vercel Auto-Injected Variables

These are automatically set by Vercel and do NOT need manual configuration:

| Variable | Value | Example |
|----------|-------|---------|
| `VERCEL` | `"1"` | Always "1" on Vercel |
| `VERCEL_ENV` | Environment type | `"production"` \| `"preview"` \| `"development"` |
| `VERCEL_URL` | Deployment URL | `"my-app.vercel.app"` |
| `VERCEL_GIT_COMMIT_SHA` | Git commit hash | `"abc123def456..."` |
| `VERCEL_GIT_COMMIT_MESSAGE` | Commit message | `"feat: add feature"` |

**Usage in Code**:
```python
from app.core.config import settings

if settings.VERCEL == "1":
    # Running on Vercel
    print(f"Deployment URL: {settings.VERCEL_URL}")
    print(f"Environment: {settings.VERCEL_ENV}")
```

---

## Environment Variable Setup in Vercel

### Step 1: Access Project Settings
1. Go to [https://vercel.com/dashboard](https://vercel.com/dashboard)
2. Select your project
3. Click **Settings** → **Environment Variables**

### Step 2: Add Variables
1. Click **Add New**
2. Enter variable name (e.g., `NEON_DATABASE_URL`)
3. Enter variable value
4. Select environments: **Production**, **Preview**, **Development**
5. Click **Save**

### Step 3: Redeploy
After adding environment variables, redeploy your project:
```bash
git push  # Triggers automatic redeploy
# or manually redeploy from Vercel dashboard
```

---

## Configuration Examples

### Minimal Setup (Database + Cache Only)
```bash
# Required
NEON_DATABASE_URL=postgresql://...
UPSTASH_REDIS_URL=redis://...
SECRET_KEY=<32-char-hex-string>

# Optional but recommended
GEMINI_API_KEY=<your-key>
G2B_API_KEY=<your-key>
```

### Full Production Setup
```bash
# Database
NEON_DATABASE_URL=postgresql://...

# Cache
UPSTASH_REDIS_URL=redis://...

# Security
SECRET_KEY=<32-char-hex-string>
CRON_SECRET=<32-char-hex-string>

# APIs
GEMINI_API_KEY=<your-key>
G2B_API_KEY=<your-key>
SLACK_WEBHOOK_URL=https://hooks.slack.com/...

# Optional
SENDGRID_API_KEY=<your-key>
TOSSPAYMENTS_SECRET_KEY=<your-key>
TOSSPAYMENTS_CLIENT_KEY=<your-key>
```

### Local Development Setup
```bash
# Database (local PostgreSQL)
POSTGRES_SERVER=localhost
POSTGRES_USER=admin
POSTGRES_PASSWORD=password
POSTGRES_DB=biz_retriever
POSTGRES_PORT=5432

# Cache (local Redis)
REDIS_HOST=localhost
REDIS_PORT=6379

# Security
SECRET_KEY=<any-32-char-string>

# APIs (optional for testing)
GEMINI_API_KEY=<your-key>
G2B_API_KEY=<your-key>
```

---

## Troubleshooting

### Database Connection Fails
**Symptom**: `psycopg2.OperationalError: could not connect to server`

**Solutions**:
1. Verify `NEON_DATABASE_URL` is correct
2. Check Neon project is active (not paused)
3. Ensure pgbouncer is enabled in connection string
4. Check Vercel logs: `vercel logs <project-name>`

```bash
# Test connection locally
psql "postgresql://user:pass@host/db?pgbouncer=true"
```

### Redis Connection Fails
**Symptom**: `redis.exceptions.ConnectionError: Error 111 connecting`

**Solutions**:
1. Verify `UPSTASH_REDIS_URL` is correct
2. Check Upstash dashboard for active database
3. Ensure firewall allows Redis connections
4. Check Vercel logs for connection errors

```bash
# Test connection locally
redis-cli -u "redis://default:pass@host:port"
```

### API Key Errors
**Symptom**: `401 Unauthorized` or `403 Forbidden`

**Solutions**:
1. Verify API key is correct (no extra spaces)
2. Check API key has required permissions
3. Verify API key is not expired
4. Check API quota/rate limits

### Pgbouncer Parameter Not Added
**Symptom**: Connection pooling not working

**Solution**: The application automatically adds `?pgbouncer=true` when:
- `VERCEL == "1"` (running on Vercel)
- Using `NEON_DATABASE_URL` or `DATABASE_URL`

If manually setting `DATABASE_URL`, ensure it includes `?pgbouncer=true`.

---

## Security Best Practices

### ✅ DO
- ✅ Use Vercel's **Environment Variables** feature (encrypted at rest)
- ✅ Rotate `SECRET_KEY` and `CRON_SECRET` periodically
- ✅ Use separate keys for production and preview environments
- ✅ Enable **Automatic Deployments** only from main branch
- ✅ Use connection pooling (pgbouncer) for database
- ✅ Monitor API usage and set rate limits

### ❌ DON'T
- ❌ Commit `.env` files to Git
- ❌ Share API keys in Slack/Email
- ❌ Use same key for multiple environments
- ❌ Hardcode secrets in code
- ❌ Use weak passwords for database/Redis
- ❌ Expose `SECRET_KEY` in logs or error messages

---

## Monitoring & Debugging

### View Deployment Logs
```bash
# Real-time logs
vercel logs <project-name> --follow

# Specific function logs
vercel logs <project-name> --function api
```

### Check Environment Variables
```bash
# List all environment variables (values hidden)
vercel env list

# View specific variable (value shown)
vercel env pull  # Downloads to .env.local
```

### Test Configuration
```python
# In Python REPL or script
from app.core.config import settings

print(f"Database: {settings.SQLALCHEMY_DATABASE_URI[:50]}...")
print(f"Redis: {settings.get_redis_url[:50]}...")
print(f"Vercel: {settings.VERCEL}")
print(f"Environment: {settings.VERCEL_ENV}")
```

---

## Related Documentation

- [Vercel Deployment Guide](./VERCEL_DEPLOYMENT_FINAL.md)
- [Neon Postgres Setup](https://neon.tech/docs)
- [Upstash Redis Setup](https://upstash.com/docs)
- [Google Gemini API](https://ai.google.dev/docs)
- [G2B API Documentation](https://www.data.go.kr)

---

## Support

For issues or questions:
1. Check [Troubleshooting](#troubleshooting) section
2. Review Vercel logs: `vercel logs <project-name>`
3. Check application logs in Vercel dashboard
4. Open an issue on GitHub with logs and configuration details

---

**Last Updated**: 2026-02-03  
**Version**: 1.0  
**Status**: Production Ready ✅
