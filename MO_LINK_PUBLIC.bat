@echo off
title KINGFOOD SCM - MO LINK PUBLIC INTERNET (CLOUDFLARE TUNNEL)
color 0B
cd /d "%~dp0"

echo ================================================================
echo       KINGFOOD SCM - MO LINK PUBLIC RA INTERNET
echo ================================================================
echo.

:: 1. Kiem tra xem Web Dashboard da chay chua
powershell -NoProfile -Command "try { $r = Invoke-WebRequest -Uri 'http://127.0.0.1:5000' -UseBasicParsing -TimeoutSec 2; exit 0 } catch { exit 1 }"
if %ERRORLEVEL% neq 0 (
    echo [!] Web Dashboard chua bat! Dang tu dong khoi dong Dashboard truoc...
    if exist "..\python\python.exe" (
        start /B "" "..\python\python.exe" "app.py"
    ) else (
        start /B "" python "app.py"
    )
    echo [*] Cho 4 giay de Web Server khoi dong...
    timeout /t 4 >nul
)

:: 2. Kiem tra cloudflared.exe
if not exist "cloudflared.exe" (
    if exist "C:\Program Files (x86)\cloudflared\cloudflared.exe" (
        copy /y "C:\Program Files (x86)\cloudflared\cloudflared.exe" "cloudflared.exe" >nul
    ) else (
        echo [!] Khong tim thay cloudflared.exe, dang tu dong tai ve...
        powershell -NoProfile -Command "[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12; (New-Object System.Net.WebClient).DownloadFile('https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-windows-amd64.exe', 'cloudflared.exe')"
    )
)

echo [*] Dang tao duong link Public HTTPS bao mat qua Cloudflare...
echo [*] Vui long nhin duong link dang https://xxx.trycloudflare.com ben duoi de chia se!
echo.
echo ================================================================
cloudflared.exe tunnel --url http://127.0.0.1:5000
pause
