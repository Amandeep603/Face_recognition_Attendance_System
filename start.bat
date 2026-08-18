@echo off
title AI Face Recognition Attendance System - Production Server
color 0b

echo ==============================================================================
echo   AI Face Recognition Attendance System (Enterprise Edition)
echo   Target Stream: http://192.168.18.142/capture (Capture Mode)
echo ==============================================================================
echo.

cd /d "%~dp0"

echo [*] Checking Python environment...
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] Python is not installed or not added to your system PATH!
    echo Please install Python 3.11 from python.org and check "Add to PATH".
    pause
    exit /b 1
)

echo [*] Launching Production Server...
echo [*] Web Dashboard URL: http://127.0.0.1:5000
echo.

start http://127.0.0.1:5000
python app.py

pause
