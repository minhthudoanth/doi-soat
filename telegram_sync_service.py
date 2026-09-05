import os
import sys
import asyncio
from datetime import datetime, timezone, timedelta
from telethon import TelegramClient
import sqlite3

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from config import API_ID, API_HASH, SESSION_NAME, DB_PATH
from classifier import classify_message, is_group_excluded

VN_TZ = timezone(timedelta(hours=7))

async def _do_sync_telegram():
    import tempfile, shutil
    temp_dir = tempfile.gettempdir()
    ts_name = os.path.join(temp_dir, f"temp_sync_{int(datetime.now().timestamp()*1000)}")
    orig_s = os.path.join(BASE_DIR, f"{SESSION_NAME}.session")
    if os.path.exists(orig_s):
        shutil.copy2(orig_s, ts_name + ".session")
        client = TelegramClient(ts_name, API_ID, API_HASH)
    else:
        client = TelegramClient(SESSION_NAME, API_ID, API_HASH)

    await client.connect()
    if not await client.is_user_authorized():
        await client.disconnect()
        return {"success": False, "error": "Telegram client not authorized"}

    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    dialogs = await client.get_dialogs(limit=150)
    audit_dialog = None
    for d in dialogs:
        if d.title and 'SCM - KRC (Đối soát)' in d.title:
            audit_dialog = d
            break

    saved_cnt = 0
    if audit_dialog:
        # Lấy 100 tin gần nhất từ group Đối soát
        async for msg in client.iter_messages(audit_dialog.entity, limit=100):
            if not msg.text:
                continue
            msg_date = msg.date.astimezone(VN_TZ)
            cursor.execute("SELECT id FROM raw_messages WHERE msg_id = ? AND chat_id = ?", (msg.id, audit_dialog.id))
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

            reply_to_id = msg.reply_to.reply_to_msg_id if msg.reply_to else None
            res = classify_message(text, sender_name, audit_dialog.title)
            
            category = "KRC - Đối soát"
            priority = res.get("priority", "P2") if res else "P2"
            issue_type = res.get("issue_type", "Khác") if res else "Khác"
            date_str = msg_date.strftime("%Y-%m-%d %H:%M:%S")

            cursor.execute("""
                INSERT INTO raw_messages (msg_id, chat_id, chat_title, sender_id, sender_name, username, message_text, category, priority, issue_type, reply_to_msg_id, created_at, is_read, is_dismissed)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 0, 0)
            """, (msg.id, audit_dialog.id, audit_dialog.title, sender_id, sender_name, username, text, category, priority, issue_type, reply_to_id, date_str))

            if issue_type in ["Thiếu", "Thừa", "XCL", "Sự cố Tài xế"]:
                cursor.execute("""
                    INSERT INTO priority_cases (msg_id, chat_title, sender_name, category, priority, content, status, issue_type, created_at, is_read, is_dismissed)
                    VALUES (?, ?, ?, ?, ?, ?, 'Chờ xử lý', ?, ?, 0, 0)
                """, (msg.id, audit_dialog.title, sender_name, category, priority, text, issue_type, date_str))

            saved_cnt += 1

        conn.commit()

    # Quét các tin nhắn cảnh báo đã gửi bởi chính tài khoản Thư Đoàn trong 3 ngày qua để cập nhật sent_alert_time
    sent_cnt = 0
    try:
        me = await client.get_me()
        cutoff = datetime.now(VN_TZ) - timedelta(days=3)
        for d in dialogs:
            if not (d.is_group or d.is_channel):
                continue
            c_title = d.title or "Group"
            if is_group_excluded(c_title):
                continue
            try:
                async for m in client.iter_messages(d.entity, limit=20):
                    m_dt = m.date.astimezone(VN_TZ)
                    if m_dt < cutoff:
                        break
                    if m.sender_id == me.id and m.text:
                        cursor.execute("SELECT id FROM raw_messages WHERE msg_id = ? AND chat_id = ?", (m.id, d.id))
                        if not cursor.fetchone():
                            cursor.execute("""
                                INSERT INTO raw_messages (msg_id, chat_id, chat_title, sender_id, sender_name, username, message_text, category, priority, issue_type, reply_to_msg_id, created_at, is_read, is_dismissed)
                                VALUES (?, ?, ?, ?, ?, ?, ?, 'Tin Đã Báo', 'P3', 'Khác', ?, ?, 0, 0)
                            """, (m.id, d.id, c_title, me.id, f"{me.first_name} {me.last_name or ''}".strip(), f"@{me.username or ''}", m.text.strip(), m.reply_to.reply_to_msg_id if m.reply_to else None, m_dt.strftime("%Y-%m-%d %H:%M:%S")))
                            sent_cnt += 1
            except Exception:
                pass
        conn.commit()
    except Exception:
        pass

    conn.close()
    await client.disconnect()
    return {"success": True, "saved_audit_count": saved_cnt, "saved_sent_count": sent_cnt}

def sync_telegram_audit_group_and_alerts():
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        res = loop.run_until_complete(_do_sync_telegram())
        return res
    finally:
        loop.close()
