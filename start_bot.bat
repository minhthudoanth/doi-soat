@echo off
title Kingfood SCM Auto-Check Bot (Passive Monitor)
color 0A
echo ================================================================
echo       KINGFOOD SCM - TELEGRAM AUTO-CHECK USERBOT (24/7)
echo ================================================================
echo.
cd /d "%~dp0"
if exist "..\python\python.exe" (
    "..\python\python.exe" telegram_listener.py
) else (
    python telegram_listener.py
)
pause
