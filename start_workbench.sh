#!/usr/bin/env bash
# Smart Stack 操盘工作台 - 一键启动(macOS/Linux)
set -e
cd "$(dirname "$0")"

echo "========================================"
echo "  Smart Stack 操盘工作台 - 一键启动"
echo "========================================"

echo "[1/2] 启动后端 http://localhost:8000 ..."
(cd backend && PYTHONPATH=. uvicorn app.main:app --reload --port 8000) &
BACKEND_PID=$!

sleep 3

echo "[2/2] 启动前端 http://localhost:5173 ..."
(cd frontend && npm run dev) &
FRONTEND_PID=$!

echo ""
echo "后端 Swagger: http://localhost:8000/docs"
echo "前端工作台:  http://localhost:5173"
echo ""
echo "Ctrl+C 停止所有服务"

trap "kill $BACKEND_PID $FRONTEND_PID 2>/dev/null; exit" INT TERM
wait
