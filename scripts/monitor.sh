#!/bin/bash
# 리소스 모니터링 스크립트

echo "📊 Biz-Retriever 리소스 사용량"
echo "================================"
echo ""

# 전체 시스템 메모리
echo "💾 시스템 메모리:"
free -h
echo ""

# Docker 컨테이너 리소스
echo "🐳 컨테이너 리소스 사용량:"
docker stats --no-stream --format "table {{.Container}}\t{{.CPUPerc}}\t{{.MemUsage}}\t{{.MemPerc}}"
echo ""

# 디스크 사용량
echo "💿 디스크 사용량:"
df -h | grep -E "Filesystem|/dev/root|/dev/mmcblk"
echo ""

# 컨테이너 상태
echo "📦 컨테이너 상태:"
docker compose -f docker-compose.pi.yml ps
echo ""

# CPU 온도 (라즈베리파이)
if command -v vcgencmd &> /dev/null; then
    echo "🌡️  CPU 온도:"
    vcgencmd measure_temp
    echo ""
fi

# 로그 파일 크기
echo "📝 로그 파일 크기:"
du -sh logs/
echo ""
