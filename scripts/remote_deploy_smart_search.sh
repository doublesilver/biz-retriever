#!/bin/bash
set -e

REMOTE_DIR="~/projects/biz-retriever"
CONTAINER_API="biz-retriever-api"
CONTAINER_FRONTEND="biz-retriever-frontend"

echo "📦 Injecting files into containers..."

# Backend
sudo docker exec -i $CONTAINER_API tee /app/requirements.txt < requirements.txt > /dev/null
sudo docker exec -u root -i $CONTAINER_API pip install -r /app/requirements.txt

sudo docker exec -i $CONTAINER_API tee /app/app/services/matching_service.py < matching_service.py > /dev/null
sudo docker exec -i $CONTAINER_API tee /app/app/api/endpoints/analysis.py < analysis.py > /dev/null

# Frontend
sudo docker exec -i $CONTAINER_FRONTEND tee /usr/share/nginx/html/dashboard.html < dashboard.html > /dev/null
sudo docker exec -i $CONTAINER_FRONTEND tee /usr/share/nginx/html/js/api.js < api.js > /dev/null
sudo docker exec -i $CONTAINER_FRONTEND tee /usr/share/nginx/html/js/dashboard.js < dashboard.js > /dev/null

echo "🔄 Restarting API container..."
sudo docker compose -f ../docker-compose.pi.yml restart api

echo "✅ Deployment finished successfully!"
