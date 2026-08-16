@echo off
cd /d "%~dp0"
title SNRU Scitech Activity System

echo ====================================================================
echo      Starting SNRU Scitech Activity System...
echo ====================================================================
echo.

if exist ".venv\Scripts\python.exe" (
    set "PYTHON_EXE=.venv\Scripts\python.exe"
    echo [1/3] Found Virtual Environment .venv
) else (
    set "PYTHON_EXE=python"
    echo [1/3] Using System Python
)


%PYTHON_EXE% --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] Python not found on this system!
    echo Please install Python 3.10+ and check "Add Python to PATH".
    echo.
    pause
    exit /b
)

%PYTHON_EXE% --version

echo [2/3] Opening http://localhost:5000 in browser...
start http://localhost:5000

echo [3/3] Running Flask Server...
echo --------------------------------------------------------------------
echo  * Web server running at: http://localhost:5000
echo  * Press Ctrl + C in this window to stop server
echo --------------------------------------------------------------------
echo.

%PYTHON_EXE% app.py

if %errorlevel% neq 0 (
    echo.
    echo [ERROR] Server stopped with error.
)

pause


