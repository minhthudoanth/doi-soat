import os
import sys

# Thêm thư mục hiện tại vào sys.path
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

import asyncio
import logging
from telethon import TelegramClient, events
from config import API_ID, API_HASH, SESSION_NAME

from classifier import classify_message
from database import init_db, save_message, get_recent_cases, get_stats_today

# Thiết lập logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Khởi tạo Telegram Client
client = TelegramClient(SESSION_NAME, API_ID, API_HASH)

@client.on(events.NewMessage(incoming=True))
async def handle_incoming_message(event):
    """
    Lắng nghe thụ động toàn bộ tin nhắn đến (từ Group, Channel, Chat riêng)
    """
    try:
        # Bỏ qua tin nhắn không có văn bản
        if not event.raw_text:
            return

        chat = await event.get_chat()
        sender = await event.get_sender()
        
        chat_title = getattr(chat, 'title', None) or getattr(chat, 'first_name', 'Chat riêng')
        chat_id = event.chat_id
        
        sender_name = "Ẩn danh"
        username = "Không có"
        sender_id = event.sender_id or 0
        
        if sender:
            first_name = getattr(sender, 'first_name', '') or ''
            last_name = getattr(sender, 'last_name', '') or ''
            sender_name = f"{first_name} {last_name}".strip() or "Ẩn danh"
            if getattr(sender, 'username', None):
                username = f"@{sender.username}"

        text = event.raw_text.strip()
        
        # Phân loại theo nội dung và tên Group (Bỏ qua tin nhắn tự động)
        category, priority, is_auto = classify_message(text, chat_title, sender_name)
        
        # Lưu vào SQLite
        save_message(
            msg_id=event.id,
            chat_id=chat_id,
            chat_title=chat_title,
            sender_id=sender_id,
            sender_name=sender_name,
            username=username,
            text=text,
            category=category,
            priority=priority
        )
        
        logger.info(f"[{priority}] [{category}] {chat_title} - {sender_name}: {text[:50]}...")
        
        # Nếu là case P1 (Khẩn cấp) và KHÔNG PHẢI tin tự động -> Bắn cảnh báo
        if "P1" in priority and not is_auto:
            alert_msg = (
                f"🚨 **[CẢNH BÁO SCM KHẨN CẤP - P1]**\n"
                f"━━━━━━━━━━━━━━━━━━\n"
                f"📍 **Nguồn:** {chat_title}\n"
                f"👤 **Người báo:** {sender_name} ({username})\n"
                f"📦 **Ngành hàng:** {category}\n"
                f"📝 **Nội dung:**\n_{text}_\n"
                f"━━━━━━━━━━━━━━━━━━\n"
                f"👉 _Vui lòng kiểm tra và phối hợp xử lý ngay!_"
            )
            await client.send_message('me', alert_msg)


    except Exception as e:
        logger.error(f"Lỗi khi xử lý tin nhắn: {e}")

@client.on(events.NewMessage(outgoing=True, chats='me'))
async def handle_saved_messages_commands(event):
    """
    Xử lý các lệnh tra cứu nhanh bạn tự gửi trong Saved Messages ('me')
    """
    cmd = event.raw_text.strip().lower()
    
    if cmd == ".help":
        help_text = (
            "🛠 **DANH SÁCH LỆNH TRA CỨU SCM USERBOT:**\n\n"
            "• `.summary` - Báo cáo tổng hợp tình hình hôm nay\n"
            "• `.urgent` hoặc `.p1` - Xem danh sách các case khẩn cấp tồn đọng\n"
            "• `.stats` - Thống kê số lượng tin theo ngành hàng\n"
            "• `.ping` - Kiểm tra trạng thái bot"
        )
        await event.reply(help_text)
        
    elif cmd == ".summary":
        cases = get_recent_cases(limit=8)
        cat_stats, pri_stats = get_stats_today()
        
        total_p1 = sum(c[1] for c in pri_stats if "P1" in c[0])
        total_p2 = sum(c[1] for c in pri_stats if "P2" in c[0])
        
        summary_text = (
            f"📊 **[TỔNG HỢP VẬN HÀNH SCM KINGFOOD HÔM NAY]**\n"
            f"━━━━━━━━━━━━━━━━━━\n"
            f"🔥 **Khẩn cấp (P1):** {total_p1} tin\n"
            f"⚡ **Cần xử lý (P2):** {total_p2} tin\n"
            f"━━━━━━━━━━━━━━━━━━\n"
            f"📋 **CÁC CASE GẦN NHẤT CẦN LƯU Ý:**\n"
        )
        
        if not cases:
            summary_text += "✅ Không có case tồn đọng!\n"
        else:
            for row in cases:
                case_id, st_name, reporter, cat, pri, content, status, dt = row
                icon = "🔴" if "P1" in pri else "🟡"
                summary_text += f"{icon} `[#{case_id}]` **{st_name}** ({cat}): {content[:60]}...\n"
                
        await event.reply(summary_text)
        
    elif cmd in [".urgent", ".p1"]:
        cases = get_recent_cases(limit=10, p1_only=True)
        if not cases:
            await event.reply("✅ Tuyệt vời! Hiện tại không có case P1 nào tồn đọng.")
        else:
            text = "🚨 **DANH SÁCH CÁC CASE P1 KHẨN CẤP:**\n\n"
            for row in cases:
                case_id, st_name, reporter, cat, pri, content, status, dt = row
                text += f"🔴 `[#{case_id}]` **{st_name}** ({reporter} - {dt}):\n_{content}_\n\n"
            await event.reply(text)
            
    elif cmd == ".stats":
        cat_stats, pri_stats = get_stats_today()
        text = "📈 **THỐNG KÊ TIN NHẮN HÔM NAY THEO NGÀNH HÀNG:**\n\n"
        for cat, count in cat_stats:
            text += f"• **{cat}:** {count} tin nhắn\n"
        await event.reply(text)
        
    elif cmd == ".ping":
        await event.reply("🟢 SCM Userbot đang chạy ngầm và lắng nghe tin nhắn ổn định 100%!")

async def main():
    logger.info("Dang khoi tao Co so du lieu SQLite...")
    init_db()
    
    logger.info("Dang khoi dong Telegram Client...")
    await client.start()
    
    me = await client.get_me()
    logger.info(f"[*] Dang nhap thanh cong voi tai khoan: {me.first_name} (@{me.username or 'Khong co'})")
    logger.info("[*] Bot dang am tham lang nghe toan bo tin nhan tu cac Group/Kenh...")
    
    # Gửi thông báo khởi động vào Saved Messages
    await client.send_message('me', "🟢 **SCM Auto-Check Bot đã bắt đầu hoạt động ngầm!**\nGõ `.help` hoặc `.summary` để xem các lệnh tra cứu nhanh.")
    
    await client.run_until_disconnected()


if __name__ == "__main__":
    asyncio.run(main())
