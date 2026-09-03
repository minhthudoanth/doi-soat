@echo off
title DONG BO CODE LEN GITHUB (minhthudoanth)
color 0B

cd /d "%~dp0"
set GIT_EXE=git
if exist "..\git\cmd\git.exe" set GIT_EXE=..\git\cmd\git.exe

:: Kiem tra neu chay o che do im lang (silent)
set SILENT_MODE=0
if "%1"=="/silent" set SILENT_MODE=1
if "%1"=="--silent" set SILENT_MODE=1

if %SILENT_MODE% equ 0 (
    echo ================================================================
    echo       DANG TU DONG DONG BO VA DAY CODE LEN GITHUB...
    echo       Account: https://github.com/minhthudoanth/doi-soat
    echo ================================================================
    echo.
)

:: Dam bao remote origin tro ve GitHub
"%GIT_EXE%" remote set-url origin https://github.com/minhthudoanth/doi-soat.git >nul 2>&1

:: 1. Gom toan bo thay doi
"%GIT_EXE%" add .

:: 2. Kiem tra co thay doi nao de commit khong
"%GIT_EXE%" diff --cached --quiet
if %ERRORLEVEL% neq 0 (
    for /f "tokens=1-4 delims=/ " %%a in ('date /t') do (set mydate=%%c-%%b-%%a)
    for /f "tokens=1-2 delims=: " %%a in ('time /t') do (set mytime=%%a:%%b)
    if %SILENT_MODE% equ 0 echo [*] Dang tao commit moi...
    "%GIT_EXE%" commit -m "auto: cap nhat ma nguon luc %DATE% %TIME%" >nul 2>&1
)

:: 3. Day code len GitHub (origin main)
if %SILENT_MODE% equ 0 echo [*] Dang day (push) code len GitHub...
"%GIT_EXE%" push -u origin main >nul 2>&1
if %ERRORLEVEL% neq 0 (
    if %SILENT_MODE% equ 0 echo [*] Dang dong bo conflict va thu lai...
    "%GIT_EXE%" pull --rebase origin main >nul 2>&1
    "%GIT_EXE%" push -u origin main
)

:: 4. Day du phong len GitLab (backup)
"%GIT_EXE%" push gitlab main >nul 2>&1

if %SILENT_MODE% equ 0 (
    echo.
    echo ================================================================
    echo   [OK] DONG BO VA DAY CODE LEN GITHUB THANH CONG!
    echo   Link Repo: https://github.com/minhthudoanth/doi-soat
    echo ================================================================
    echo.
    pause
)
