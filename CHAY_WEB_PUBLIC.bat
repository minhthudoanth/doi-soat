@echo off
chcp 65001 >nul
title KINGFOOD SCM - PUBLIC DASHBOARD (CLOUDFLARE TUNNEL)
echo ====================================================================
echo    KHỞI ĐỘNG DASHBOARD PUBLIC RA INTERNET QUA CLOUDFLARE TUNNEL
echo ====================================================================
echo.
echo [*] Đang kiểm tra Web Server nội bộ (http://localhost:5000)...
netstat -ano | findstr ":5000" >nul
if %errorlevel% neq 0 (
    echo [*] Server chưa chạy, đang tự động khởi động app.py...
    start /b python app.py
    timeout /t 3 >nul
)

echo.
echo ====================================================================
echo  Đang kết nối Cloudflare Tunnel để tạo link HTTPS công khai...
echo  Sau vài giây, bạn sẽ thấy dòng chữ:
echo  https://...trycloudflare.com
echo.
echo  Bất kỳ máy tính, điện thoại nào cũng có thể truy cập link này!
echo  (Vui lòng không tắt cửa sổ này khi đang sử dụng từ máy khác)
echo ====================================================================
echo.

"C:\Program Files (x86)\cloudflared\cloudflared.exe" tunnel --url http://127.0.0.1:5000
pause
