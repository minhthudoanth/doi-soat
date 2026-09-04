@echo off
title KET NOI WIREGUARD VPN - VNPT-VPN-01
color 0B
cd /d "%~dp0"

net session >nul 2>&1
if %errorLevel% neq 0 (
    echo [*] Dang yeu cau quyen Administrator de bat ket noi VPN...
    powershell -NoProfile -ExecutionPolicy Bypass -Command "Start-Process cmd -ArgumentList '/c \"\"%~dpnx0\"\"' -Verb RunAs"
    exit /b
)

echo ================================================================
echo        DANG KET NOI WIREGUARD VPN (VNPT-VPN-01)
echo        Peer: thu.doanthiminh ^| VPN IP: 10.100.0.50
echo ================================================================
echo.

set WG_EXE=C:\Program Files\WireGuard\wireguard.exe
if not exist "%WG_EXE%" (
    echo [LOI] Khong tim thay WireGuard tai "%WG_EXE%"!
    pause
    exit /b 1
)

echo [*] Dang kich hoat Tunnel Service thu.doanthiminh...
"%WG_EXE%" /installtunnelservice "%~dp0thu.doanthiminh.conf"

timeout /t 2 >nul
echo.
echo [*] Kiem tra trang thai dich vu VPN:
sc query WireGuardTunnel$thu.doanthiminh | findstr /i "STATE"
echo.
echo ================================================================
echo   [OK] DA BAT KET NOI VPN THANH CONG!
echo   Dia chi VPN IP cua ban: 10.100.0.50
echo ================================================================
echo.
pause
