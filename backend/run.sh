#!/usr/bin/env bash
# 启动后端开发服务器
cd "$(dirname "$0")"
export PYTHONPATH=.
uvicorn app.main:app --reload --port 8000
