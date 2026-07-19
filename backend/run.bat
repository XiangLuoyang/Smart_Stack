@echo off
cd /d "%~dp0"
set PYTHONPATH=.
uvicorn app.main:app --reload --port 8000
