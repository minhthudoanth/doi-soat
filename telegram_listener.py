import os
import sys

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

class RobustLogger:
    def __init__(self, log_filename, orig_stream):
        self.orig_stream = orig_stream
        self.log_path = os.path.join(BASE_DIR, log_filename)
        self._f = None
        try:
            self._f = open(self.log_path, 'a', encoding='utf-8', buffering=1)
        except Exception:
            pass

    def write(self, data):
        if self._f:
            try:
                self._f.write(data)
                self._f.flush()
            except Exception:
                pass
        if self.orig_stream and hasattr(self.orig_stream, 'write') and self.orig_stream != self:
            try:
                self.orig_stream.write(data)
                if hasattr(self.orig_stream, 'flush'):
                    self.orig_stream.flush()
            except Exception:
                pass

    def flush(self):
        if self._f:
            try:
                self._f.flush()
            except Exception:
                pass
        if self.orig_stream and hasattr(self.orig_stream, 'flush') and self.orig_stream != self:
            try:
                self.orig_stream.flush()
            except Exception:
                pass

    def isatty(self):
        return False

if sys.platform == 'win32':
    try:
        if sys.stdout and hasattr(sys.stdout, 'reconfigure'):
            sys.stdout.reconfigure(encoding='utf-8')
        if sys.stderr and hasattr(sys.stderr, 'reconfigure'):
            sys.stderr.reconfigure(encoding='utf-8')
    except Exception:
        pass

sys.stdout = RobustLogger('listener.log', sys.stdout)
sys.stderr = RobustLogger('listener.log', sys.stderr)

import asyncio
import sqlite3
from datetime import datetime, timezone, timedelta
from telethon import TelegramClient, events
from config import API_ID, API_HASH, SESSION_NAME, DB_PATH
from classifier import classify_message, is_group_excluded
from database import init_db

VN_TZ = timezone(timedelta(hours=7))

async def start_listener():
    init_db()
    from database import get_optimized_conn
    conn = get_optimized_conn()
    cursor = conn.cursor()

    client = TelegramClient(SESSION_NAME, API_ID, API_HASH)
    await client.connect()
    
    if not await client.is_user_authorized():
        print("[!] Client chưa đăng nhập Telegram!", flush=True)
        return

    me = await client.get_me()
    print(f"[*] REALTIME LISTENER ĐANG CHẠY: {me.first_name} (ID: {me.id})", flush=True)

    # 0. Tự động đồng bộ các tin nhắn trong 7 ngày gần nhất lúc khởi động
    try:
        now_vn = datetime.now(VN_TZ)
        cutoff_time = datetime(now_vn.year, now_vn.month, now_vn.day, 0, 0, 0, tzinfo=VN_TZ) - timedelta(days=7)
        dialogs = await client.get_dialogs(limit=150)
        backfill_cnt = 0
        for d in dialogs:
            if (d.is_group or d.is_channel) and d.date and d.date.astimezone(VN_TZ) >= cutoff_time:
                chat_title = d.title or "Group"
                if is_group_excluded(chat_title):
                    continue
                try:
                    async for msg in client.iter_messages(d.entity, limit=60):
                        if not msg.text:
                            continue
                        msg_date = msg.date.astimezone(VN_TZ)
                        if msg_date < cutoff_time:
                            break
                        cursor.execute("SELECT id FROM raw_messages WHERE msg_id = ? AND chat_id = ?", (msg.id, d.id))
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
                        res = classify_message(text, sender_name, chat_title)
                        if not res:
                            continue
                        category = res.get("category", "Khác")
                        priority = res.get("priority", "P3")
                        issue_type = res.get("issue_type", "Khác")
                        date_str = msg_date.strftime("%Y-%m-%d %H:%M:%S")

                        cursor.execute("""
                            INSERT INTO raw_messages (msg_id, chat_id, chat_title, sender_id, sender_name, username, message_text, category, priority, issue_type, reply_to_msg_id, created_at, is_read, is_dismissed)
                            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 0, 0)
                        """, (msg.id, d.id, chat_title, sender_id, sender_name, username, text, category, priority, issue_type, reply_to_id, date_str))

                        if issue_type in ["Thiếu", "Thừa", "XCL", "Sự cố Tài xế"]:
                            cursor.execute("""
                                INSERT INTO priority_cases (msg_id, chat_title, sender_name, category, priority, content, status, issue_type, created_at, is_read, is_dismissed)
                                VALUES (?, ?, ?, ?, ?, ?, 'Chờ xử lý', ?, ?, 0, 0)
                            """, (msg.id, chat_title, sender_name, category, priority, text, issue_type, date_str))
                        backfill_cnt += 1
                except Exception:
                    continue
        conn.commit()
        if backfill_cnt > 0:
            print(f"[*] Đã đồng bộ bổ sung {backfill_cnt} tin nhắn Telegram gần nhất vào hệ thống!", flush=True)
    except Exception as e:
        print(f"[!] Lỗi backfill telegram: {e}", flush=True)

    # 1. Bắt tin nhắn mới tức thì (Real-time New Message)
    @client.on(events.NewMessage(incoming=True))
    async def on_new_message(event):
        try:
            if not event.raw_text:
                return
            chat = await event.get_chat()
            chat_title = getattr(chat, 'title', None) or getattr(chat, 'first_name', 'Group')
            if is_group_excluded(chat_title):
                return
                
            sender = await event.get_sender()
            sender_name = "Ẩn danh"
            username = "Không có"
            sender_id = event.sender_id or 0
            if sender:
                fn = getattr(sender, 'first_name', '') or ''
                ln = getattr(sender, 'last_name', '') or ''
                sender_name = f"{fn} {ln}".strip() or "Ẩn danh"
                if getattr(sender, 'username', None):
                    username = f"@{sender.username}"

            text = event.raw_text.strip()
            res = classify_message(text, sender_name, chat_title)
            if not res:
                return
                
            category = res.get("category", "Khác")
            priority = res.get("priority", "P3")
            issue_type = res.get("issue_type", "Khác")
            
            msg_date = event.date.astimezone(VN_TZ)
            date_str = msg_date.strftime("%Y-%m-%d %H:%M:%S")
            
            # Trích xuất ID tin nhắn gốc nếu đây là tin Reply
            reply_to_id = getattr(event, 'reply_to_msg_id', None)
            if not reply_to_id and getattr(event, 'message', None) and getattr(event.message, 'reply_to', None):
                reply_to_id = getattr(event.message.reply_to, 'reply_to_msg_id', None)

            # Lưu vào raw_messages
            cursor.execute("""
                INSERT INTO raw_messages (msg_id, chat_id, chat_title, sender_id, sender_name, username, message_text, category, priority, issue_type, reply_to_msg_id, created_at, is_read, is_dismissed)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 0, 0)
            """, (event.id, event.chat_id, chat_title, sender_id, sender_name, username, text, category, priority, issue_type, reply_to_id, date_str))

            if issue_type in ["Thiếu", "Thừa", "XCL", "Sự cố Tài xế"]:
                cursor.execute("""
                    INSERT INTO priority_cases (msg_id, chat_title, sender_name, category, priority, content, status, issue_type, created_at, is_read, is_dismissed)
                    VALUES (?, ?, ?, ?, ?, ?, 'Chờ xử lý', ?, ?, 0, 0)
                """, (event.id, chat_title, sender_name, category, priority, text, issue_type, date_str))

            
            conn.commit()
            print(f"[+] [TIN MỚI REALTIME] {chat_title} | {sender_name}: {text[:50]}...", flush=True)
        except Exception as e:
            print(f"[!] Lỗi on_new_message: {e}", flush=True)

    # 2. Bắt sự kiện đã đọc trên Telegram (MessageRead Event)
    @client.on(events.MessageRead(inbox=True))
    async def on_message_read(event):
        try:
            max_id = event.max_id
            chat_id = event.chat_id
            cursor.execute("UPDATE raw_messages SET is_read = 1 WHERE chat_id = ? AND msg_id <= ?", (chat_id, max_id))
            cursor.execute("UPDATE priority_cases SET is_read = 1 WHERE msg_id IN (SELECT msg_id FROM raw_messages WHERE chat_id = ? AND msg_id <= ?)", (chat_id, max_id))
            conn.commit()
        except Exception as e:
            pass

    # 3. Vòng lặp đồng bộ định kỳ trạng thái Đã đọc mỗi 20 giây
    async def sync_read_status_loop():
        while True:
            try:
                await asyncio.sleep(20)
                dialogs = await client.get_dialogs(limit=250)
                for d in dialogs:
                    if d.is_group or d.is_channel:
                        max_read = getattr(d.dialog, 'read_inbox_max_id', 0) or 0
                        if max_read > 0:
                            cursor.execute("UPDATE raw_messages SET is_read = 1 WHERE chat_id = ? AND msg_id <= ? AND is_read = 0", (d.id, max_read))
                            cursor.execute("UPDATE priority_cases SET is_read = 1 WHERE msg_id IN (SELECT msg_id FROM raw_messages WHERE chat_id = ? AND msg_id <= ?) AND is_read = 0", (d.id, max_read))
                conn.commit()
            except Exception as e:
                pass

    asyncio.create_task(sync_read_status_loop())
    print("[*] Đang lắng nghe Telegram Realtime 24/7...", flush=True)
    await client.run_until_disconnected()

async def main():
    backoff = 3
    while True:
        try:
            await start_listener()
        except asyncio.CancelledError:
            print("[*] Telegram Listener đã dừng an toàn.")
            break
        except Exception as e:
            print(f"[!] Mất kết nối Telegram: {e}. Tự động kết nối lại sau {backoff}s...", flush=True)
            await asyncio.sleep(backoff)
            backoff = min(backoff * 2, 60)

if __name__ == '__main__':
    import socket
    _lock_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        _lock_socket.bind(('127.0.0.1', 5001))
    except OSError:
        print("[*] Telegram Listener đã đang chạy trên hệ thống (Port 5001). Bỏ qua tiến trình trùng lặp.", flush=True)
        sys.exit(0)

    asyncio.run(main())

