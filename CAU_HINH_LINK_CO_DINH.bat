@echo off
title CAU HINH LINK CO DINH CHO WEB SCM (doi-soat.local)
color 0A

:: Kiem tra quyen Administrator va tu dong xin quyen
net session >nul 2>&1
if %errorlevel% neq 0 (
    echo [*] Dang yeu cau quyen Administrator de them ten mien vao file hosts...
    powershell -Command "Start-Process cmd -ArgumentList '/c \"\"%~f0\"\"' -Verb RunAs"
    exit /b
)

set HOSTS_FILE=%windir%\system32\drivers\etc\hosts

findstr /i "doi-soat.local" "%HOSTS_FILE%" >nul 2>&1
if %errorlevel% neq 0 (
    echo. >> "%HOSTS_FILE%"
    echo # Ten mien rieng cho Web Doi Soat Kingfood SCM >> "%HOSTS_FILE%"
    echo 127.0.0.1  doi-soat.local doisoat-krc.local doisoat.kingfood >> "%HOSTS_FILE%"
    echo [OK] Da them thanh cong ten mien 'doi-soat.local' vao he thong!
) else (
    echo [OK] Ten mien 'doi-soat.local' da duoc cau hinh tu truoc!
)

ipconfig /flushdns >nul 2>&1
echo [OK] Da lam moi bo nho dem DNS.
echo.
echo ================================================================
echo   BAN CO THE TRUY CAP WEB BANG CAC DUONG LINK CO DINH SAU:
echo   - http://doi-soat.local:5000
echo   - http://doisoat-krc.local:5000
echo   - http://doisoat.kingfood:5000
echo   - http://localhost:5000
echo ================================================================
timeout /t 3 >nul
