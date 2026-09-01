@echo off
title Kingfood SCM Web Dashboard
color 0B
echo ================================================================
echo       KINGFOOD SCM - OPERATIONS WEB DASHBOARD
echo ================================================================
echo.
cd /d "%~dp0"
echo Dang khoi dong Web Dashboard tai: http://127.0.0.1:5000 ...
start http://127.0.0.1:5000
if exist "..\python\python.exe" (
    "..\python\python.exe" app.py
) else (
    python app.py
)
pause
