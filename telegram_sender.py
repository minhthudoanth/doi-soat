import os
import sys
import asyncio
import sqlite3
import re


BASE_DIR = os.path.dirname(os.path.abspath(__file__))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

if sys.platform == 'win32':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
        sys.stderr.reconfigure(encoding='utf-8')
    except Exception:
        pass


import random
from telethon import TelegramClient, errors
from config import API_ID, API_HASH, SESSION_NAME, DB_PATH
from classifier import is_group_excluded


async def send_telegram_messages(chat_ids: list, message_text: str):
    """
    Gửi tin nhắn Telegram tự động đến danh sách chat_id được chọn
    Tích hợp cơ chế Anti-Flood / Smart Delay để bảo vệ an toàn 100% cho tài khoản
    Tự động ghi nhận batch_id và message_id vào Database để hỗ trợ thu hồi tin nhắn
    """
    from datetime import datetime
    if not chat_ids or not message_text.strip():
        return {"success": False, "sent_count": 0, "errors": ["Thiếu nội dung hoặc danh sách ST"]}

    client = TelegramClient(SESSION_NAME, API_ID, API_HASH)
    await client.connect()

    if not await client.is_user_authorized():
        await client.disconnect()
        return {"success": False, "sent_count": 0, "errors": ["Chưa đăng nhập Telegram"]}

    # Lấy map tên ST để lưu lịch sử
    store_titles = {}
    try:
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.execute("SELECT chat_id, chat_title FROM raw_messages GROUP BY chat_id")
        store_titles = {int(r[0]): r[1] for r in c.fetchall() if r[0]}
        conn.close()
    except Exception:
        pass

    batch_id = datetime.now().strftime('%Y%m%d_%H%M%S')
    success_count = 0
    failed = []
    sent_records = []

    for cid in chat_ids:
        try:
            target = int(cid)
            msg = await client.send_message(target, message_text)
            success_count += 1
            chat_name = store_titles.get(target, f"ST_{target}")
            sent_records.append((batch_id, target, chat_name, msg.id, message_text))

            # Delay ngẫu nhiên từ 1.8s - 3.2s để giả lập hành vi người thật, chống Rate Limit
            delay_sec = round(random.uniform(1.8, 3.2), 2)
            await asyncio.sleep(delay_sec)
        except errors.FloodWaitError as e:
            print(f"[!] Gặp FloodWait: Chờ {e.seconds}s...")
            await asyncio.sleep(e.seconds + 1)
            try:
                msg = await client.send_message(target, message_text)
                success_count += 1
                chat_name = store_titles.get(target, f"ST_{target}")
                sent_records.append((batch_id, target, chat_name, msg.id, message_text))
            except Exception as e2:
                failed.append({"chat_id": cid, "error": str(e2)})
        except Exception as e:
            failed.append({"chat_id": cid, "error": str(e)})

    await client.disconnect()

    # Lưu thông tin các tin nhắn đã gửi để phục vụ chức năng thu hồi
    if sent_records:
        try:
            conn = sqlite3.connect(DB_PATH)
            c = conn.cursor()
            c.executemany("""
                INSERT INTO sent_broadcast_history (batch_id, chat_id, chat_title, msg_id, message_text)
                VALUES (?, ?, ?, ?, ?)
            """, sent_records)
            conn.commit()
            conn.close()
        except Exception as e:
            print(f"[!] Lỗi lưu sent_broadcast_history: {e}", flush=True)

    return {
        "success": True,
        "batch_id": batch_id,
        "sent_count": success_count,
        "failed_count": len(failed),
        "failed": failed
    }

async def recall_telegram_batch(batch_id: str = None):
    """
    Thu hồi tin nhắn đã gửi đối với TẤT CẢ mọi người trong group siêu thị (revoke=True)
    Nếu không truyền batch_id, sẽ tự động thu hồi đợt gửi gần nhất.
    """
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    if not batch_id:
        cursor.execute("SELECT batch_id FROM sent_broadcast_history WHERE is_recalled = 0 ORDER BY id DESC LIMIT 1")
        row = cursor.fetchone()
        if not row:
            conn.close()
            return {"success": False, "error": "Không tìm thấy tin nhắn nào có thể thu hồi gần đây!"}
        batch_id = row['batch_id']
        
    cursor.execute("SELECT id, chat_id, chat_title, msg_id FROM sent_broadcast_history WHERE batch_id = ? AND is_recalled = 0", (batch_id,))
    msgs = cursor.fetchall()
    if not msgs:
        conn.close()
        return {"success": False, "error": "Đợt tin nhắn này đã được thu hồi trước đó hoặc không tồn tại!"}
        
    client = TelegramClient(SESSION_NAME, API_ID, API_HASH)
    await client.connect()
    if not await client.is_user_authorized():
        await client.disconnect()
        conn.close()
        return {"success": False, "error": "Tài khoản Telegram chưa được ủy quyền."}
        
    recalled_ids = []
    failed_items = []
    
    for m in msgs:
        try:
            cid = int(m['chat_id'])
            mid = int(m['msg_id'])
            # revoke=True xóa tin nhắn đối với TẤT CẢ thành viên trong group
            await client.delete_messages(cid, [mid], revoke=True)
            recalled_ids.append(m['id'])
            await asyncio.sleep(0.3)
        except Exception as e:
            failed_items.append({"chat_id": m['chat_id'], "chat_title": m['chat_title'], "error": str(e)})
            
    if recalled_ids:
        cursor.execute(f"UPDATE sent_broadcast_history SET is_recalled = 1 WHERE id IN ({','.join('?'*len(recalled_ids))})", recalled_ids)
        conn.commit()
        
    await client.disconnect()
    conn.close()
    
    return {
        "success": True,
        "batch_id": batch_id,
        "recalled_count": len(recalled_ids),
        "failed_count": len(failed_items),
        "failed": failed_items,
        "message": f"Đã thu hồi thành công {len(recalled_ids)} tin nhắn khỏi các group Siêu Thị!"
    }

def get_recent_sent_batches(limit: int = 15):
    """
    Lấy danh sách các đợt gửi tin gần nhất kèm trạng thái đã thu hồi hay chưa
    """
    try:
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute("""
            SELECT batch_id, 
                   min(message_text) as message_text, 
                   count(*) as total_stores,
                   sum(case when is_recalled = 1 then 1 else 0 end) as recalled_stores,
                   min(created_at) as sent_at
            FROM sent_broadcast_history
            GROUP BY batch_id
            ORDER BY min(id) DESC
            LIMIT ?
        """, (limit,))
        batches = []
        for r in cursor.fetchall():
            batches.append({
                "batch_id": r["batch_id"],
                "message_text": r["message_text"],
                "total_stores": r["total_stores"],
                "recalled_stores": r["recalled_stores"],
                "is_fully_recalled": r["recalled_stores"] >= r["total_stores"],
                "sent_at": r["sent_at"]
            })
        conn.close()
        return batches
    except Exception as e:
        return []


def get_all_store_chats():
    """
    Lấy toàn bộ danh sách group Siêu Thị & Kho hợp lệ từ SQLite
    """
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        SELECT DISTINCT chat_id, chat_title 
        FROM raw_messages 
        WHERE chat_title IS NOT NULL AND chat_title != ''
        ORDER BY chat_title ASC
    """)
    rows = cursor.fetchall()
    conn.close()

    stores = []
    for cid, title in rows:
        if is_group_excluded(title):
            continue
        # Xác định nhóm kho
        t_low = title.lower()
        dept = "KRC"
        if "aba" in t_low or "đông mát" in t_low or "thịt" in t_low or "cá" in t_low or "mđ" in t_low:
            dept = "Đông Mát Thịt Cá"
        elif "dc" in t_low or "kho tổng" in t_low:
            dept = "DC"
        elif "krc" in t_low or "rau" in t_low:
            dept = "KRC"

        stores.append({
            "chat_id": cid,
            "chat_title": title,
            "department": dept
        })
    return stores

from datetime import datetime, timedelta


def calculate_deadline(current_dt=None):
    """
    Tính mốc deadline cho Siêu thị (3-5 tiếng để check, làm tròn theo các mốc 12h, 15h, 17h, 19h, 21h, không cần năm)
    """
    if not current_dt:
        current_dt = datetime.now()
        
    milestones = [12, 15, 17, 19, 21]
    cur_time = current_dt.hour + current_dt.minute / 60.0
    
    for m in milestones:
        if (m - cur_time) >= 2.8: # Cho ST ít nhất gần 3 tiếng
            return f"{m}h ngày {current_dt.strftime('%d/%m')}"
            
    # Nếu gửi sau 18h30 tối -> Deadline là 12h trưa ngày mai (D+1)
    next_day = current_dt + timedelta(days=1)
    return f"12h ngày {next_day.strftime('%d/%m')}"


def find_krc_store_chat(store_str, stores_list=None):
    """
    Tìm group Telegram KRC của Siêu thị dựa vào mã/tên ST
    """
    if not store_str or store_str == '---':
        return None
        
    stores = stores_list if stores_list is not None else get_all_store_chats()
    s = store_str.strip().upper()
    
    from kingfood_api import STORE_ALIAS_MAP
    alias = STORE_ALIAS_MAP.get(s, s).upper()

    
    # 1. Tìm group KRC khớp chính xác mã (word boundary) hoặc tên
    for st in stores:
        t = st['chat_title'].upper()
        if 'KRC' in t or 'RAU' in t:
            if re.search(r'\b' + re.escape(s) + r'\b', t) or (alias != s and alias in t):
                return st
                
    # 2. Tìm group KRC chứa s dạng substring
    for st in stores:
        t = st['chat_title'].upper()
        if 'KRC' in t or 'RAU' in t:
            if s in t or alias in t:
                return st

    # 3. Tìm group bất kỳ của ST đó
    for st in stores:
        t = st['chat_title'].upper()
        if re.search(r'\b' + re.escape(s) + r'\b', t) or s in t or alias in t:
            return st

            
    return None

async def get_store_manager_tags(chat_id):
    """
    Lấy danh sách username các quản lý (SM, TC, GSM, Trưởng ca...) trong group
    """
    if not chat_id:
        return ""
    try:
        client = TelegramClient(SESSION_NAME, API_ID, API_HASH)
        await client.connect()
        if not await client.is_user_authorized():
            await client.disconnect()
            return ""
            
        participants = await client.get_participants(int(chat_id))
        tags = []
        for p in participants:
            if p.bot or p.is_self:
                continue
            title = (getattr(p, 'participant', None) and getattr(p.participant, 'rank', '')) or ''
            first_name = (p.first_name or '').upper()
            last_name = (p.last_name or '').upper()
            user_str = f"{first_name} {last_name} {title}".upper()
            
            # Nhận diện SM, TC, GSM, Quản lý, Trưởng ca
            is_mgr = any(k in user_str for k in ['SM', 'TC', 'GSM', 'QL', 'TRƯỞNG CA', 'CỬA HÀNG TRƯỞNG', 'LEAD', 'CHỦ CA'])
            if is_mgr and p.username:
                tags.append(f"@{p.username}")
                
        await client.disconnect()
        return " ".join(tags)
    except Exception as e:
        print(f"Lỗi get_store_manager_tags: {e}")
        return ""

async def get_store_manager_tag_line(chat_id):
    """
    Lấy dòng thông tin tag quản lý riêng biệt cho ST:
    Ví dụ: @thachphanHV2 ⛑ HCM1 - HV2 - TC - Trúc Nguyễn - SC013957 ⛑
    Nếu không tìm thấy ai thì fallback về @sm @tc @gsm
    """
    if not chat_id:
        return "@sm @tc @gsm"
    try:
        client = TelegramClient(SESSION_NAME, API_ID, API_HASH)
        await client.connect()
        if not await client.is_user_authorized():
            await client.disconnect()
            return "@sm @tc @gsm"
            
        participants = await client.get_participants(int(chat_id))
        tag_items = []
        for p in participants:
            if p.bot or p.is_self:
                continue
            title_rk = (getattr(p, 'participant', None) and getattr(p.participant, 'rank', '')) or ''
            fn = (p.first_name or '').strip()
            ln = (p.last_name or '').strip()
            full_name = f"{fn} {ln}".strip()
            user_str = f"{full_name} {title_rk}".upper()
            
            is_mgr = any(k in user_str for k in ['SM', 'TC', 'GSM', 'QL', 'TRƯỞNG CA', 'CỬA HÀNG TRƯỞNG', 'LEAD', 'CHỦ CA'])
            if is_mgr:
                if p.username:
                    tag_items.append(f"@{p.username}")
                elif full_name:
                    tag_items.append(full_name)
                    
        await client.disconnect()
        if tag_items:
            seen = set()
            unique_tags = [x for x in tag_items if not (x in seen or seen.add(x))]
            return " ".join(unique_tags)
        return "@sm @tc @gsm"
    except Exception as e:
        print(f"Lỗi get_store_manager_tag_line: {e}")
        return "@sm @tc @gsm"

async def forward_and_send_surplus_alert(target_chat_id, source_chat_id, msg_id, message_text):
    """
    Chuyển tiếp tin nhắn từ group Đối Soát sang group KRC của ST nhận dư
    và gửi kèm tin nhắn yêu cầu check với deadline và tag SM/TC/GSM.
    """
    if not target_chat_id or not message_text.strip():
        return {"success": False, "error": "Thiếu group nhận hoặc nội dung tin nhắn"}

    client = TelegramClient(SESSION_NAME, API_ID, API_HASH)
    await client.connect()

    if not await client.is_user_authorized():
        await client.disconnect()
        return {"success": False, "error": "Chưa đăng nhập tài khoản Telegram"}

    try:
        target = int(target_chat_id)
        # 1. Chuyển tiếp tin nhắn gốc từ group Đối soát (nếu có)
        if source_chat_id and msg_id:
            try:
                await client.forward_messages(
                    entity=target,
                    messages=int(msg_id),
                    from_peer=int(source_chat_id)
                )
                await asyncio.sleep(0.5)
            except Exception as fe:
                print(f"[!] Lỗi forward message gốc: {fe}")

        # 2. Gửi tin nhắn yêu cầu check
        await client.send_message(target, message_text)
        await client.disconnect()
        return {"success": True}
    except Exception as e:
        await client.disconnect()
        return {"success": False, "error": str(e)}

