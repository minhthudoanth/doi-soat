@echo off
title DONG BO DU LIEU SCM LEN STARROCKS (kfm_scm)
color 0B
echo ================================================================
echo         KINGFOOD SCM - DONG BO DU LIEU LEN STARROCKS
echo              Host: 103.147.122.103:9030 (VPN)
echo ================================================================
echo.
cd /d "%~dp0"

if exist "..\python\python.exe" (
    "..\python\python.exe" sync_starrocks.py
) else (
    python sync_starrocks.py
)

echo.
pause
