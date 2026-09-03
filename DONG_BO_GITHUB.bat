@echo off
title DONG BO CODE LEN GITHUB (minhthudoanth)
color 0B
echo ================================================================
echo       DANG TU DONG DONG BO VA DAY CODE LEN GITHUB...
echo       Account: https://github.com/minhthudoanth
echo ================================================================
echo.

cd /d "%~dp0"
set GIT_EXE=git
if exist "..\git\cmd\git.exe" set GIT_EXE=..\git\cmd\git.exe

:: Kiem tra remote github da co chua
"%GIT_EXE%" remote get-url github >nul 2>&1
if %ERRORLEVEL% neq 0 (
    echo [*] Dang tao remote github: https://github.com/minhthudoanth/doi-soat.git
    "%GIT_EXE%" remote add github https://github.com/minhthudoanth/doi-soat.git
)

echo [*] Kiem tra trang thai thay doi...
"%GIT_EXE%" status --short

echo.
echo [*] Dang gom toan bo thay doi (git add .)...
"%GIT_EXE%" add .

for /f "tokens=1-4 delims=/ " %%a in ('date /t') do (set mydate=%%c-%%b-%%a)
for /f "tokens=1-2 delims=: " %%a in ('time /t') do (set mytime=%%a:%%b)

echo [*] Dang tao Commit tu dong...
"%GIT_EXE%" commit -m "auto: cap nhat ma nguon luc %DATE% %TIME%"

echo.
echo [*] Dang day (push) code len GitHub: https://github.com/minhthudoanth/doi-soat ...
"%GIT_EXE%" push -u origin main

if %ERRORLEVEL% equ 0 (
    echo.
    echo ================================================================
    echo   [OK] DONG BO VA DAY CODE LEN GITHUB THANH CONG!
    echo   Link Repo: https://github.com/minhthudoanth/doi-soat
    echo ================================================================
) else (
    echo.
    echo ================================================================
    echo   [!] Dang thu dong bo lai voi GitHub...
    "%GIT_EXE%" pull --rebase origin main
    "%GIT_EXE%" push -u origin main
    echo ================================================================
)

echo.
pause
