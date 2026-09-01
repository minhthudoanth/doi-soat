@echo off
title Khoi Dong Kingfood SCM System
color 0E
echo ================================================================
echo       DANG KHOI DONG HE THONG KINGFOOD SCM BOT + WEB
echo ================================================================
echo.
cd /d "%~dp0"
start "Kingfood SCM Userbot" cmd /c "start_bot.bat"
timeout /t 2 >nul
start "Kingfood SCM Web Dashboard" cmd /c "start_web.bat"
echo.
echo Da khoi dong thanh cong ca Bot va Web Dashboard!
