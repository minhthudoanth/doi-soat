@echo off
title KINGFOOD SCM - DOI SOAT KRC
color 0A
echo ================================================================
echo    DANG KHOI DONG HE THONG DOI SOAT SCM KINGFOODMART...
echo ================================================================

cd /d "%~dp0"

set PYTHON_EXE=python
if exist "..\python\python.exe" set PYTHON_EXE=..\python\python.exe

:: Kiem tra neu he thong da dang chay san thi chi can mo Web
powershell -NoProfile -Command "try { $r = Invoke-WebRequest -Uri 'http://127.0.0.1:5000' -UseBasicParsing -TimeoutSec 2; exit 0 } catch { exit 1 }"
if %ERRORLEVEL% equ 0 (
    echo [*] He thong da dang chay san! Dang mo trinh duyet...
    start "" "http://doi-soat.local:5000"
    ping 127.0.0.1 -n 2 >nul
    exit /b
)

:: 1. Khoi dong Telegram Real-time Listener ngam
start /B "" "%PYTHON_EXE%" "telegram_listener.py"

:: 2. Khoi dong Web Server Dashboard
"%PYTHON_EXE%" "app.py"

pause

