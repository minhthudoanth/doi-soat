import os
import sys
import asyncio
import zipfile
import shutil
import tempfile
from datetime import datetime
from telethon import TelegramClient

if sys.platform == 'win32':
    try:
        if sys.stdout and hasattr(sys.stdout, 'reconfigure'):
            sys.stdout.reconfigure(encoding='utf-8')
        if sys.stderr and hasattr(sys.stderr, 'reconfigure'):
            sys.stderr.reconfigure(encoding='utf-8')
    except Exception:
        pass

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from config import API_ID, API_HASH, SESSION_NAME

async def main():
    now_str = datetime.now().strftime("%Y%m%d_%H%M%S")
    display_time = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
    
    zip_filename = f"Kingfood_SCM_Bot_Full_{now_str}.zip"
    temp_dir = tempfile.gettempdir()
    zip_path = os.path.join(temp_dir, zip_filename)
    
    print(f"[*] Đang đóng gói file zip: {zip_filename}...", flush=True)
    
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
        for root, dirs, files in os.walk(BASE_DIR):
            if ".git" in root or "__pycache__" in root:
                continue
            for f in files:
                if f.endswith(".log") or f.endswith(".pyc") or f.endswith(".session") or f.endswith(".session-journal") or f.endswith(".db-shm") or f.endswith(".db-wal"):
                    continue
                file_path = os.path.join(root, f)
                rel_path = os.path.relpath(file_path, BASE_DIR)
                zf.write(file_path, rel_path)
                
    zip_size_mb = os.path.getsize(zip_path) / (1024 * 1024)
    print(f"[OK] Đã đóng gói xong: {zip_size_mb:.2f} MB", flush=True)
    
    # Tạo session tạm để tránh xung đột SQLite database lock
    temp_session_name = os.path.join(temp_dir, f"temp_send_session_{now_str}")
    orig_session = os.path.join(BASE_DIR, f"{SESSION_NAME}.session")
    shutil.copy2(orig_session, temp_session_name + ".session")
    
    client = TelegramClient(temp_session_name, API_ID, API_HASH)
    await client.connect()
    
    if not await client.is_user_authorized():
        print("[!] Session chưa đăng nhập!", flush=True)
        return
        
    me = await client.get_me()
    name = f"{getattr(me, 'first_name', '')} {getattr(me, 'last_name', '')}".strip()
    print(f"[*] Đã kết nối với Telegram: {name} (ID: {me.id})", flush=True)
    
    # 1. Gửi tin nhắn mở đầu
    intro_text = (
        f"🚀 **[SAO LƯU MÃ NGUỒN KINGFOOD SCM BOT]**\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"⏰ **Thời gian:** {display_time}\n"
        f"👤 **Tài khoản:** {name} (`{me.id}`)\n"
        f"🌐 **GitHub:** `https://github.com/minhthudoanth/doi-soat`\n"
        f"🌐 **GitLab:** `https://gitlab.com/scm5795236/d-i-soat-krc`\n"
        f"🖥 **Dashboard Local:** `http://doi-soat.local:5000`\n"
        f"☁️ **Cloud Web:** `https://mae-bot.onrender.com`\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"📦 **Gói sao lưu:** `{zip_filename}` ({zip_size_mb:.2f} MB)\n"
        f"Bao gồm file nén Full dự án và các tệp mã nguồn cốt lõi đính kèm bên dưới 👇"
    )
    await client.send_message("me", intro_text)
    print("[OK] Đã gửi thông báo mở đầu.", flush=True)
    await asyncio.sleep(1)
    
    # 2. Gửi file zip
    print(f"[*] Đang gửi file nén {zip_filename}...", flush=True)
    await client.send_file(
        "me",
        zip_path,
        caption=f"📦 **{zip_filename}**\nBản nén Full toàn bộ mã nguồn, cấu hình, giao diện & database ({zip_size_mb:.2f} MB) lúc {display_time}."
    )
    print("[OK] Đã gửi xong file zip.", flush=True)
    await asyncio.sleep(1.5)
    
    # 3. Gửi các file cốt lõi
    core_files = [
        (os.path.join(BASE_DIR, "app.py"), "Mã nguồn chính Flask Dashboard & Realtime API backend"),
        (os.path.join(BASE_DIR, "templates", "dashboard.html"), "Giao diện Dashboard HTML/CSS/JS (Realtime UI)"),
        (os.path.join(BASE_DIR, "database.py"), "Quản lý cơ sở dữ liệu SQLite & tối ưu WAL"),
        (os.path.join(BASE_DIR, "config.py"), "File cấu hình Telegram API & quy tắc phân loại SCM"),
        (os.path.join(BASE_DIR, "classifier.py"), "Bộ phân loại sự cố thông minh & tag Thư Đoàn"),
        (os.path.join(BASE_DIR, "sheet_sync.py"), "Đồng bộ dữ liệu Realtime Google Sheet"),
        (os.path.join(BASE_DIR, "kingfood_api.py"), "Client kết nối API kiểm kê & tồn kho Kingfood (KDB)"),
        (os.path.join(BASE_DIR, "telegram_listener.py"), "Bot lắng nghe thụ động Telegram tin nhắn 24/7"),
        (os.path.join(BASE_DIR, "telegram_sender.py"), "Công cụ phát thông báo hàng loạt và thu hồi tin nhắn Telegram"),
        (os.path.join(BASE_DIR, "doc_generator.py"), "Bộ xuất báo cáo biên bản Word / PDF"),
        (os.path.join(BASE_DIR, "requirements.txt"), "Danh sách thư viện phụ thuộc Python"),
        (os.path.join(BASE_DIR, "Dockerfile"), "File cấu hình Docker container"),
        (os.path.join(BASE_DIR, "Procfile"), "File cấu hình tiến trình Cloud Render"),
        (os.path.join(BASE_DIR, "DONG_BO_GITHUB.bat"), "Script tự động commit & đồng bộ mã nguồn lên GitHub / GitLab"),
        (os.path.join(BASE_DIR, "start_all.bat"), "Script khởi động toàn bộ hệ thống bot & web"),
        (os.path.join(BASE_DIR, "DAY_CODE_LEN_TELEGRAM.bat"), "Script 1-click đẩy mã nguồn lên Telegram Saved Messages"),
        (os.path.join(BASE_DIR, "send_to_telegram.py"), "Mã nguồn Python tự động đóng gói & gửi file lên Telegram"),
        (os.path.join(BASE_DIR, "README.md"), "Tài liệu hướng dẫn sử dụng và vận hành hệ thống"),
        (os.path.join(BASE_DIR, "TONG_KET_PHIEN_LAM_VIEC_SCM.md"), "Biên bản tổng kết phiên làm việc & bàn giao hệ thống")
    ]
    
    print(f"[*] Đang gửi {len(core_files)} file mã nguồn cốt lõi...", flush=True)
    for file_path, desc in core_files:
        if os.path.exists(file_path):
            file_name = os.path.basename(file_path)
            caption = f"📄 **{file_name}**\n{desc}"
            try:
                await client.send_file("me", file_path, caption=caption)
                print(f"  [+] Đã gửi: {file_name}", flush=True)
                await asyncio.sleep(1.2)
            except Exception as ex:
                print(f"  [-] Lỗi gửi {file_name}: {ex}", flush=True)
                
    finish_text = (
        f"✅ **[HOÀN TẤT SAO LƯU MÃ NGUỒN]**\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"Toàn bộ mã nguồn đã được cập nhật lên Telegram Saved Messages lúc {display_time}."
    )
    await client.send_message("me", finish_text)
    print("[OK] Đã hoàn tất và gửi thông báo xong.", flush=True)
    
    await client.disconnect()
    
    # Dọn dẹp file tạm
    for p in [zip_path, temp_session_name + ".session"]:
        try:
            if os.path.exists(p):
                os.remove(p)
        except Exception:
            pass

if __name__ == "__main__":
    asyncio.run(main())
