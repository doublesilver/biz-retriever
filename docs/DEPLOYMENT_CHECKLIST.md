# 🚀 Deployment Checklist

## ✅ Pre-Deployment Verification (완료)

### Phase 1: Local Environment Health
- ✅ All containers healthy
  - ✅ API: healthy
  - ✅ Frontend: healthy
  - ✅ Celery Beat: healthy
  - ✅ Celery Worker: healthy
  - ✅ PostgreSQL: healthy
  - ✅ Redis: healthy

### Phase 2: Raspberry Pi Deployment Preparation
- ✅ Environment variables configured (5/5)
  - ✅ POSTGRES_PASSWORD
  - ✅ GEMINI_API_KEY
  - ✅ G2B_API_KEY
  - ✅ SLACK_WEBHOOK_URL
  - ✅ SECRET_KEY

- ✅ Docker Compose configuration validated
  - ✅ docker-compose.pi.yml syntax check passed
  - ✅ Resource limits optimized for 4GB RAM

- ✅ Monitoring stack ready
  - ✅ Prometheus configuration (prometheus.yml)
  - ✅ Alert rules (alert_rules.yml)
  - ✅ Alertmanager configuration (alertmanager.yml)
  - ✅ Grafana datasource (grafana-datasource.yml)
  - ✅ Grafana dashboard (grafana-dashboard-provisioning.yml)

---

## 📦 Deployment Instructions

### Step 1: Transfer Files to Raspberry Pi
```bash
# Method 1: SCP (if using Tailscale)
scp -r C:\sideproject\* admin@<TAILSCALE_IP>:/home/admin/projects/biz-retriever/

# Method 2: Git Clone (recommended)
ssh admin@<TAILSCALE_IP>
cd /home/admin/projects
git clone https://github.com/doublesilver/biz-retriever.git
cd biz-retriever
```

### Step 2: Configure Environment
```bash
# Create .env file on Raspberry Pi
cp .env.example .env
nano .env

# Required variables:
# POSTGRES_PASSWORD=your_secure_password
# GEMINI_API_KEY=your_gemini_key
# G2B_API_KEY=your_g2b_key
# SLACK_WEBHOOK_URL=your_slack_webhook
# SECRET_KEY=$(python scripts/generate_secret_key.py)
```

### Step 3: Deploy with Docker Compose
```bash
# Start all services
docker-compose -f docker-compose.pi.yml up -d

# Check status
docker-compose -f docker-compose.pi.yml ps

# View logs
docker-compose -f docker-compose.pi.yml logs -f
```

### Step 4: Verify Deployment
```bash
# Health checks
curl http://localhost:8000/health
curl http://localhost:3001/

# Monitoring dashboards
http://localhost:9090  # Prometheus
http://localhost:3000  # Grafana (admin/admin)
http://localhost:9093  # Alertmanager
```

---

## 🔍 Post-Deployment Verification

### Critical Services
- [ ] API responds to /health endpoint
- [ ] Frontend loads successfully
- [ ] Database accepts connections
- [ ] Redis cache operational
- [ ] Celery workers processing tasks
- [ ] Celery beat scheduling tasks

### Monitoring
- [ ] Prometheus scraping metrics
- [ ] Grafana dashboards loading
- [ ] Alertmanager receiving alerts
- [ ] Slack notifications working

### Performance
- [ ] API response time < 500ms
- [ ] Database queries < 100ms
- [ ] Memory usage < 3.5GB
- [ ] CPU usage < 80%

---

## 📊 Resource Allocation (4GB RAM)

| Service | Memory Limit | CPU Limit | Reserved Memory |
|---------|--------------|-----------|-----------------|
| PostgreSQL | 1G | 1.0 | 512M |
| Redis | 256M | 0.25 | - |
| API | 1200M | 1.0 | 512M |
| Celery Worker | 512M | 0.5 | - |
| Celery Beat | 512M | 0.5 | - |
| Frontend | 256M | 0.25 | - |
| Prometheus | 512M | 0.5 | 256M |
| Grafana | 256M | 0.5 | - |
| Alertmanager | 128M | 0.25 | - |
| Postgres Exporter | 64M | 0.1 | - |
| Redis Exporter | 32M | 0.1 | - |
| **Total** | **~4.7GB** | **~5.5 CPUs** | **~1.3GB** |

**Note**: Services will share resources dynamically. Peak usage should not exceed 3.5GB.

---

## 🛡️ Security Checklist

- [ ] All default passwords changed
- [ ] Grafana admin password updated
- [ ] PostgreSQL user password strong (16+ chars)
- [ ] SECRET_KEY generated securely
- [ ] Firewall rules configured
- [ ] HTTPS/SSL certificates installed (via Nginx Proxy Manager)
- [ ] Fail2Ban configured for DDoS protection

---

## 📝 Troubleshooting

### Container Won't Start
```bash
# Check logs
docker logs <container_name>

# Inspect health status
docker inspect <container_name> --format='{{json .State.Health}}'

# Restart specific service
docker-compose -f docker-compose.pi.yml restart <service_name>
```

### High Memory Usage
```bash
# Check memory by container
docker stats --no-stream

# Reduce Prometheus retention (if needed)
# Edit monitoring/prometheus.yml:
# --storage.tsdb.retention.time=15d
# --storage.tsdb.retention.size=3GB
```

### Database Performance Issues
```bash
# Run pgbench to verify SD card performance
docker exec -it biz-retriever-db pgbench -i -s 10 biz_retriever
docker exec -it biz-retriever-db pgbench -c 10 -t 1000 biz_retriever

# Expected: 200+ TPS with SD card optimizations
```

---

## 🎯 Success Criteria

Deployment is considered successful when:
- ✅ All 11 containers are healthy
- ✅ Health checks pass for all services
- ✅ Monitoring dashboards accessible
- ✅ Test user can register and login
- ✅ G2B crawler runs successfully
- ✅ Slack notifications delivered
- ✅ System uptime > 99.5% for 24 hours

---

**Prepared**: 2026-01-30  
**Status**: Ready for deployment  
**Estimated deployment time**: 30-45 minutes
