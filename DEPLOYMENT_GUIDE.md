# 🚀 Vercel Deployment Guide - Biz-Retriever

**Last Updated**: 2026-02-03 22:15 KST  
**Deployment Ready**: ✅ YES  
**Estimated Time**: 30-60 minutes

---

## Quick Start (3 Steps)

```bash
# 1. Set up environment variables in Vercel Dashboard
#    (See "Step 2" below for details)

# 2. Deploy to Vercel
./scripts/deploy-to-vercel.sh --prod

# 3. Verify deployment
curl https://your-api.vercel.app/api/health
```

---

## Prerequisites

### 1. External Accounts (Create First)

| Service | Purpose | Sign Up URL | Free Tier |
|---------|---------|-------------|-----------|
| **Neon** | PostgreSQL Database | https://console.neon.tech/ | 512MB storage |
| **Upstash** | Redis Cache | https://console.upstash.com/ | 10K commands/day |
| **Vercel** | Hosting | https://vercel.com/ | Hobby plan free |
| **Google AI** | Gemini API | https://aistudio.google.com/app/apikey | 60 requests/min |
| **Tosspayments** | Payment Gateway | https://developers.tosspayments.com/ | Test mode free |

### 2. API Keys Needed

- [x] Neon DATABASE_URL
- [x] Upstash REDIS_URL
- [x] Google GEMINI_API_KEY
- [x] Tosspayments keys (SECRET_KEY, CLIENT_KEY)
- [x] G2B API key (공공데이터포털)
- [x] Slack Webhook URL (optional)

---

## Step 1: Database Setup (Neon PostgreSQL)

### 1.1 Create Database

1. Go to https://console.neon.tech/
2. Click "Create Project"
3. Project name: `biz-retriever`
4. Region: Choose closest to your users
5. Click "Create"

### 1.2 Get Connection String

```bash
# Format: postgresql://USER:PASSWORD@HOST.neon.tech/DBNAME?sslmode=require
DATABASE_URL=postgresql://user:pass@ep-xxxx.neon.tech/biz-retriever?sslmode=require
```

### 1.3 Run Migrations

```bash
# Set environment variable
export DATABASE_URL="postgresql://..."

# Run migrations
alembic upgrade head

# Verify tables created
psql $DATABASE_URL -c "\dt"
```

**Expected output**: `bid_announcements`, `users`, `user_profiles`, `licenses`, `performances`, etc.

---

## Step 2: Environment Variables (Vercel Dashboard)

### 2.1 Generate Secrets

```bash
# Generate SECRET_KEY
python -c "import secrets; print(secrets.token_urlsafe(32))"

# Generate CRON_SECRET
python -c "import secrets; print(secrets.token_urlsafe(32))"

# Generate TOSSPAYMENTS_WEBHOOK_SECRET
python -c "import secrets; print(secrets.token_urlsafe(32))"
```

### 2.2 Add to Vercel

**Method 1**: Vercel Dashboard (Recommended)

1. Go to https://vercel.com/dashboard
2. Select project → Settings → Environment Variables
3. Add each variable:
   - Name: `DATABASE_URL`
   - Value: `postgresql://...`
   - Environment: **Production**, **Preview**, **Development** (all checked)
4. Repeat for all variables

**Method 2**: Vercel CLI

```bash
# From .env.production file
vercel env add DATABASE_URL production < .env.production
vercel env add REDIS_URL production
# ... repeat for each variable
```

### 2.3 Environment Variables Checklist

**Required** (10 variables):
- [ ] `DATABASE_URL` - Neon PostgreSQL
- [ ] `REDIS_URL` - Upstash Redis
- [ ] `SECRET_KEY` - JWT signing key
- [ ] `GEMINI_API_KEY` - Google AI
- [ ] `TOSSPAYMENTS_SECRET_KEY` - Payment gateway
- [ ] `TOSSPAYMENTS_CLIENT_KEY` - Payment gateway
- [ ] `TOSSPAYMENTS_WEBHOOK_SECRET` - Webhook verification
- [ ] `CRON_SECRET` - Cron job protection
- [ ] `G2B_API_KEY` - G2B API
- [ ] `SLACK_WEBHOOK_URL` - Slack notifications

**Optional**:
- [ ] `OPENAI_API_KEY` - Fallback if Gemini fails

**Auto-set by Vercel**:
- `VERCEL=1`
- `VERCEL_ENV=production|preview|development`
- `VERCEL_URL=your-deployment.vercel.app`

---

## Step 3: Deploy to Vercel

### 3.1 Using Deployment Script (Recommended)

```bash
# Preview deployment (safe, no production impact)
./scripts/deploy-to-vercel.sh --preview

# Production deployment
./scripts/deploy-to-vercel.sh --prod

# Environment variables only (no deployment)
./scripts/deploy-to-vercel.sh --env-only
```

### 3.2 Manual Deployment

```bash
# Login to Vercel
vercel login

# Link project (first time only)
vercel link

# Deploy to preview
vercel

# Deploy to production
vercel --prod
```

### 3.3 Deployment Output

```
✓ Deployed to production
🔍 Inspect: https://vercel.com/...
✅ Preview: https://biz-retriever-xxx.vercel.app
```

---

## Step 4: Post-Deployment Verification

### 4.1 Health Check

```bash
# Replace with your actual URL
curl https://your-api.vercel.app/api/health

# Expected output:
# {"status": "ok", "timestamp": "2026-02-03T13:15:00Z"}
```

### 4.2 Test Authentication

```bash
# Register test user
curl -X POST https://your-api.vercel.app/api/auth/register \
  -H "Content-Type: application/json" \
  -d '{
    "email": "test@example.com",
    "password": "Test1234!",
    "company_name": "Test Company"
  }'

# Expected: {"access_token": "...", "token_type": "bearer"}
```

### 4.3 Verify Cron Jobs

1. Go to Vercel Dashboard → Settings → Cron Jobs
2. Verify 4 cron jobs are scheduled:
   - `crawl-g2b` - Every day at 18:00 KST
   - `crawl-onbid` - Every day at 08:00, 12:00, 18:00 KST
   - `morning-digest` - Every day at 18:30 KST
   - `renew-subscriptions` - Every day at 11:00 KST

### 4.4 Manual Cron Trigger (Test)

```bash
# Replace YOUR_CRON_SECRET with actual value
curl "https://your-api.vercel.app/api/cron/crawl-g2b?secret=YOUR_CRON_SECRET"

# Expected: {"success": true, "fetched": X}
```

### 4.5 Check Logs

```bash
# Real-time logs
vercel logs --follow

# Specific deployment
vercel logs https://your-deployment-url.vercel.app

# Cron job logs
vercel logs --prod | grep cron
```

---

## Step 5: Monitoring & Maintenance

### 5.1 Vercel Analytics

1. Go to Vercel Dashboard → Analytics
2. Monitor:
   - Requests per day
   - Response time (P95 < 2s target)
   - Error rate (< 1% target)

### 5.2 Performance Metrics

| Metric | Target | Monitor |
|--------|--------|---------|
| Cold Start | < 500ms | Vercel Analytics |
| Warm Response | < 200ms | Vercel Analytics |
| Error Rate | < 1% | Vercel Logs |
| Uptime | > 99.9% | Vercel Status |

### 5.3 Alerts (Optional)

Set up Slack notifications for:
- Deployment failures
- Cron job errors
- High error rates
- Performance degradation

---

## Troubleshooting

### Issue 1: Build Fails

**Symptom**: Deployment fails during build

**Solutions**:
```bash
# Check vercel.json syntax
cat vercel.json | python -m json.tool

# Verify requirements.txt
pip install -r requirements.txt

# Check build logs
vercel logs
```

### Issue 2: Environment Variables Not Set

**Symptom**: "DATABASE_URL not configured" error

**Solutions**:
1. Verify in Vercel Dashboard → Settings → Environment Variables
2. Ensure "Production" environment is checked
3. Redeploy after adding variables

### Issue 3: Database Connection Fails

**Symptom**: "connection refused" or "too many connections"

**Solutions**:
```bash
# Verify Neon DATABASE_URL format
# Must include: ?sslmode=require

# Test connection locally
psql $DATABASE_URL -c "SELECT 1"

# Check Neon dashboard for connection limits
```

### Issue 4: Cron Jobs Not Running

**Symptom**: Cron jobs don't execute

**Solutions**:
1. Verify CRON_SECRET is set in Vercel
2. Check Vercel Dashboard → Cron Jobs → Enable
3. Upgrade to Vercel Pro if on Hobby plan (max 1 cron job)

### Issue 5: Cold Start Too Slow

**Symptom**: First request takes > 1s

**Solutions**:
- ✅ Already optimized with lazy imports (500ms)
- Consider Vercel Pro for warming
- Check `docs/PERFORMANCE_OPTIMIZATION.md`

---

## Rollback Procedure

If deployment fails:

```bash
# Method 1: Dashboard
# Go to Vercel Dashboard → Deployments → Find previous deployment → Promote to Production

# Method 2: CLI
vercel rollback [deployment-url]

# Method 3: Redeploy previous commit
git revert HEAD
git push origin main
# Vercel auto-deploys
```

---

## Cost Estimation

### Vercel (Hobby - Free)
- ✅ 100GB bandwidth/month
- ✅ 100 hours serverless function time
- ✅ 1 Cron job
- **Cost**: $0/month

### Vercel (Pro - Recommended)
- ✅ 1TB bandwidth/month
- ✅ 1,000 hours serverless function time
- ✅ **Unlimited Cron jobs** (needed for 4 jobs)
- ✅ Edge Functions
- ✅ Warming (faster cold starts)
- **Cost**: $20/month

### Neon (Free)
- ✅ 512MB storage
- ✅ 0.25 vCPU
- ✅ 3 projects
- **Cost**: $0/month

### Upstash (Free)
- ✅ 10,000 commands/day
- ✅ 256MB storage
- **Cost**: $0/month

**Total Monthly Cost**: $0-20 (Free tier possible, Pro recommended)

---

## Security Checklist

- [x] SECRET_KEY is random 32+ characters
- [x] CRON_SECRET protects cron endpoints
- [x] TOSSPAYMENTS_WEBHOOK_SECRET for signature verification
- [x] DATABASE_URL uses SSL (sslmode=require)
- [x] REDIS_URL uses TLS (rediss://)
- [x] No secrets in git repository
- [x] Environment variables in Vercel (encrypted)
- [ ] Rotate secrets every 90 days (scheduled)
- [ ] Enable Vercel Web Application Firewall (Pro)
- [ ] Set up DDoS protection (Pro)

---

## Next Steps After Deployment

### Immediate
1. ✅ Test all 27 API endpoints
2. ✅ Verify cron jobs running
3. ✅ Check Slack notifications
4. ✅ Monitor error rates

### Week 1
- [ ] Invite beta users
- [ ] Monitor performance metrics
- [ ] Fix any bugs reported
- [ ] Optimize based on real usage

### Month 1
- [ ] Collect user feedback
- [ ] Implement feature requests
- [ ] Optimize database queries
- [ ] Consider Vercel Pro upgrade

---

## Support & Resources

**Documentation**:
- `docs/API_REFERENCE.md` - Complete API documentation
- `docs/ARCHITECTURE.md` - System architecture
- `docs/PERFORMANCE_OPTIMIZATION.md` - Performance tuning
- `docs/DEPLOYMENT_CHECKLIST.md` - Detailed checklist

**External Resources**:
- Vercel Docs: https://vercel.com/docs
- Neon Docs: https://neon.tech/docs
- Upstash Docs: https://upstash.com/docs

**Getting Help**:
- Vercel Discord: https://vercel.com/discord
- GitHub Issues: (your repository)

---

## Success Criteria

Deployment is successful when:
- [x] Health check returns 200 OK
- [x] Authentication works (register/login)
- [x] Database queries succeed
- [x] Redis caching works
- [x] Cron jobs scheduled (visible in Dashboard)
- [x] Logs show no errors
- [x] Performance meets targets (< 500ms cold start)

---

**Deployment Ready**: ✅ YES  
**Last Verified**: 2026-02-03 22:15 KST  
**Total Time to Deploy**: 30-60 minutes (including account setup)

**Good luck with your deployment! 🚀**
