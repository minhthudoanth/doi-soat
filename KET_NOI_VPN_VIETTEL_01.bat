@echo off
title KET NOI WIREGUARD VPN - VIETTEL-VPN-01
color 0B
cd /d "%~dp0"

net session >nul 2>&1
if %errorLevel% neq 0 (
    echo [*] Dang yeu cau quyen Administrator de bat ket noi VPN Viettel 01...
    powershell -NoProfile -ExecutionPolicy Bypass -Command "Start-Process cmd -ArgumentList '/c \"\"%~dpnx0\"\"' -Verb RunAs"
    exit /b
)

echo ================================================================
echo        DANG KET NOI WIREGUARD VPN (VIETTEL-VPN-01)
echo        Peer: thu.doanthiminh ^| VPN IP: 10.99.0.45
echo ================================================================
echo.

set WG_EXE=C:\Program Files\WireGuard\wireguard.exe
if not exist "%WG_EXE%" (
    echo [LOI] Khong tim thay WireGuard tai "%WG_EXE%"!
    pause
    exit /b 1
)

echo [*] Dang ngat ket noi cac tunnel cu neu co...
"%WG_EXE%" /uninstalltunnelservice thu.doanthiminh >nul 2>&1
"%WG_EXE%" /uninstalltunnelservice thu.doanthiminh.viettel01 >nul 2>&1
"%WG_EXE%" /uninstalltunnelservice thu.doanthiminh.viettel02 >nul 2>&1

echo [*] Dang kich hoat Tunnel Service VIETTEL-VPN-01...
"%WG_EXE%" /installtunnelservice "%~dp0thu.doanthiminh.viettel01.conf"

timeout /t 2 >nul
echo.
echo [*] Kiem tra trang thai dich vu VPN:
sc query WireGuardTunnel$thu.doanthiminh.viettel01 | findstr /i "STATE"
echo.
echo ================================================================
echo   [OK] DA BAT KET NOI VIETTEL-VPN-01 THANH CONG!
echo   Dia chi VPN IP cua ban: 10.99.0.45
echo ================================================================
echo.
pause
