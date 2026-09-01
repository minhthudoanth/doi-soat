import os
import sys

# Đảm bảo UTF-8 cho Windows console
if sys.platform == 'win32':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
        sys.stderr.reconfigure(encoding='utf-8')
    except Exception:
        pass

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)


import asyncio
from datetime import datetime, timezone, timedelta
from telethon import TelegramClient
from telethon.tl.types import Channel, Chat
from config import API_ID, API_HASH, SESSION_NAME, DB_PATH
from classifier import classify_message
from database import init_db
import sqlite3

VN_TZ = timezone(timedelta(hours=7))

async def sync_today_messages():
    init_db()
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    print("================================================================")
    print(" >>> DANG KET NOI VA DONG BO TIN NHAN NGAY 21/08 TU TELEGRAM...")
    print("================================================================")

    client = TelegramClient(SESSION_NAME, API_ID, API_HASH)
    await client.start()

    me = await client.get_me()
    print(f"[*] Dang nhap: {me.first_name} (@{me.username or 'Khong co'})")

    # Mốc thời gian bắt đầu ngày hôm nay 21/08 (00:00:00)
    now_vn = datetime.now(VN_TZ)
    start_of_today = datetime(now_vn.year, now_vn.month, now_vn.day, 0, 0, 0, tzinfo=VN_TZ)

    dialogs = await client.get_dialogs()
    print(f"[*] Tim thay {len(dialogs)} hoi thoai/group tren tai khoan.")

    total_scanned = 0
    total_saved = 0
    p1_count = 0
    p2_count = 0
    krc_audit_count = 0

    for dialog in dialogs:
        # Chỉ quét Group, Supergroup và Channel
        if not (dialog.is_group or dialog.is_channel):
            continue

        chat_title = dialog.title or "Group"
        chat_id = dialog.id
        
        try:
            async for msg in client.iter_messages(dialog.entity, limit=200):
                if not msg.text:
                    continue

                msg_date = msg.date.astimezone(VN_TZ)
                
                # Nếu tin nhắn trước ngày hôm nay, bỏ qua
                if msg_date < start_of_today:
                    break

                total_scanned += 1

                # Kiểm tra trùng lặp
                cursor.execute("SELECT id FROM raw_messages WHERE msg_id = ? AND chat_id = ?", (msg.id, chat_id))
                if cursor.fetchone():
                    continue

                text = msg.text.strip()
                sender = await msg.get_sender()
                sender_name = "Ẩn danh"
                username = "Không có"
                sender_id = msg.sender_id or 0

                if sender:
                    fn = getattr(sender, 'first_name', '') or ''
                    ln = getattr(sender, 'last_name', '') or ''
                    sender_name = f"{fn} {ln}".strip() or "Ẩn danh"
                    if getattr(sender, 'username', None):
                        username = f"@{sender.username}"

                category, priority = classify_message(text, chat_title)

                date_str = msg_date.strftime("%Y-%m-%d %H:%M:%S")

                cursor.execute("""
                    INSERT INTO raw_messages (msg_id, chat_id, chat_title, sender_id, sender_name, username, message_text, category, priority, created_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (msg.id, chat_id, chat_title, sender_id, sender_name, username, text, category, priority, date_str))

                if "P1" in priority or "P2" in priority or category == "KRC - Đối soát":
                    cursor.execute("""
                        INSERT INTO priority_cases (msg_id, chat_title, sender_name, category, priority, content, status, created_at)
                        VALUES (?, ?, ?, ?, ?, ?, 'Chờ xử lý', ?)
                    """, (msg.id, chat_title, sender_name, category, priority, text, date_str))

                total_saved += 1
                if "P1" in priority:
                    p1_count += 1
                if "P2" in priority:
                    p2_count += 1
                if category == "KRC - Đối soát":
                    krc_audit_count += 1

        except Exception as e:
            # Bỏ qua nếu không có quyền đọc lịch sử
            continue

    conn.commit()
    conn.close()
    await client.disconnect()

    print("\n================================================================")
    print(" >>> KET QUA DONG BO DU LIEU NGAY 21/08:")
    print(f" [+] Tong tin nhan quet duoc: {total_scanned}")
    print(f" [+] Tin nhan moi luu vao CSDL: {total_saved}")
    print(f" [+] Case Khan cap (P1): {p1_count}")
    print(f" [+] Case Can xu ly (P2): {p2_count}")
    print(f" [+] Case KRC - Doi soat: {krc_audit_count}")
    print("================================================================")
    print(" >>> Da cap nhat toan bo len Web Dashboard tai http://127.0.0.1:5000!")

if __name__ == "__main__":
    asyncio.run(sync_today_messages())
