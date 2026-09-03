@echo off
title Kingfood SCM Web Dashboard
color 0B
echo ================================================================
echo       KINGFOOD SCM - OPERATIONS WEB DASHBOARD
echo ================================================================
echo.
cd /d "%~dp0"
echo Dang khoi dong Web Dashboard...
if exist "..\python\python.exe" (
    "..\python\python.exe" app.py
) else (
    python app.py
)
pause
