@echo off
cd /d "%~dp0\.."
title Quick Track - FORCE RESTART
echo [1/4] Killing all stuck Python and Uvicorn processes...
taskkill /F /IM python.exe /T >nul 2>&1
taskkill /F /IM uvicorn.exe /T >nul 2>&1

echo [2/4] Ensuring all AI dependencies are installed in .venv...
if exist .venv\Scripts\pip.exe (
    .venv\Scripts\pip install opencv-python-headless pdfplumber pymupdf
) else (
    echo [ERROR] .venv not found! Please create it first.
    pause
    exit
)

echo [3/4] Clearing Python cache...
for /d /r . %%d in (__pycache__) do @if exist "%%d" rd /s /q "%%d"

echo [4/4] Starting fresh Backend server...
echo ------------------------------------------------------------
echo LOOK FOR THIS LOG: "Manual Ranges: checks=9-19"
echo ------------------------------------------------------------
.venv\Scripts\python -m uvicorn server.main:app --host 127.0.0.1 --port 8000 --reload
pause
