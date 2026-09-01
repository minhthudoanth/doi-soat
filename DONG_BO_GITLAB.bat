@echo off
title DONG BO CODE LEN GITLAB
color 0A
echo ================================================================
echo        DANG TU DONG DONG BO VA DAY CODE LEN GITLAB...
echo ================================================================
echo.

cd /d "%~dp0"
set GIT_EXE=C:\Users\a1dtm\.gemini\antigravity\scratch\git\cmd\git.exe

echo [*] Kiem tra trang thai thay doi...
"%GIT_EXE%" status --short

echo.
echo [*] Dang gom toan bo thay doi (git add)...
"%GIT_EXE%" add .

for /f "tokens=1-4 delims=/ " %%a in ('date /t') do (set mydate=%%c-%%b-%%a)
for /f "tokens=1-2 delims=: " %%a in ('time /t') do (set mytime=%%a:%%b)

echo [*] Dang tao Commit tu dong...
"%GIT_EXE%" commit -m "auto: cap nhat ma nguon luc %DATE% %TIME%"

echo.
echo [*] Dang day (push) code len GitLab...
"%GIT_EXE%" push origin main

echo.
echo ================================================================
echo   [OK] DONG BO VA DAY CODE LEN GITLAB HOAN TAT THANH CONG!
echo ================================================================
echo.
pause
