@echo off
title DONG BO CODE LEN GITHUB (minhthudoanth)
color 0B

cd /d "%~dp0"
set "GIT_EXE=git"
if exist "%~dp0..\git\cmd\git.exe" (
    set "GIT_EXE=%~dp0..\git\cmd\git.exe"
    set "PATH=%~dp0..\git\cmd;%~dp0..\git\mingw64\bin;%PATH%"
)

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

:: 1. Gom toan bo thay doi
"%GIT_EXE%" add .

:: 2. Kiem tra co thay doi nao de commit khong
"%GIT_EXE%" diff --cached --quiet
if %ERRORLEVEL% neq 0 (
    if %SILENT_MODE% equ 0 echo [*] Dang tao commit moi...
    "%GIT_EXE%" commit -m "feat: cap nhat ma nguon luc %DATE% %TIME%" >nul 2>&1
)

:: 3. Day code len GitHub (origin main)
if %SILENT_MODE% equ 0 echo [*] Dang day (push) code len GitHub...
"%GIT_EXE%" push -u origin main
if %ERRORLEVEL% neq 0 (
    if %SILENT_MODE% equ 1 (
        "%GIT_EXE%" pull --rebase origin main >nul 2>&1
        "%GIT_EXE%" push -u origin main >nul 2>&1
    ) else (
        echo.
        echo [!] Ket noi GitHub yeu cau xac thuc Token.
        echo     (Ban co the tao Token tai: https://github.com/settings/tokens/new voi quyen 'repo')
        set /p GITHUB_TOKEN="Nhap GitHub Personal Access Token cua ban (hoac an Enter de thu pull/rebase): "
        if defined GITHUB_TOKEN (
            "%GIT_EXE%" remote set-url origin https://!GITHUB_TOKEN!@github.com/minhthudoanth/doi-soat.git
            "%GIT_EXE%" push -u origin main
        ) else (
            echo [*] Dang dong bo conflict va thu lai...
            "%GIT_EXE%" pull --rebase origin main
            "%GIT_EXE%" push -u origin main
        )
    )
)

if %SILENT_MODE% equ 0 (
    echo.
    echo ================================================================
    echo   [OK] DONG BO VA DAY CODE LEN GITHUB THANH CONG!
    echo   Link Repo: https://github.com/minhthudoanth/doi-soat
    echo ================================================================
    echo.
    pause
)

