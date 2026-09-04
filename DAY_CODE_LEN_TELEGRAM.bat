@echo off
title DAY MA NGUON LEN TELEGRAM SAVED MESSAGES
color 0B

echo ================================================================
echo       DANG DONG GOI VA DAY MA NGUON LEN TELEGRAM SAVED MESSAGES
echo ================================================================
echo.

cd /d "%~dp0"
if exist "..\python\python.exe" (
    "..\python\python.exe" send_to_telegram.py
) else (
    python send_to_telegram.py
)

echo.
echo ================================================================
echo   [OK] HOAN TAT! VUI LONG KIEM TRA MUC SAVED MESSAGES TREN TELEGRAM
echo ================================================================
echo.
pause
