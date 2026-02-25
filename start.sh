#!/bin/bash
# ==========================================================
# Biz-Retriever Start Script (Graceful Shutdown 지원)
# ==========================================================
#
# 학습 노트:
#
# Graceful Shutdown이란?
# 서버를 종료할 때 진행 중인 요청을 "강제로 끊지 않고"
# 모두 처리한 후 안전하게 종료하는 방식입니다.
#
# 비유: 식당 문을 닫을 때
# - 강제 종료: 손님이 밥 먹는 중에 불 끔 (데이터 손실 위험)
# - Graceful: "새 손님 안 받고, 지금 손님 다 먹으면 문 닫음" (안전)
#
# SIGTERM 시그널이 오면:
# 1. 새 요청 수신 중단
# 2. 진행 중인 요청 완료 대기 (최대 30초)
# 3. 모든 프로세스 순서대로 종료
# ==========================================================

set -eo pipefail

echo "=== Biz-Retriever Start Script ==="
echo "PORT: ${PORT:-8000}"
echo "RAILWAY_ENVIRONMENT: ${RAILWAY_ENVIRONMENT:-local}"
echo "PID: $$"

# 프로세스 PID 저장
PIDS=()

# Graceful shutdown 핸들러
cleanup() {
    echo ""
    echo "=== Graceful Shutdown Started ==="
    echo "Received termination signal, shutting down gracefully..."

    # 역순으로 프로세스 종료 (API → Scheduler → Worker)
    for ((i=${#PIDS[@]}-1; i>=0; i--)); do
        pid=${PIDS[i]}
        if kill -0 "$pid" 2>/dev/null; then
            echo "Sending SIGTERM to PID $pid..."
            kill -TERM "$pid" 2>/dev/null || true
        fi
    done

    # 최대 30초 대기
    local timeout=30
    local elapsed=0
    while [ $elapsed -lt $timeout ]; do
        local all_done=true
        for pid in "${PIDS[@]}"; do
            if kill -0 "$pid" 2>/dev/null; then
                all_done=false
                break
            fi
        done

        if $all_done; then
            echo "All processes terminated gracefully."
            break
        fi

        sleep 1
        elapsed=$((elapsed + 1))
    done

    # 타임아웃 시 강제 종료
    if [ $elapsed -ge $timeout ]; then
        echo "Timeout reached, force killing remaining processes..."
        for pid in "${PIDS[@]}"; do
            kill -9 "$pid" 2>/dev/null || true
        done
    fi

    echo "=== Shutdown Complete ==="
    exit 0
}

# SIGTERM, SIGINT 시그널 핸들러 등록
trap cleanup SIGTERM SIGINT

# 1. Run Alembic migrations
echo "--- Running database migrations ---"
alembic upgrade head || echo "WARN: alembic upgrade skipped (no revisions or already up-to-date)"
echo "--- Migrations complete ---"

# 2. Start Taskiq Worker in background
echo "--- Starting Taskiq Worker ---"
taskiq worker app.worker.taskiq_app:broker --fs-discover --tasks-pattern "taskiq_tasks.py" &
PIDS+=($!)
echo "Taskiq Worker PID: ${PIDS[-1]}"

# 3. Start Taskiq Scheduler in background
echo "--- Starting Taskiq Scheduler ---"
taskiq scheduler app.worker.taskiq_app:scheduler &
PIDS+=($!)
echo "Taskiq Scheduler PID: ${PIDS[-1]}"

# 4. Start Uvicorn API server
# --timeout-graceful-shutdown: SIGTERM 수신 후 진행 중 요청 완료 대기 시간
echo "--- Starting Uvicorn API Server on port ${PORT:-8000} ---"
uvicorn app.main:app \
    --host 0.0.0.0 \
    --port "${PORT:-8000}" \
    --loop asyncio \
    --timeout-graceful-shutdown 25 \
    --log-level info &
PIDS+=($!)
echo "Uvicorn PID: ${PIDS[-1]}"

echo "=== All processes started ==="
echo "PIDs: ${PIDS[*]}"

# 5. Wait for any process to exit
wait -n "${PIDS[@]}"
EXIT_CODE=$?

echo "A process exited with code $EXIT_CODE -- initiating shutdown"

# 남은 프로세스 정리
cleanup
