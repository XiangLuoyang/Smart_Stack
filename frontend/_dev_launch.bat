@echo off
cd /d "%~dp0"
"E:\Program Files\nodejs\node.exe" node_modules\vite\bin\vite.js --host > dev.log 2> dev.err.log
