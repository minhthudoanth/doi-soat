import os
import sys

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
from config import API_ID, API_HASH, SESSION_NAME, DB_PATH
from classifier import classify_message
from database import init_db
import sqlite3

VN_TZ = timezone(timedelta(hours=7))

async def sync():
    init_db()
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    print("================================================================", flush=True)
    print(" >>> DANG QUET TOAN BO TIN NHAN HOM NAY (21/08)...", flush=True)
    print("================================================================", flush=True)

    client = TelegramClient(SESSION_NAME, API_ID, API_HASH)
    await client.connect()
    
    if not await client.is_user_authorized():
        print("[!] Chua dang nhap!", flush=True)
        return

    me = await client.get_me()
    print(f"[*] Dang nhap: {me.first_name} (ID: {me.id})", flush=True)

    now_vn = datetime.now(VN_TZ)
    # Lấy tin nhắn từ 00:00:00 ngày 21/08
    cutoff_time = datetime(now_vn.year, now_vn.month, now_vn.day, 0, 0, 0, tzinfo=VN_TZ)

    dialogs = await client.get_dialogs()
    print(f"[*] Tong so hoi thoai/nhom: {len(dialogs)}", flush=True)

    active_dialogs = []
    for d in dialogs:
        if (d.is_group or d.is_channel) and d.date:
            d_date = d.date.astimezone(VN_TZ)
            if d_date >= cutoff_time:
                active_dialogs.append(d)

    print(f"[*] So nhom co tin nhan hoat dong trong ngay 21/08: {len(active_dialogs)} nhom", flush=True)

    total_scanned = 0
    total_saved = 0
    p1_count = 0
    p2_count = 0
    krc_count = 0
    meat_count = 0
    dc_count = 0
    audit_count = 0

    for idx, dialog in enumerate(active_dialogs, 1):
        chat_title = dialog.title or "Group"
        chat_id = dialog.id

        print(f" -> [{idx}/{len(active_dialogs)}] Dang doc: {chat_title}...", flush=True)

        try:
            async for msg in client.iter_messages(dialog.entity, limit=100):
                if not msg.text:
                    continue

                msg_date = msg.date.astimezone(VN_TZ)
                if msg_date < cutoff_time:
                    break

                total_scanned += 1

                # Kiem tra trung lap
                cursor.execute("SELECT id FROM raw_messages WHERE msg_id = ? AND chat_id = ?", (msg.id, chat_id))
                if cursor.fetchone():
                    continue

                text = msg.text.strip()
                sender = await msg.get_sender()
                sender_name = "An danh"
                username = "Khong co"
                sender_id = msg.sender_id or 0

                if sender:
                    fn = getattr(sender, 'first_name', '') or ''
                    ln = getattr(sender, 'last_name', '') or ''
                    sender_name = f"{fn} {ln}".strip() or "An danh"
                    if getattr(sender, 'username', None):
                        username = f"@{sender.username}"

                res = classify_message(text, sender_name, chat_title)
                if res:
                    category = res.get("category", "Khác")
                    priority = res.get("priority", "P3")
                    issue_type = res.get("issue_type", "Khác")
                else:
                    category, priority, issue_type = "Khác", "P3", "Khác"

                date_str = msg_date.strftime("%Y-%m-%d %H:%M:%S")

                cursor.execute("""
                    INSERT INTO raw_messages (msg_id, chat_id, chat_title, sender_id, sender_name, username, message_text, category, priority, issue_type, created_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (msg.id, chat_id, chat_title, sender_id, sender_name, username, text, category, priority, issue_type, date_str))

                if issue_type in ["Thiếu", "Thừa", "XCL", "Sự cố Tài xế"]:
                    cursor.execute("""
                        INSERT INTO priority_cases (msg_id, chat_title, sender_name, category, priority, content, status, issue_type, created_at)
                        VALUES (?, ?, ?, ?, ?, ?, 'Chờ xử lý', ?, ?)
                    """, (msg.id, chat_title, sender_name, category, priority, text, issue_type, date_str))

                total_saved += 1
                if "P1" in priority: p1_count += 1
                if "P2" in priority: p2_count += 1
                if "KRC" in category: krc_count += 1
                if "thịt cá" in category.lower() or "đông mát" in category.lower(): meat_count += 1
                if "DC" in category: dc_count += 1
                if "Đối soát" in category: audit_count += 1


            conn.commit()
        except Exception as e:
            continue

    conn.commit()
    conn.close()
    await client.disconnect()

    print("\n================================================================", flush=True)
    print(f" [+] Tong tin nhan quet duoc trong ngay: {total_scanned}", flush=True)
    print(f" [+] Tin nhan da luu vao Dashboard: {total_saved}", flush=True)
    print(f" [+] Case Khan cap (P1): {p1_count}", flush=True)
    print(f" [+] Case Can xu ly (P2): {p2_count}", flush=True)
    print(f" [+] Tin nhan KRC (Kho Rau Cu): {krc_count}", flush=True)
    print(f" [+] Tin nhan Dong Mat Thit Ca: {meat_count}", flush=True)
    print(f" [+] Tin nhan DC (Kho Tong): {dc_count}", flush=True)
    print(f" [+] Case KRC - Doi soat: {audit_count}", flush=True)
    print("================================================================", flush=True)

if __name__ == "__main__":
    asyncio.run(sync())
