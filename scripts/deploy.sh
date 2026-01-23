#!/bin/bash
# Production Deployment Script for Biz-Retriever

set -e  # Exit on error

echo "🚀 Starting Biz-Retriever Production Deployment..."

# 1. Pull latest changes
echo "📥 Pulling latest code..."
git pull origin main

# 2. Install/Update dependencies
echo "📦 Installing dependencies..."
pip install -r requirements.txt --upgrade

# 3. Stop existing services
echo "🛑 Stopping existing services..."
docker-compose down

# 4. Start Docker services
echo "🐳 Starting Docker services..."
docker-compose -f docker-compose.yml up -d

# 5. Wait for database
echo "⏳ Waiting for database..."
sleep 10

# 6. Run migrations
echo "🔄 Running database migrations..."
alembic upgrade head

# 7. Restart application
echo "♻️ Restarting application..."
docker-compose restart app

# 8. Health check
echo "🏥 Performing health check..."
sleep 5
curl -f http://localhost:8000/health || echo "⚠️ Health check failed"

echo "✅ Deployment complete!"
echo "📊 Access dashboard: http://localhost:8000"
echo "📖 API docs: http://localhost:8000/docs"
