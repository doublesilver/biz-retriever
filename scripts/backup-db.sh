#!/bin/bash
# DB 백업 스크립트

DATE=$(date +%Y%m%d_%H%M%S)
BACKUP_DIR="./data/backups"
BACKUP_FILE="$BACKUP_DIR/db_backup_$DATE.sql"

mkdir -p $BACKUP_DIR

echo "📦 데이터베이스 백업 중..."
docker-compose -f docker-compose.pi.yml exec -T postgres pg_dump -U admin biz_retriever > $BACKUP_FILE

if [ $? -eq 0 ]; then
    echo "✅ 백업 완료: $BACKUP_FILE"
    
    # 압축
    gzip $BACKUP_FILE
    echo "✅ 압축 완료: $BACKUP_FILE.gz"
    
    # 7일 이상 된 백업 파일 삭제
    find $BACKUP_DIR -name "*.sql.gz" -mtime +7 -delete
    echo "🧹 오래된 백업 파일 정리 완료"
else
    echo "❌ 백업 실패"
    exit 1
fi
