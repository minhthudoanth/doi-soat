@echo off
title KINGFOOD SCM - DOI SOAT KRC
color 0A
echo ================================================================
echo    DANG KHOI DONG HE THONG DOI SOAT SCM KINGFOODMART...
echo ================================================================

cd /d "%~dp0"

:: 1. Khoi dong Telegram Real-time Listener ngam
start /B "" "C:\Users\a1dtm\.gemini\antigravity\scratch\python\python.exe" "telegram_listener.py"

:: 2. Khoi dong Web Server Dashboard
start "" "http://127.0.0.1:5000"
"C:\Users\a1dtm\.gemini\antigravity\scratch\python\python.exe" "app.py"

pause
