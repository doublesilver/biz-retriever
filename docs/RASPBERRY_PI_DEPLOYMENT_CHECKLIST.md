# Raspberry Pi Deployment Checklist

## Pre-Deployment Requirements

### Hardware
- [ ] Raspberry Pi 5 (4GB RAM minimum)
- [ ] microSD card (32GB+ recommended, Class 10 or UHS-I)
- [ ] Stable internet connection
- [ ] Power supply (official 27W USB-C recommended)
- [ ] (Optional) Cooling case or fan

### Software
- [ ] Raspberry Pi OS (64-bit) installed
- [ ] Docker & Docker Compose installed
- [ ] Git installed
- [ ] SSH access configured

---

## Step 1: Environment Setup

### 1.1 Clone Repository
```bash
cd ~
git clone https://github.com/yourusername/biz-retriever.git
cd biz-retriever
```

### 1.2 Create Environment File
```bash
cp .env.example .env
```

### 1.3 Configure Required Variables
Edit `.env` and set the following **REQUIRED** values:

#### Security (CRITICAL)
```bash
# Generate a strong secret key
python3 -c "import secrets; print(secrets.token_urlsafe(64))"

# Paste the output here
SECRET_KEY=<generated-secret-key>
```

#### Database Credentials
```bash
POSTGRES_USER=admin
POSTGRES_PASSWORD=<strong-password-here>
POSTGRES_DB=biz_retriever
```

#### API Keys
```bash
# Get from: https://aistudio.google.com/app/apikey
GEMINI_API_KEY=AIza...

# Get from: https://www.g2b.go.kr/index.jsp (API 신청)
G2B_API_KEY=<your-g2b-key>
```

#### Production Domain
```bash
# Your Tailscale domain or public IP
PRODUCTION_DOMAIN=https://leeeunseok.tail32c3e2.ts.net
```

### 1.4 Verify Environment File
```bash
bash scripts/verify-env.sh
```

---

## Step 2: SSL Certificate Setup

### Option A: Using Nginx Proxy Manager (Recommended)
1. Access Nginx Proxy Manager: `http://<pi-ip>:81`
2. Default credentials: `admin@example.com` / `changeme`
3. **CHANGE PASSWORD IMMEDIATELY**
4. Add Proxy Host:
   - Domain: `leeeunseok.tail32c3e2.ts.net`
   - Forward to: `api:8000`
   - Enable SSL with Let's Encrypt
   - Force SSL: YES
   - HTTP/2: YES
5. Request certificate (auto-renewal configured)

### Option B: Manual Certbot
```bash
sudo certbot certonly --standalone -d leeeunseok.tail32c3e2.ts.net
```

**Verification:**
```bash
bash scripts/verify-ssl.sh
```

---

## Step 3: Database Migration

### 3.1 Run Alembic Migrations
```bash
# Inside the running API container
docker-compose -f docker-compose.pi.yml exec api python -m alembic upgrade head
```

### 3.2 Verify Tables Created
```bash
docker-compose -f docker-compose.pi.yml exec db psql -U admin -d biz_retriever -c "\dt"
```

Expected tables:
- users
- user_profiles
- user_licenses
- user_performances
- bid_announcements
- bid_results
- subscriptions
- payment_history
- exclude_keywords
- user_keywords
- crawler_logs

---

## Step 4: Launch Services

### 4.1 Start Docker Compose
```bash
docker-compose -f docker-compose.pi.yml up -d
```

### 4.2 Monitor Startup
```bash
docker-compose -f docker-compose.pi.yml logs -f
```

Wait for:
- `✅ Database tables created`
- `✅ Redis cache initialized`
- `✅ Prometheus metrics initialized`
- `🎉 Application startup complete!`

Press `Ctrl+C` to exit logs (containers keep running)

### 4.3 Check Container Status
```bash
docker-compose -f docker-compose.pi.yml ps
```

All containers should show `Up` status:
- api
- db
- redis
- celery_worker
- celery_beat
- nginx
- prometheus
- grafana
- alertmanager
- postgres_exporter
- redis_exporter

---

## Step 5: Health Checks

### 5.1 API Health
```bash
curl -X GET http://localhost:8000/health
```
Expected: `{"status": "ok", "service": "Biz-Retriever", "version": "1.0.0"}`

### 5.2 Frontend Access
```bash
curl -I http://localhost:8081
```
Expected: `HTTP/1.1 200 OK`

### 5.3 Database Connection
```bash
docker-compose -f docker-compose.pi.yml exec api python -c "from app.db.session import engine; import asyncio; asyncio.run(engine.dispose())"
```
Expected: No errors

### 5.4 Redis Connection
```bash
docker-compose -f docker-compose.pi.yml exec redis redis-cli ping
```
Expected: `PONG`

### 5.5 Celery Worker
```bash
docker-compose -f docker-compose.pi.yml logs celery_worker | tail -20
```
Expected: `[2026-01-30 ...] [INFO] celery@... ready.`

---

## Step 6: Monitoring Setup

### 6.1 Access Prometheus
- URL: `http://<pi-ip>:9090`
- Verify targets: Status > Targets
  - api (http://api:8000/metrics)
  - postgres_exporter
  - redis_exporter
- All should show `UP` status

### 6.2 Access Grafana
- URL: `http://<pi-ip>:3000`
- Default credentials: `admin` / `admin`
- **CHANGE PASSWORD IMMEDIATELY**
- Dashboards pre-configured:
  - Biz-Retriever System Metrics
  - PostgreSQL Database Metrics
  - Redis Metrics

### 6.3 Configure Alert Manager (Slack)
Edit `monitoring/alertmanager.yml`:
```yaml
receivers:
  - name: 'slack'
    slack_configs:
      - api_url: '<your-slack-webhook-url>'
        channel: '#biz-retriever-alerts'
```

Reload:
```bash
docker-compose -f docker-compose.pi.yml restart alertmanager
```

---

## Step 7: Backup Configuration

### 7.1 Setup Automated Backups
```bash
# Add cron job
crontab -e

# Add this line (daily 3 AM backup)
0 3 * * * /home/pi/biz-retriever/scripts/backup-db.sh
```

### 7.2 Test Backup
```bash
bash scripts/backup-db.sh
```

### 7.3 Verify Backup
```bash
bash scripts/verify-backup.sh
```

### 7.4 Test Restore (IMPORTANT - Test on non-production DB first)
```bash
bash scripts/test-restore.sh
```

---

## Step 8: Performance Testing

### 8.1 Database Performance
```bash
# Run pgbench inside db container
docker-compose -f docker-compose.pi.yml exec db pgbench -i -s 50 biz_retriever
docker-compose -f docker-compose.pi.yml exec db pgbench -c 10 -j 2 -t 1000 biz_retriever
```

Expected TPS: **250+** (with SD card optimizations)

### 8.2 API Load Test
```bash
# Install Apache Bench (if not installed)
sudo apt-get install apache2-utils

# Test API endpoint
ab -n 1000 -c 10 http://localhost:8000/health
```

Expected:
- Requests per second: **100+**
- Time per request (mean): **<100ms**
- Failed requests: **0**

### 8.3 Disk I/O Monitoring
```bash
bash scripts/monitor-disk-io.sh
```

Check:
- Writes per second: **<50** (SD card lifespan optimization)
- Read/Write ratio: **High reads, low writes**

---

## Step 9: Security Hardening

### 9.1 Fail2Ban Configuration
```bash
# Install Fail2Ban
sudo apt-get install fail2ban

# Configure for nginx
sudo cp /etc/fail2ban/jail.conf /etc/fail2ban/jail.local
sudo nano /etc/fail2ban/jail.local
```

Add:
```ini
[nginx-rate-limit]
enabled  = true
port     = http,https
filter   = nginx-limit-req
logpath  = /var/log/nginx/error.log
maxretry = 5
findtime = 600
bantime  = 3600
```

Start:
```bash
sudo systemctl enable fail2ban
sudo systemctl start fail2ban
```

### 9.2 Firewall Rules
```bash
# Enable UFW
sudo ufw enable

# Allow SSH
sudo ufw allow 22/tcp

# Allow HTTP/HTTPS (if public)
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp

# Allow Tailscale (if using)
sudo ufw allow 41641/udp

# Check status
sudo ufw status
```

### 9.3 Update System
```bash
sudo apt-get update && sudo apt-get upgrade -y
```

---

## Step 10: Final Verification

### 10.1 Full System Test
```bash
# Run comprehensive test
bash scripts/deployment-verification.sh
```

### 10.2 Check Logs for Errors
```bash
docker-compose -f docker-compose.pi.yml logs --tail=100 | grep -i error
```

Expected: No critical errors

### 10.3 Test User Registration
1. Navigate to `https://leeeunseok.tail32c3e2.ts.net`
2. Register new account
3. Login
4. Add test license and performance
5. Trigger crawl
6. Verify bid appears in dashboard

---

## Post-Deployment Monitoring

### Daily Checks
- [ ] Check Grafana dashboard for anomalies
- [ ] Verify backup completed (check Slack notifications)
- [ ] Monitor disk usage: `df -h`
- [ ] Check Docker container health: `docker ps`

### Weekly Checks
- [ ] Review Prometheus alerts
- [ ] Check database size growth
- [ ] Verify SSL certificate auto-renewal
- [ ] Review application logs for errors

### Monthly Checks
- [ ] Test backup restore process
- [ ] Update Docker images: `docker-compose pull`
- [ ] Review and rotate logs
- [ ] System security updates

---

## Troubleshooting

### Container Won't Start
```bash
# Check logs
docker-compose -f docker-compose.pi.yml logs <container-name>

# Restart specific container
docker-compose -f docker-compose.pi.yml restart <container-name>

# Full restart
docker-compose -f docker-compose.pi.yml down
docker-compose -f docker-compose.pi.yml up -d
```

### Database Connection Issues
```bash
# Check PostgreSQL is running
docker-compose -f docker-compose.pi.yml exec db pg_isready

# Check credentials in .env match docker-compose.pi.yml
```

### High Memory Usage
```bash
# Check container memory
docker stats

# Restart services if needed
docker-compose -f docker-compose.pi.yml restart
```

### SSL Certificate Renewal Failed
```bash
# Manual renewal
docker-compose -f docker-compose.pi.yml exec nginx certbot renew

# Check logs
docker-compose -f docker-compose.pi.yml logs nginx | grep certbot
```

---

## Rollback Procedure

If deployment fails:

1. Stop all services:
```bash
docker-compose -f docker-compose.pi.yml down
```

2. Restore database from backup:
```bash
bash scripts/restore-db.sh <backup-file>
```

3. Checkout previous version:
```bash
git checkout <previous-commit-hash>
```

4. Restart services:
```bash
docker-compose -f docker-compose.pi.yml up -d
```

---

## Success Criteria

✅ **Deployment is successful when:**

1. All containers running (`docker ps` shows 11 containers UP)
2. API health check returns 200 OK
3. Frontend accessible via HTTPS
4. SSL certificate valid (green padlock)
5. Database migration complete (all tables exist)
6. Grafana showing live metrics
7. Prometheus targets all UP
8. Backup script runs successfully
9. Test user can register and login
10. Crawl triggers and saves bids to database

---

## Support

For issues or questions:
- Check logs: `docker-compose -f docker-compose.pi.yml logs -f`
- Review documentation: `docs/` directory
- GitHub Issues: https://github.com/yourusername/biz-retriever/issues
