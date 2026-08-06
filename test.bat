@echo off
title AI Face Recognition Attendance System - 10-Point Diagnostics
color 0a

echo ==============================================================================
echo   AI Face Recognition Attendance System - Diagnostics & Health Suite
echo ==============================================================================
echo.

cd /d "%~dp0"
python diagnostics.py

echo.
echo Press any key to exit...
pause >nul
