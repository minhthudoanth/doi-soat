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
    from progress_tracker import reset_broadcast_progress, update_broadcast_progress, finish_broadcast_progress
    reset_broadcast_progress(len(chat_ids), batch_id)

    success_count = 0
    failed = []
    sent_records = []

    adaptive_delay = 0.0

    for idx, cid in enumerate(chat_ids):
        try:
            target = int(cid)
            chat_name = store_titles.get(target, f"ST_{target}")
            now_t = datetime.now().strftime('%H:%M:%S')
            update_broadcast_progress(idx, len(chat_ids), chat_name, f"Đang gửi {idx+1}/{len(chat_ids)}: {chat_name}...", success_count, len(failed))

            # 1. Giả lập hành vi người thật: gửi action Typing trước khi gửi tin
            try:
                from telethon.tl import types, functions
                await client(functions.messages.SetTypingRequest(peer=target, action=types.SendMessageTypingAction()))
                await asyncio.sleep(round(random.uniform(0.6, 1.2), 2))
            except Exception:
                pass

            msg = await client.send_message(target, message_text)
            success_count += 1
            chat_name = store_titles.get(target, f"ST_{target}")
            sent_records.append((batch_id, target, chat_name, msg.id, message_text))
            now_t = datetime.now().strftime('%H:%M:%S')
            update_broadcast_progress(idx + 1, len(chat_ids), chat_name, f"Đã gửi {idx+1}/{len(chat_ids)}: {chat_name}", success_count, len(failed), log_entry=f"[{now_t}] ✅ {chat_name} - Gửi thành công")

            # 3. Smart Jitter Delay (2.5s - 4.2s ngẫu nhiên + độ trễ thích ứng)
            delay_sec = round(random.uniform(2.5, 4.2) + adaptive_delay, 2)
            await asyncio.sleep(delay_sec)

            # 2. Cơ chế nghỉ giải lao (Batch Chunking & Smart Cooldown): cứ 15 ST nghỉ 12s - 18s
            if (idx + 1) % 15 == 0 and (idx + 1) < len(chat_ids):
                cooldown = round(random.uniform(12.0, 18.0), 1)
                now_t = datetime.now().strftime('%H:%M:%S')
                update_broadcast_progress(idx + 1, len(chat_ids), chat_name, f"⏳ [Anti-Spam] Nghỉ giải lao {cooldown}s sau {idx+1} ST...", success_count, len(failed), log_entry=f"[{now_t}] ☕ Nghỉ giải lao chống SpamBot {cooldown}s...")
                print(f"[*] [Broadcast] Đã gửi {idx+1}/{len(chat_ids)} ST. Nghỉ giải lao {cooldown}s (Anti-Spam Cooldown)...", flush=True)
                await asyncio.sleep(cooldown)

        except errors.FloodWaitError as e:
            # 4. Tự động xử lý & thích ứng FloodWait (Auto-Backoff)
            wait_time = e.seconds + 2
            now_t = datetime.now().strftime('%H:%M:%S')
            update_broadcast_progress(idx, len(chat_ids), chat_name, f"⚠️ Telegram FloodWait: Tạm dừng {wait_time}s...", success_count, len(failed), log_entry=f"[{now_t}] ⚠️ Chờ FloodWait {wait_time}s...")
            print(f"[!] Gặp FloodWait: Chờ {wait_time}s và tự động tăng độ trễ thích ứng...", flush=True)
            adaptive_delay += 1.5
            await asyncio.sleep(wait_time)
            try:
                msg = await client.send_message(target, message_text)
                success_count += 1
                chat_name = store_titles.get(target, f"ST_{target}")
                sent_records.append((batch_id, target, chat_name, msg.id, message_text))
                update_broadcast_progress(idx + 1, len(chat_ids), chat_name, f"Đã gửi lại thành công: {chat_name}", success_count, len(failed), log_entry=f"[{now_t}] ✅ {chat_name} (sau FloodWait) - Thành công")
            except Exception as e2:
                failed.append({"chat_id": cid, "error": str(e2)})
                update_broadcast_progress(idx + 1, len(chat_ids), chat_name, f"Lỗi gửi {chat_name}", success_count, len(failed), log_entry=f"[{now_t}] ❌ {chat_name} - Lỗi: {e2}")
        except Exception as e:
            failed.append({"chat_id": cid, "error": str(e)})
            now_t = datetime.now().strftime('%H:%M:%S')
            update_broadcast_progress(idx + 1, len(chat_ids), chat_name, f"Lỗi gửi {chat_name}", success_count, len(failed), log_entry=f"[{now_t}] ❌ {chat_name} - Lỗi: {e}")

    await client.disconnect()
    finish_broadcast_progress(success_count, len(failed))

    # Lưu thông tin các tin nhắn đã gửi để phục vụ chức năng thu hồi
    if sent_records:
        try:
            from database import get_optimized_conn
            conn = get_optimized_conn()
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

    
    # 1. ƯU TIÊN TUYỆT ĐỐI: Khớp chính xác mã ST (word boundary) trong group KRC/RAU
    for st in stores:
        t = st['chat_title'].upper()
        if 'KRC' in t or 'RAU' in t:
            if re.search(r'\b' + re.escape(s) + r'\b', t):
                return st
                
    # 2. Khớp theo alias chính xác trong group KRC/RAU
    if alias != s:
        for st in stores:
            t = st['chat_title'].upper()
            if 'KRC' in t or 'RAU' in t:
                if re.search(r'\b' + re.escape(alias) + r'\b', t) or alias in t:
                    return st

    # 3. Tìm group KRC chứa s dạng substring
    for st in stores:
        t = st['chat_title'].upper()
        if 'KRC' in t or 'RAU' in t:
            if s in t:
                return st

    # 4. Tìm group bất kỳ khớp mã chính xác
    for st in stores:
        t = st['chat_title'].upper()
        if re.search(r'\b' + re.escape(s) + r'\b', t):
            return st

    # 5. Tìm group bất kỳ theo alias hoặc substring
    for st in stores:
        t = st['chat_title'].upper()
        if (alias != s and alias in t) or s in t:
            return st

    return None

async def get_store_manager_tags(chat_id):
    """
    Lấy dòng tag quản lý theo đúng quy tắc ưu tiên:
    1. Tuyệt đối không tag Hà Trang Smartlog và team SCM.
    2. Nếu có SM: Ưu tiên tag SM.
    3. Nếu KHÔNG có SM: Tag SL / TC / GSM.
    """
    return await get_store_manager_tag_line(chat_id)

EXCLUDED_USERNAMES = {
    'hatrang290303', 'minhthudoan', 'long_sc015349', 'tunhipham', 
    'hapham_scm', 'nnhau2110', 'camnhung_scm', 'hubert286', 
    'doi_soat_scm_bot', 'phutrantn', 'vo_tan7411', 'quanghieu_sc007693',
    'quacamnhieuvitaminc'
}
EXCLUDED_KEYWORDS = [
    'smartlog', 'scm', 'sc017084', 'sc015349', 'sc012433', 
    'sc007251', 'sc015700', 'sc011297', 'sc003147', 'sc005651',
    'hatrang', 'hà trang'
]

def is_user_excluded_from_tags(p, full_name, title_rk=''):
    if p.bot or p.is_self:
        return True
    un = (p.username or '').lower().strip()
    if un in EXCLUDED_USERNAMES:
        return True
    if any(kw in un for kw in ['smartlog', 'hatrang', 'scm']):
        return True
    combined = f"{full_name} {title_rk}".lower()
    for kw in EXCLUDED_KEYWORDS:
        if kw in combined:
            return True
    return False

async def get_forum_rau_topic_id(client, chat_id):
    """
    Với các group DC dạng Forum/Topics, tìm channel/topic 'Rau' / 'Rau Củ' / 'KRC'
    để tự động đẩy tin nhắn vào đúng chuyên mục.
    """
    try:
        entity = await client.get_entity(int(chat_id))
        if getattr(entity, 'forum', False):
            from telethon import functions
            res = await client(functions.messages.GetForumTopicsRequest(
                peer=entity, offset_date=None, offset_id=0, offset_topic=0, limit=100
            ))
            for t in res.topics:
                title_clean = t.title.strip().upper()
                if any(k in title_clean for k in ['RAU', 'RAU CỦ', 'KRC']):
                    return t.id
    except Exception as e:
        print(f"[!] Lỗi tìm topic Rau trong group {chat_id}: {e}")
    return None

async def get_store_manager_tag_line(chat_id, client=None):
    """
    Lấy dòng tag quản lý theo đúng quy tắc ưu tiên:
    1. Tuyệt đối không tag đối tác/vendor (Hà Trang Smartlog @HaTrang290303) và team SCM.
    2. Nếu có SM: Ưu tiên tag SM.
    3. Nếu KHÔNG có SM: Tag SL / TC / GSM.
    4. Định dạng mention chuẩn Telegram: @username hoặc [Họ Tên](tg://user?id=123) để kích hoạt tag thật.
    5. Tự động lưu cache vào CSDL store_tag_cache để tái sử dụng ngay lập tức.
    """
    if not chat_id:
        return "@sm @tc @gsm"

    # 0. Kiểm tra cache trong CSDL
    try:
        from database import get_optimized_conn
        conn_c = get_optimized_conn()
        c_c = conn_c.cursor()
        c_c.execute("CREATE TABLE IF NOT EXISTS store_tag_cache (chat_id TEXT PRIMARY KEY, tag_line TEXT, updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)")
        c_c.execute("SELECT tag_line FROM store_tag_cache WHERE chat_id = ?", (str(chat_id),))
        r_c = c_c.fetchone()
        if r_c and r_c[0] and r_c[0] != "@sm @tc @gsm":
            cached_tag = r_c[0]
            if client is None:
                conn_c.close()
                return cached_tag
        conn_c.close()
    except Exception:
        pass

    should_disconnect = False
    try:
        if client is None:
            import tempfile, shutil
            temp_dir = tempfile.gettempdir()
            ts_name = os.path.join(temp_dir, f"temp_tag_{int(time.time()*1000)}")
            orig_s = os.path.join(BASE_DIR, f"{SESSION_NAME}.session")
            if os.path.exists(orig_s):
                shutil.copy2(orig_s, ts_name + ".session")
                client = TelegramClient(ts_name, API_ID, API_HASH)
            else:
                client = TelegramClient(SESSION_NAME, API_ID, API_HASH)
            await client.connect()
            should_disconnect = True
            if not await client.is_user_authorized():
                return "@sm @tc @gsm"

        participants = await client.get_participants(int(chat_id))
        sm_tags = []
        backup_tags = [] # SL, TC, GSM

        for p in participants:
            title_rk = (getattr(p, 'participant', None) and getattr(p.participant, 'rank', '')) or ''
            fn = (p.first_name or '').strip()
            ln = (p.last_name or '').strip()
            full_name = f"{fn} {ln}".strip()
            if not full_name or is_user_excluded_from_tags(p, full_name, title_rk):
                continue

            user_str = f"{full_name} {title_rk}".upper()
            # Nếu có username thì dùng @username, nếu không dùng cú pháp tg://user?id= để mention thật
            tag_val = f"@{p.username}" if p.username else f"[{full_name}](tg://user?id={p.id})"

            # 1. Kiểm tra SM
            is_sm = bool(re.search(r'\bSM\d*(?:\(TT\))?\b', user_str) or 'CỬA HÀNG TRƯỞNG' in user_str or 'STORE MANAGER' in user_str)
            if is_sm and not bool(re.search(r'\bGSM\d*\b', user_str)):
                sm_tags.append(tag_val)
                continue

            # 2. Kiểm tra SL, TC, GSM (bao gồm GSM27, TC, TCTT...)
            is_backup = bool(re.search(r'\b(SL\d*|TC\d*|GSM\d*|TCTT\d*|TC\(TT\)|TRƯỞNG CA|CHỦ CA|LEAD)\b', user_str))
            if is_backup:
                backup_tags.append(tag_val)

        res_tag = "@sm @tc @gsm"
        # Quy tắc: nếu có SM -> tag SM
        if sm_tags:
            seen = set()
            u_sm = [x for x in sm_tags if not (x in seen or seen.add(x))]
            res_tag = " ".join(u_sm)
        # Nếu không có SM -> tag SL, TC, GSM
        elif backup_tags:
            seen = set()
            u_bk = [x for x in backup_tags if not (x in seen or seen.add(x))]
            res_tag = " ".join(u_bk)

        # Lưu cache nếu lấy được tag hợp lệ
        if res_tag and res_tag != "@sm @tc @gsm":
            try:
                from database import get_optimized_conn
                conn_w = get_optimized_conn()
                c_w = conn_w.cursor()
                c_w.execute("CREATE TABLE IF NOT EXISTS store_tag_cache (chat_id TEXT PRIMARY KEY, tag_line TEXT, updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)")
                c_w.execute("INSERT OR REPLACE INTO store_tag_cache (chat_id, tag_line, updated_at) VALUES (?, ?, CURRENT_TIMESTAMP)", (str(chat_id), res_tag))
                conn_w.commit()
                conn_w.close()
            except Exception:
                pass

        return res_tag
    except Exception as e:
        print(f"Lỗi get_store_manager_tag_line: {e}")
        return "@sm @tc @gsm"
    finally:
        if should_disconnect and client:
            try:
                await client.disconnect()
            except Exception:
                pass

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

