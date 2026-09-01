@echo off
title Cai Dat Tu Dong Chay Khi Bat May - Kingfood SCM
echo ================================================================
echo    CAI DAT KINGFOOD SCM TU DONG CHAY NGAM KHI BAT MAY...
echo ================================================================
echo.
set STARTUP_DIR=%APPDATA%\Microsoft\Windows\Start Menu\Programs\Startup
powershell -Command "$ws = New-Object -ComObject WScript.Shell; $s = $ws.CreateShortcut('%STARTUP_DIR%\Kingfood_SCM_AutoStart.lnk'); $s.TargetPath = 'wscript.exe'; $s.Arguments = '"C:\Users\a1dtm\.gemini\antigravity\scratch\kingfood_scm_bot\KHOI_DONG_NGAM_KHI_BAT_MAY.vbs"'; $s.WorkingDirectory = 'C:\Users\a1dtm\.gemini\antigravity\scratch\kingfood_scm_bot'; $s.Save()"

echo [OK] Da cai dat thanh cong! Tu gio moi khi bat may tinh, he thong se tu dong chay ngam!
echo Ban co the mo trinh duyet bat ky luc nao tai: http://127.0.0.1:5000
echo.
pause
