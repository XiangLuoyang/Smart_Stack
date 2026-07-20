@echo off
cd /d "%~dp0"
set PYTHONPATH=.;..
"..\.venv\Scripts\python.exe" -m uvicorn app.main:app --host 0.0.0.0 --port 8000 > run.log 2> run.err.log
