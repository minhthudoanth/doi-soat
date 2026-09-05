import os
import sys
import json
import urllib.request
from datetime import datetime, timezone, timedelta
import sqlite3
import random
import asyncio

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

if sys.platform == 'win32':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
        sys.stderr.reconfigure(encoding='utf-8')
    except Exception:
        pass

from config import DB_PATH, API_ID, API_HASH, SESSION_NAME
from kingfood_api import get_kingfood_token

VN_TZ = timezone(timedelta(hours=7))

SOURCE_WAREHOUSES = {
    'KRC': {
        'id': '5fdc170ebd89c10006f15b7c',
        'name': 'KHO RAU CỦ (KRC)'
    },
    'KRCBT': {
        'id': '6a3e383fe20b440007640326',
        'name': 'KHO QUÁ CẢNH BÁNH TƯƠI (KRCBT)'
    }
}

BRANCHES_CACHE = None
STORE_ALIAS_MAP_CACHE = None


def get_headers():
    token = get_kingfood_token()
    return {
        'Authorization': f'Bearer {token}',
        'x-access-token': token,
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)',
        'Accept': 'application/json, text/plain, */*'
    }


def load_all_branches():
    """
    Tải danh mục toàn bộ chi nhánh Kingfood từ API hoặc SQLite
    """
    global BRANCHES_CACHE
    if BRANCHES_CACHE:
        return BRANCHES_CACHE

    b_map = {}
    try:
        headers = get_headers()
        req = urllib.request.Request('https://api.kingfood.co/v1/branches?limit=500', headers=headers)
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read().decode('utf-8'))
            for b in data.get('items', []):
                bid = b.get('id')
                b_map[bid] = {
                    'id': bid,
                    'code': b.get('code', ''),
                    'name': b.get('name', '')
                }
    except Exception as e:
        print(f"[!] Lỗi tải chi nhánh từ API Kingfood: {e}", flush=True)

    # Bổ sung/fallback từ bảng sheet_store_list trong SQLite
    try:
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.execute("SELECT store_id, store_name FROM sheet_store_list")
        for sid, sname in c.fetchall():
            if sid and sid not in b_map:
                b_map[sid] = {'id': sid, 'code': sid, 'name': sname}
        conn.close()
    except Exception:
        pass

    BRANCHES_CACHE = b_map
    return BRANCHES_CACHE


def load_canonical_store_map():
    """
    Tải bản đồ ánh xạ Tên chi nhánh -> Mã cửa hàng chuẩn (KHI, HV2, D10, MZ2, VHT, A221...)
    """
    global STORE_ALIAS_MAP_CACHE
    if STORE_ALIAS_MAP_CACHE:
        return STORE_ALIAS_MAP_CACHE

    mapping = {}
    try:
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.execute("SELECT store_id, store_name FROM sheet_store_list")
        for sid, sname in c.fetchall():
            if sid and sname:
                mapping[sname.strip().upper()] = sid.strip().upper()
        conn.close()
    except Exception:
        pass

    STORE_ALIAS_MAP_CACHE = mapping
    return mapping


def resolve_store_id(branch_name, branch_code):
    """
    Chuyển đổi tên hoặc mã chi nhánh từ API thành store_id chuẩn trong hệ thống SCM
    """
    b_name_clean = (branch_name or '').strip().upper()
    b_code_clean = (branch_code or '').strip().upper()

    smap = load_canonical_store_map()

    # 1. Khớp chính xác tên
    if b_name_clean in smap:
        return smap[b_name_clean]

    # 2. Khớp chuỗi con
    for s_name_key, s_id in smap.items():
        if b_name_clean and (b_name_clean in s_name_key or s_name_key in b_name_clean):
            return s_id

    # 3. Tra bảng viết tắt mặc định
    from kingfood_api import STORE_ALIAS_MAP
    if b_code_clean in STORE_ALIAS_MAP:
        return b_code_clean

    return b_code_clean or b_name_clean


def fetch_pending_double_checks(target_date_str=None):
    """
    Lấy toàn bộ danh sách phiếu hậu kiểm KRC & KRCBT đang ở trạng thái Cần Hậu Kiểm (status = 1)
    Lọc theo ngày chỉ định (định dạng DD/MM/YYYY, mặc định là ngày hôm nay theo giờ VN)
    """
    now_vn = datetime.now(VN_TZ)
    if not target_date_str:
        target_date_str = now_vn.strftime('%d/%m/%Y')

    branches_map = load_all_branches()
    headers = get_headers()

    all_tickets = []
    store_groups = {}

    for wh_key, wh_info in SOURCE_WAREHOUSES.items():
        bid = wh_info['id']
        url = f"https://api.kingfood.co/v1/transfers/double-check?from_branch_id={bid}&status=1&limit=100"
        try:
            req = urllib.request.Request(url, headers=headers)
            with urllib.request.urlopen(req, timeout=12) as resp:
                data = json.loads(resp.read().decode('utf-8'))
                items = data.get('items', [])
                
                for it in items:
                    raw_created = it.get('created_at', '')
                    if not raw_created:
                        continue
                    dt_utc = datetime.fromisoformat(raw_created.replace('Z', '+00:00'))
                    dt_vn = dt_utc.astimezone(VN_TZ)
                    created_date_vn = dt_vn.strftime('%d/%m/%Y')

                    # Chỉ lấy các phiếu thuộc ngày cần kiểm tra
                    if target_date_str and created_date_vn != target_date_str:
                        continue

                    to_bid = it.get('to_branch_id')
                    b_info = branches_map.get(to_bid, {})
                    b_code = b_info.get('code') or it.get('to_branch_code', '')
                    b_name = b_info.get('name') or it.get('to_branch_name', '')

                    resolved_sid = resolve_store_id(b_name, b_code)

                    t_item = {
                        'source_key': wh_key,
                        'source_name': wh_info['name'],
                        'hk_code': it.get('code', ''),
                        'pt_code': it.get('transfer_code') or (it.get('transfer') or {}).get('code') or '---',
                        'raw_utc': raw_created,
                        'created_dt_vn': dt_vn,
                        'created_date_vn': created_date_vn,
                        'created_time_str': dt_vn.strftime('%d/%m %H:%M'),
                        'to_branch_id': to_bid,
                        'branch_code': b_code,
                        'branch_name': b_name,
                        'store_id': resolved_sid,
                        'status': it.get('status', 1),
                        'total_sku': it.get('total_sku') or it.get('sku') or 0,
                        'total_transfer_qty': it.get('total_transfer_quantity') or 0
                    }
                    all_tickets.append(t_item)

                    if resolved_sid not in store_groups:
                        store_groups[resolved_sid] = {
                            'store_id': resolved_sid,
                            'branch_name': b_name,
                            'branch_code': b_code,
                            'tickets': []
                        }
                    store_groups[resolved_sid]['tickets'].append(t_item)
        except Exception as e:
            print(f"[!] Lỗi truy vấn phiếu hậu kiểm kho {wh_key}: {e}", flush=True)

    return {
        'target_date': target_date_str,
        'total_tickets': len(all_tickets),
        'total_stores': len(store_groups),
        'all_tickets': all_tickets,
        'store_groups': store_groups
    }


def render_hk_card_image(store_code, store_name, tickets, output_path=None):
    """
    Vẽ ảnh thẻ thông báo phiếu hậu kiểm CHỈ GỒM BẢNG THÔNG TIN đúng theo Hình 1:
    - Dòng thông tin: Siêu thị: [Mã] Tên ST | Ngày: DD/MM/YYYY
    - Bảng chi tiết: STT | Mã Phiếu Hậu Kiểm | Mã Phiếu Chuyển (PT) | Kho Xuất | Thời Gian Tạo | Trạng Thái
    - Tuyệt đối KHÔNG có banner đen trên đầu và KHÔNG có ghi chú chân trang.
    """
    from PIL import Image, ImageDraw, ImageFont

    def get_font(size, bold=False):
        font_names = [
            "C:\\Windows\\Fonts\\segoeuib.ttf" if bold else "C:\\Windows\\Fonts\\segoeui.ttf",
            "C:\\Windows\\Fonts\\arialbd.ttf" if bold else "C:\\Windows\\Fonts\\arial.ttf",
            "C:\\Windows\\Fonts\\tahomabd.ttf" if bold else "C:\\Windows\\Fonts\\tahoma.ttf",
        ]
        for fn in font_names:
            if os.path.exists(fn):
                try:
                    return ImageFont.truetype(fn, size)
                except Exception:
                    pass
        return ImageFont.load_default()

    row_height = 42
    top_info_height = 45
    table_header_height = 42
    total_rows = max(len(tickets), 1)
    width = 860
    height = top_info_height + table_header_height + (total_rows * row_height) + 15

    img = Image.new('RGB', (width, height), color='#FFFFFF')
    draw = ImageDraw.Draw(img)

    font_info_bold = get_font(14, bold=True)
    font_th = get_font(14, bold=True)
    font_td = get_font(14, bold=False)
    font_td_bold = get_font(14, bold=True)
    font_badge = get_font(12, bold=True)

    # 1. Dòng thông tin Siêu thị & Ngày
    date_str = tickets[0].get('created_date_vn', '') if tickets else ''
    store_disp = f"Siêu thị: [{store_code}] {store_name}"
    draw.text((20, 14), store_disp, font=font_info_bold, fill='#0f172a')
    draw.text((width - 170, 14), f"Ngày: {date_str}", font=font_info_bold, fill='#64748b')

    # Đường phân cách mờ dưới thông tin
    draw.line([(0, top_info_height), (width, top_info_height)], fill='#e2e8f0', width=1)

    # 2. Tiêu đề bảng (Header xanh biển Kingfood)
    y_th = top_info_height + 5
    draw.rectangle([(15, y_th), (width - 15, y_th + table_header_height)], fill='#0284c7')

    col_x = [25, 75, 255, 435, 555, 705]
    headers = ["STT", "Mã Phiếu Hậu Kiểm", "Mã Phiếu Chuyển (PT)", "Kho Xuất", "Thời Gian Tạo", "Trạng Thái"]
    for i, h in enumerate(headers):
        draw.text((col_x[i], y_th + 11), h, font=font_th, fill='#ffffff')

    # 3. Các hàng dữ liệu phiếu
    y_row = y_th + table_header_height
    for idx, t in enumerate(tickets, 1):
        bg_col = '#f8fafc' if idx % 2 == 0 else '#ffffff'
        draw.rectangle([(15, y_row), (width - 15, y_row + row_height)], fill=bg_col)
        draw.line([(15, y_row + row_height), (width - 15, y_row + row_height)], fill='#e2e8f0', width=1)

        draw.text((col_x[0] + 5, y_row + 11), str(idx), font=font_td, fill='#334155')
        draw.text((col_x[1], y_row + 11), t.get('hk_code', ''), font=font_td_bold, fill='#0369a1')
        draw.text((col_x[2], y_row + 11), t.get('pt_code', ''), font=font_td_bold, fill='#b91c1c')
        draw.text((col_x[3], y_row + 11), t.get('source_key', ''), font=font_td, fill='#334155')
        draw.text((col_x[4], y_row + 11), t.get('created_time_str', ''), font=font_td, fill='#475569')

        # Badge Trạng thái
        status_text = "Cần hậu kiểm"
        draw.rectangle([(col_x[5] - 5, y_row + 8), (col_x[5] + 95, y_row + 32)], fill='#fef3c7', outline='#f59e0b', width=1)
        draw.text((col_x[5] + 3, y_row + 10), status_text, font=font_badge, fill='#b45309')

        y_row += row_height

    # Khung viền ngoài bảng
    draw.rectangle([(15, y_th), (width - 15, y_row)], outline='#cbd5e1', width=1)

    if not output_path:
        out_dir = os.path.join(BASE_DIR, 'static', 'generated_docs')
        os.makedirs(out_dir, exist_ok=True)
        date_slug = date_str.replace('/', '') if date_str else datetime.now().strftime('%Y%m%d')
        output_path = os.path.join(out_dir, f"hk_{store_code}_{date_slug}.png")

    os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
    img.save(output_path, quality=95)
    return output_path


def prepare_hk_alerts(target_date_str=None):
    """
    Chuẩn bị danh sách gửi tin batch cảnh báo phiếu hậu kiểm theo kiểu thứ 2:
    - Tin 1 (kèm ảnh): "ST kiểm tra HOÀN THÀNH phiếu hậu kiểm GẤP nhé"
    - Tin 2 (tin riêng biệt): Tag thông tin các quản lý ST (@username / Tên quản lý)
    """
    from telegram_sender import find_krc_store_chat, get_all_store_chats, get_store_manager_tag_line

    scan_res = fetch_pending_double_checks(target_date_str)
    all_stores = get_all_store_chats()
    store_groups = scan_res['store_groups']

    batch_list = []
    out_dir = os.path.join(BASE_DIR, 'static', 'generated_docs')
    os.makedirs(out_dir, exist_ok=True)

    for sid, sdata in store_groups.items():
        tickets = sdata['tickets']
        s_name = sdata['branch_name'] or sid
        
        # Tìm group Telegram
        target_chat = find_krc_store_chat(sid, all_stores)
        if not target_chat and sdata['branch_code']:
            target_chat = find_krc_store_chat(sdata['branch_code'], all_stores)
        if not target_chat and sdata['branch_name']:
            target_chat = find_krc_store_chat(sdata['branch_name'], all_stores)

        chat_id = target_chat['chat_id'] if target_chat else None
        chat_title = target_chat['chat_title'] if target_chat else f"KRC - {s_name}"

        # 1. Caption tin nhắn thứ nhất (gửi kèm hình ảnh)
        caption = "ST kiểm tra HOÀN THÀNH phiếu hậu kiểm GẤP nhé"

        # 2. Tin nhắn thứ hai: Thông tin tag quản lý riêng biệt
        tag_line = "@sm @tc @gsm"
        if chat_id:
            try:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                tag_line = loop.run_until_complete(get_store_manager_tag_line(chat_id))
                loop.close()
            except Exception:
                pass

        full_preview = f"{caption}\n\n{tag_line}"

        # Render ảnh bảng chi tiết (chỉ gồm bảng thông tin)
        date_slug = scan_res['target_date'].replace('/', '')
        img_filename = f"hk_{sid}_{date_slug}.png"
        img_abs_path = os.path.join(out_dir, img_filename)
        try:
            render_hk_card_image(sid, s_name, tickets, img_abs_path)
            img_rel_url = f"/static/generated_docs/{img_filename}"
        except Exception as err:
            print(f"[!] Lỗi render ảnh thẻ HK {sid}: {err}")
            img_abs_path = None
            img_rel_url = None

        batch_list.append({
            'store_key': sid,
            'store_name': s_name,
            'chat_id': chat_id,
            'chat_title': chat_title,
            'caption': caption,
            'tag_line': tag_line,
            'message_text': full_preview,
            'image_path': img_abs_path,
            'image_url': img_rel_url,
            'count_items': len(tickets),
            'tickets': tickets
        })

    return {
        'success': True,
        'target_date': scan_res['target_date'],
        'total_tickets': scan_res['total_tickets'],
        'total_stores': len(batch_list),
        'batch_list': batch_list
    }


async def send_hk_batch_telethon(alerts):
    """
    Gửi tin nhắn theo Kiểu thứ 2 theo hình:
    - Tin 1: Gửi hình ảnh bảng phiếu + Chú thích "ST kiểm tra HOÀN THÀNH phiếu hậu kiểm GẤP nhé"
    - Tin 2: Gửi tin nhắn riêng biệt ngay sau đó tag quản lý ST (@username / Tên quản lý)
    """
    from telethon import TelegramClient, errors

    if not alerts:
        return {"success": False, "sent_count": 0, "error": "Danh sách gửi trống"}

    client = TelegramClient(SESSION_NAME, API_ID, API_HASH)
    await client.connect()

    if not await client.is_user_authorized():
        await client.disconnect()
        return {"success": False, "sent_count": 0, "error": "Tài khoản Telegram chưa được ủy quyền"}

    batch_id = datetime.now().strftime('HK_%Y%m%d_%H%M%S')
    success_count = 0
    failed = []
    sent_records = []

    for a in alerts:
        cid = a.get('chat_id')
        caption = a.get('caption') or "ST kiểm tra HOÀN THÀNH phiếu hậu kiểm GẤP nhé"
        tag_line = (a.get('tag_line') or '').strip()
        img_path = a.get('image_path')
        c_title = a.get('chat_title') or f"ST_{cid}"

        if not cid:
            failed.append({"chat_id": None, "store": a.get('store_name'), "error": "Chưa tìm thấy group Telegram"})
            continue

        target = int(cid)
        try:
            # Với các group DC dạng Forum: tự động tìm kênh/topic Rau / Rau Củ / KRC để gửi vào
            from telegram_sender import get_forum_rau_topic_id
            topic_id = await get_forum_rau_topic_id(client, target)

            # 1. Gửi Tin 1: Hình ảnh bảng phiếu kèm caption (đẩy vào topic nếu có)
            if img_path and os.path.exists(img_path):
                sent_msg1 = await client.send_file(target, img_path, caption=caption, reply_to=topic_id)
            else:
                sent_msg1 = await client.send_message(target, caption, reply_to=topic_id)

            sent_records.append((batch_id, target, c_title, sent_msg1.id, caption))

            # 2. Gửi Tin 2: Tin riêng biệt tag quản lý (Kiểu thứ 2)
            if tag_line:
                await asyncio.sleep(0.6)
                sent_msg2 = await client.send_message(target, tag_line, reply_to=topic_id)
                sent_records.append((batch_id, target, c_title, sent_msg2.id, tag_line))

            success_count += 1
            await asyncio.sleep(round(random.uniform(2.0, 3.5), 2))
        except errors.FloodWaitError as e:
            print(f"[!] FloodWait: Đợi {e.seconds}s...")
            await asyncio.sleep(e.seconds + 1)
            try:
                from telegram_sender import get_forum_rau_topic_id
                topic_id = await get_forum_rau_topic_id(client, target)

                if img_path and os.path.exists(img_path):
                    sent_msg1 = await client.send_file(target, img_path, caption=caption, reply_to=topic_id)
                else:
                    sent_msg1 = await client.send_message(target, caption, reply_to=topic_id)
                sent_records.append((batch_id, target, c_title, sent_msg1.id, caption))

                if tag_line:
                    await asyncio.sleep(0.6)
                    sent_msg2 = await client.send_message(target, tag_line, reply_to=topic_id)
                    sent_records.append((batch_id, target, c_title, sent_msg2.id, tag_line))

                success_count += 1
            except Exception as e2:
                failed.append({"chat_id": cid, "error": str(e2)})
        except Exception as e:
            failed.append({"chat_id": cid, "error": str(e)})

    await client.disconnect()

    # Ghi lại lịch sử gửi tin
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
        except Exception as err:
            print(f"[!] Lỗi ghi sent_broadcast_history: {err}")

    return {
        "success": True,
        "batch_id": batch_id,
        "sent_count": success_count,
        "failed_count": len(failed),
        "failed": failed
    }


def execute_auto_daily_hk_reminder(target_date_str=None):
    """
    Hàm thực thi tự động lúc 09:00 sáng:
    Quét phiếu treo -> Tạo ảnh -> Gửi Telegram cho từng ST -> Báo cáo
    """
    import asyncio
    print(f"[*] [09:00 AM] Bắt đầu tự động quét phiếu Hậu kiểm KRC & KRCBT...", flush=True)
    prep = prepare_hk_alerts(target_date_str)
    batch_list = prep.get('batch_list', [])

    if not batch_list:
        print(f"[*] [09:00 AM] Không có Siêu thị nào có phiếu Hậu kiểm cần hoàn thành ngày {prep.get('target_date')}.", flush=True)
        return {
            "success": True,
            "message": "Không có phiếu hậu kiểm nào đang treo",
            "total_stores": 0
        }

    print(f"[*] [09:00 AM] Phát hiện {len(batch_list)} Siêu thị có {prep.get('total_tickets')} phiếu cần nhắc. Bắt đầu gửi...", flush=True)
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    res = loop.run_until_complete(send_hk_batch_telethon(batch_list))
    loop.close()

    print(f"[*] [09:00 AM] Hoàn tất gửi nhắc nhở: Đã gửi {res.get('sent_count')}/{len(batch_list)} Siêu thị.", flush=True)
    return res
