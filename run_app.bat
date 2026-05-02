@echo off
echo Starting Activity Calendar Server...
echo Please wait 2 seconds...

start "Server" python app.py

timeout /t 2 /nobreak >nul

start http://127.0.0.1:5000/

echo Server is running!
echo Please DO NOT close the other black window (Server).
pause
