@echo off
title Cloudflare Public Tunnel
echo ==========================================
echo    ACTIVITY CALENDAR - PUBLIC LINK
echo ==========================================
echo.
echo 1. Make sure your Python Server (app.py) is RUNNING.
echo 2. Waiting for Cloudflare to generate your link...
echo.
cloudflared tunnel --url http://127.0.0.1:5000
echo.
echo If you see an error, please install Cloudflare Tunnel first:
echo https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-windows-amd64.msi
pause
