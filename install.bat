@echo off
title AI Face Recognition Attendance System - Environment Setup
color 0e

echo ==============================================================================
echo   AI Face Recognition Attendance System - Automated Environment Setup
echo ==============================================================================
echo.

cd /d "%~dp0"

echo [*] Upgrading pip...
python -m pip install --upgrade pip

echo [*] Installing pre-built dlib wheel for Python 3.11 x64...
python -m pip install https://github.com/z-mahmud22/Dlib_Windows_Python3.x/raw/main/dlib-19.24.1-cp311-cp311-win_amd64.whl

echo [*] Installing production requirements...
python -m pip install -r requirements.txt

echo.
echo [*] Running system pre-flight verification...
python diagnostics.py

echo.
echo ==============================================================================
echo   Installation and Verification Complete!
echo   Double click "start.bat" to run the system.
echo ==============================================================================
echo.
pause
