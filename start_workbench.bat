@echo off
chcp 65001 >nul
echo ========================================
echo   Smart Stack 操盘工作台 - 一键启动
echo ========================================
echo.

REM 启动后端(FastAPI, 端口 8000)
echo [1/2] 启动后端服务 http://localhost:8000 ...
start "SmartStack Backend" cmd /k "cd backend && run.bat"

REM 等后端起来
timeout /t 3 /nobreak >nul

REM 启动前端(Vite, 端口 5173)
echo [2/2] 启动前端工作台 http://localhost:5173 ...
start "SmartStack Frontend" cmd /k "cd frontend && dev.bat"

echo.
echo ========================================
echo   后端: http://localhost:8000/docs  (Swagger)
echo   前端: http://localhost:5173       (工作台)
echo ========================================
echo.
echo 两个窗口已打开,关闭对应窗口即可停止服务。
pause
