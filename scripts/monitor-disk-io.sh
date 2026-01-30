#!/bin/bash
# SD 카드 I/O 모니터링 스크립트
# 목적: PostgreSQL WAL 쓰기 부하 모니터링 및 경고

set -e

THRESHOLD=1000  # kB/s 기준값
INTERVAL=1      # 샘플링 간격 (초)
SAMPLES=10      # 샘플 개수

echo "=== SD 카드 I/O 모니터링 (${INTERVAL}초 간격, ${SAMPLES}회 샘플) ==="
echo "임계값: ${THRESHOLD} kB/s"
echo ""

# 시스템 정보 출력
if command -v lsblk &> /dev/null; then
    echo "📊 SD 카드 정보:"
    lsblk | grep -E "mmcblk|NAME|SIZE" || echo "  (mmcblk 장치 미감지)"
    echo ""
fi

# iostat 명령어 확인
if ! command -v iostat &> /dev/null; then
    echo "⚠️  경고: iostat 명령어를 찾을 수 없습니다."
    echo "   설치: apt-get install sysstat"
    exit 1
fi

# I/O 통계 수집
echo "📈 I/O 통계 (쓰기 속도 kB/s):"
echo "---"

WRITE_SPEEDS=()
TOTAL_WRITE=0

for i in $(seq 1 $SAMPLES); do
    # mmcblk0 또는 sda 등 감지
    DEVICE=$(iostat -x 1 1 2>/dev/null | grep -E "mmcblk0|sda|nvme" | head -1 | awk '{print $1}')
    
    if [ -z "$DEVICE" ]; then
        echo "❌ 에러: 저장소 장치를 감지할 수 없습니다."
        exit 1
    fi
    
    # 쓰기 속도 추출 (kB_wrtn/s 컬럼)
    WRITE_SPEED=$(iostat -x 1 2 2>/dev/null | grep "$DEVICE" | tail -1 | awk '{print $NF}')
    
    if [ -z "$WRITE_SPEED" ]; then
        WRITE_SPEED=0
    fi
    
    WRITE_SPEEDS+=($WRITE_SPEED)
    TOTAL_WRITE=$(echo "$TOTAL_WRITE + $WRITE_SPEED" | bc)
    
    printf "  [%2d/%2d] %s: %.2f kB/s\n" "$i" "$SAMPLES" "$DEVICE" "$WRITE_SPEED"
done

echo "---"

# 평균 계산
AVG_WRITE=$(echo "scale=2; $TOTAL_WRITE / $SAMPLES" | bc)
echo ""
echo "📊 결과:"
echo "  평균 쓰기 속도: $AVG_WRITE kB/s"

# 경고 판정
if (( $(echo "$AVG_WRITE > $THRESHOLD" | bc -l) )); then
    echo ""
    echo "⚠️  경고: 쓰기 속도 초과!"
    echo "  현재: $AVG_WRITE kB/s > 임계값: $THRESHOLD kB/s"
    echo ""
    echo "💡 권장 조치:"
    echo "  1. PostgreSQL 설정 확인:"
    echo "     docker-compose -f docker-compose.pi.yml exec postgres \\"
    echo "       psql -U admin -d biz_retriever -c \"SHOW synchronous_commit;\""
    echo "  2. 활성 쿼리 확인:"
    echo "     docker-compose -f docker-compose.pi.yml exec postgres \\"
    echo "       psql -U admin -d biz_retriever -c \"SELECT pid, query FROM pg_stat_activity WHERE state != 'idle';\""
    echo "  3. WAL 아카이빙 상태 확인:"
    echo "     docker-compose -f docker-compose.pi.yml exec postgres \\"
    echo "       psql -U admin -d biz_retriever -c \"SHOW wal_level;\""
    
    # Slack 알림 (선택사항)
    if [ -n "$SLACK_WEBHOOK_URL" ]; then
        curl -X POST "$SLACK_WEBHOOK_URL" \
            -H 'Content-Type: application/json' \
            -d "{\"text\": \"⚠️ PostgreSQL I/O 경고: $AVG_WRITE kB/s (임계값: $THRESHOLD kB/s)\"}" \
            2>/dev/null || true
    fi
    
    exit 1
else
    echo "  ✅ 정상 범위 내"
    exit 0
fi
