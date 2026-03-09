@echo off
title Quick Track - Backend API Server (DO NOT CLOSE)
echo ============================================
echo  Quick Track Check Scanner - Backend API
echo  Running on http://127.0.0.1:8000
echo  Keep this window open while using the app.
echo ============================================
echo.

cd /d "%~dp0"
python -m uvicorn server.main:app --host 127.0.0.1 --port 8000

echo.
echo [ERROR] Backend server has stopped. Press any key to restart...
pause >nul
start "" "%~f0"
