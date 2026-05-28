@echo off
title Activity Calendar Unified Launcher
color 0b

echo ======================================================================
echo          Unified Launcher: Web Server + Ngrok + LINE Setup
echo ======================================================================
echo.

REM 1. Clean up existing processes to prevent conflicts
echo [*] Checking and cleaning up conflicting processes...
taskkill /f /im ngrok.exe >nul 2>&1
.venv\Scripts\python.exe -c "import os, subprocess; [subprocess.run(f'taskkill /f /pid {line.split()[-1]}', shell=True) for line in subprocess.check_output('netstat -aon', shell=True).decode().splitlines() if ':5000' in line and 'LISTENING' in line]" >nul 2>&1
ping 127.0.0.1 -n 2 >nul
echo [+] Cleanup completed.
echo.

REM 2. Start the Web Server
echo [*] Starting Flask/Waitress Web Server...
start "Activity Calendar Server" .venv\Scripts\python.exe app.py
echo [*] Waiting 3 seconds for server to start...
ping 127.0.0.1 -n 4 >nul
echo [+] Server started on http://127.0.0.1:5000/
echo.

REM 3. Start Ngrok Tunnel
echo [*] Starting Ngrok Tunnel...
start "Ngrok Tunnel" ngrok http --url=synopsis-exponent-peddling.ngrok-free.dev 5000
echo [*] Waiting 3 seconds for Ngrok tunnel to establish...
ping 127.0.0.1 -n 4 >nul
echo [+] Ngrok tunnel established.
echo.

REM 4. Configure LINE Rich Menu and Webhook URL
echo [*] Configuring LINE Rich Menu and Webhook...
.venv\Scripts\python.exe setup_user_rich_menu.py
if %errorlevel% neq 0 (
    color 0c
    echo [x] Warning: Failed to configure LINE settings. Please check your .env variables or internet connection.
) else (
    echo [+] LINE settings configured successfully!
)
echo.

REM 5. Open Webpage
echo [*] Launching your website in browser...
start https://synopsis-exponent-peddling.ngrok-free.dev/
echo.
echo ======================================================================
echo [SUCCESS] Everything is up and running!
echo 
echo - Web Server: http://127.0.0.1:5000
echo - Public URL: https://synopsis-exponent-peddling.ngrok-free.dev
echo.
echo Please DO NOT close the "Activity Calendar Server" or "Ngrok Tunnel" windows.
echo ======================================================================
pause
