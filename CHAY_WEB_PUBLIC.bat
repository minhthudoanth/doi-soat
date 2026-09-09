@echo off
chcp 65001 >nul
title KINGFOOD SCM - PUBLIC DASHBOARD (CLOUDFLARE TUNNEL)
echo ====================================================================
echo    KHOI DONG DASHBOARD PUBLIC RA INTERNET QUA CLOUDFLARE TUNNEL
echo ====================================================================
echo.

cd /d "%~dp0"

:: 1. Xac dinh duong dan Python chuan
set "PYTHON_EXE=python"
if exist "%~dp0..\python\python.exe" set "PYTHON_EXE=%~dp0..\python\python.exe"
if exist "%~dp0python\python.exe" set "PYTHON_EXE=%~dp0python\python.exe"

:: 2. Xac dinh duong dan cloudflared.exe
set "CF_EXE=cloudflared.exe"
if exist "%~dp0cloudflared.exe" (
    set "CF_EXE=%~dp0cloudflared.exe"
) else if exist "C:\Program Files (x86)\cloudflared\cloudflared.exe" (
    set "CF_EXE=C:\Program Files (x86)\cloudflared\cloudflared.exe"
)

echo [*] Dang kiem tra Web Server noi bo (http://localhost:5000)...
netstat -ano | findstr ":5000" >nul
if %errorlevel% neq 0 (
    echo [*] Server chua chay, dang tu dong khoi dong app.py...
    start "" /b "%PYTHON_EXE%" app.py
    timeout /t 4 >nul
)

echo.
echo ====================================================================
echo  Dang ket noi Cloudflare Tunnel de tao link HTTPS cong khai...
echo  Sau vai giay, ban se thay dong chu link dang:
echo  https://...trycloudflare.com
echo.
echo  Bat ky may tinh, dien thoai nao cung co the truy cap link nay!
echo  (Vui long khong tat cua so nay khi dang su dung tu may khac)
echo ====================================================================
echo.

"%CF_EXE%" tunnel --url http://127.0.0.1:5000
pause
