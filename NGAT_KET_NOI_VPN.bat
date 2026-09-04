@echo off
title NGAT KET NOI WIREGUARD VPN - VNPT-VPN-01
color 0C
cd /d "%~dp0"

net session >nul 2>&1
if %errorLevel% neq 0 (
    echo [*] Dang yeu cau quyen Administrator de ngat ket noi VPN...
    powershell -NoProfile -ExecutionPolicy Bypass -Command "Start-Process cmd -ArgumentList '/c \"\"%~dpnx0\"\"' -Verb RunAs"
    exit /b
)

echo ================================================================
echo        DANG NGAT KET NOI WIREGUARD VPN (thu.doanthiminh)
echo ================================================================
echo.

set WG_EXE=C:\Program Files\WireGuard\wireguard.exe
if not exist "%WG_EXE%" (
    echo [LOI] Khong tim thay WireGuard tai "%WG_EXE%"!
    pause
    exit /b 1
)

echo [*] Dang go bo Tunnel Service thu.doanthiminh...
"%WG_EXE%" /uninstalltunnelservice thu.doanthiminh

timeout /t 2 >nul
echo.
echo ================================================================
echo   [OK] DA NGAT KET NOI VPN THANH CONG!
echo ================================================================
echo.
pause
