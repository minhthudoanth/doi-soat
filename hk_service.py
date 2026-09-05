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

                    c_lines = it.get('container_lines', [])
                    add_in = sum(1 for c in c_lines for p in c.get('product_lines', []) if p.get('is_add_in'))
                    total_sku = it.get('total_sku') or it.get('sku') or 0
                    sku_display = f"{add_in}/{total_sku}" if total_sku else str(add_in)

                    t_qty = it.get('total_transfer_quantity') or 0
                    r_qty = it.get('total_received_quantity') or 0
                    qty_display = f"{int(r_qty):,}/{int(t_qty):,}"

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
                        'total_sku': total_sku,
                        'add_in_sku': add_in,
                        'sku_display': sku_display,
                        'total_transfer_qty': t_qty,
                        'total_received_qty': r_qty,
                        'qty_display': qty_display
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
    Vẽ ảnh bảng thông báo phiếu hậu kiểm CHUẨN 100% THEO HÌNH ẢNH YÊU CẦU (Hình 1):
    - Thanh điều hướng tối trên cùng (#1e293b)
    - Tiêu đề các cột: STT | Mã phiếu | Phiếu chuyển | Nơi chuyển | Nơi nhận | Trạng thái | SKU | Số lượng
    - Dòng dữ liệu:
      + STT: 1, 2...
      + Mã phiếu: Xanh dương (link)
      + Phiếu chuyển: Xanh dương (link)
      + Nơi chuyển: KRC / KRCBT
      + Nơi nhận: Tên đầy đủ chi nhánh ST
      + Trạng thái: Badge "Cần hậu kiểm" (nền vàng cam nhạt, chữ cam)
      + SKU: add_in/total_sku (ví dụ: 1/212)
      + Số lượng: tổng nhận/tổng chuyển (ví dụ: 1,996/1,996)
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

    col_widths = [45, 115, 115, 95, 280, 120, 75, 115]
    total_table_width = sum(col_widths)
    padding_x = 15
    image_width = total_table_width + padding_x * 2 # 990px

    top_bar_height = 14
    header_height = 42
    row_height = 48
    num_rows = max(len(tickets), 1)
    image_height = top_bar_height + header_height + (num_rows * row_height) + 12

    img = Image.new('RGB', (image_width, image_height), color='#ffffff')
    draw = ImageDraw.Draw(img)

    # 1. Thanh bar tối trên cùng
    draw.rectangle([0, 0, image_width, top_bar_height], fill='#1e293b')

    font_header = get_font(13, bold=False)
    font_cell = get_font(13, bold=False)
    font_link = get_font(13, bold=False)
    font_badge = get_font(12, bold=False)

    headers = ["STT", "Mã phiếu", "Phiếu chuyển", "Nơi chuyển", "Nơi nhận", "Trạng thái", "SKU", "Số lượng"]
    
    # 2. Tiêu đề bảng
    y_hdr = top_bar_height
    curr_x = padding_x
    for i, h in enumerate(headers):
        w = col_widths[i]
        draw.text((curr_x + 6, y_hdr + 12), h, fill='#595959', font=font_header)
        curr_x += w

    draw.line([(padding_x, y_hdr + header_height), (image_width - padding_x, y_hdr + header_height)], fill='#f0f0f0', width=1)

    # 3. Dòng dữ liệu
    curr_y = y_hdr + header_height
    for idx, t in enumerate(tickets):
        row_bg = '#ffffff' if idx % 2 == 0 else '#fafafa'
        draw.rectangle([padding_x, curr_y, image_width - padding_x, curr_y + row_height], fill=row_bg)

        curr_x = padding_x

        # STT
        draw.text((curr_x + 6, curr_y + 15), str(idx + 1), fill='#262626', font=font_cell)
        curr_x += col_widths[0]

        # Mã phiếu (blue link)
        draw.text((curr_x + 6, curr_y + 15), t.get('hk_code', '---'), fill='#1890ff', font=font_link)
        curr_x += col_widths[1]

        # Phiếu chuyển (blue link)
        draw.text((curr_x + 6, curr_y + 15), t.get('pt_code', '---'), fill='#1890ff', font=font_link)
        curr_x += col_widths[2]

        # Nơi chuyển
        draw.text((curr_x + 6, curr_y + 15), t.get('source_key', 'KRC'), fill='#262626', font=font_cell)
        curr_x += col_widths[3]

        # Nơi nhận
        bname = t.get('branch_name', store_name)
        if len(bname) > 36:
            bname = bname[:34] + '...'
        draw.text((curr_x + 6, curr_y + 15), bname, fill='#262626', font=font_cell)
        curr_x += col_widths[4]

        # Trạng thái (Badge: Cần hậu kiểm)
        badge_text = "Cần hậu kiểm"
        bx = curr_x + 6
        by = curr_y + 11
        bw = 88
        bh = 25
        draw.rounded_rectangle([bx, by, bx + bw, by + bh], radius=4, fill='#fff7e6', outline='#ffd591', width=1)
        draw.text((bx + 10, by + 4), badge_text, fill='#fa8c16', font=font_badge)
        curr_x += col_widths[5]

        # SKU
        sku_val = t.get('sku_display') or f"0/{t.get('total_sku', 0)}"
        draw.text((curr_x + 6, curr_y + 15), sku_val, fill='#262626', font=font_cell)
        curr_x += col_widths[6]

        # Số lượng
        qty_val = t.get('qty_display') or "0/0"
        draw.text((curr_x + 6, curr_y + 15), qty_val, fill='#262626', font=font_cell)
        curr_x += col_widths[7]

        draw.line([(padding_x, curr_y + row_height), (image_width - padding_x, curr_y + row_height)], fill='#f0f0f0', width=1)
        curr_y += row_height

    if not output_path:
        out_dir = os.path.join(BASE_DIR, 'static', 'generated_docs')
        os.makedirs(out_dir, exist_ok=True)
        date_str = tickets[0].get('created_date_vn', '') if tickets else ''
        date_slug = date_str.replace('/', '') if date_str else datetime.now().strftime('%Y%m%d')
        output_path = os.path.join(out_dir, f"hk_{store_code}_{date_slug}.png")

    os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
    img.save(output_path, quality=95)
    return output_path


def prepare_hk_alerts(target_date_str=None):
    """
    Chuẩn bị danh sách gửi tin cảnh báo phiếu hậu kiểm theo đúng chuẩn Hình 2:
    - Dòng 1: RAU (hoặc BÁNH TƯƠI)
    - Dòng 2: DD.MM (ví dụ: 05.09)
    - Dòng 3: Siêu thị kiểm tra HOÀN THÀNH phiếu HẬU KIỂM HÀNG RAU gấp nhé team
    - Dòng 4: Tag quản lý ST (ưu tiên SM -> SL/TC/GSM; tuyệt đối không tag Hà Trang Smartlog)
    - Kèm hình ảnh bảng phiếu chi tiết (theo Hình 1)
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

        # Xác định ngành hàng: RAU hoặc BÁNH TƯƠI
        sources = set(t.get('source_key') for t in tickets)
        if sources == {'KRCBT'}:
            dept_title = "BÁNH TƯƠI"
            dept_name = "HÀNG BÁNH TƯƠI"
        elif 'KRCBT' in sources and 'KRC' in sources:
            dept_title = "RAU & BÁNH TƯƠI"
            dept_name = "HÀNG RAU & BÁNH TƯƠI"
        else:
            dept_title = "RAU"
            dept_name = "HÀNG RAU"

        # Định dạng ngày DD.MM theo đúng hình 2 (ví dụ 05.09)
        date_obj = tickets[0].get('created_dt_vn') if tickets and tickets[0].get('created_dt_vn') else datetime.now(VN_TZ)
        date_dot = date_obj.strftime('%d.%m')

        # Cú pháp đúng chuẩn Hình 2
        caption_intro = f"{dept_title}\n{date_dot}\nSiêu thị kiểm tra HOÀN THÀNH phiếu HẬU KIỂM {dept_name} gấp nhé team"

        # Tag quản lý riêng biệt
        tag_line = "@sm @tc @gsm"
        if chat_id:
            try:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                tag_line = loop.run_until_complete(get_store_manager_tag_line(chat_id))
                loop.close()
            except Exception:
                pass

        full_preview = f"{caption_intro}\n{tag_line}" if tag_line else caption_intro

        # Render ảnh bảng chi tiết (chuẩn theo Hình 1)
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
            'caption': caption_intro,
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
    Gửi tin nhắn theo đúng chuẩn Hình 2:
    - Ảnh bảng phiếu chi tiết (Hình 1)
    - Kèm nội dung:
      RAU
      DD.MM
      Siêu thị kiểm tra HOÀN THÀNH phiếu HẬU KIỂM HÀNG RAU gấp nhé team
      [Tag Quản lý ST: SM -> SL/TC/GSM, không tag Hà Trang Smartlog]
    - Tự động đẩy vào Topic RAU nếu group là DC Forum
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
        caption = a.get('caption') or "Siêu thị kiểm tra HOÀN THÀNH phiếu HẬU KIỂM HÀNG RAU gấp nhé team"
        tag_line = (a.get('tag_line') or '').strip()
        full_caption = f"{caption}\n{tag_line}" if tag_line else caption
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

            if img_path and os.path.exists(img_path):
                if len(full_caption) <= 1024:
                    sent_msg = await client.send_file(target, img_path, caption=full_caption, reply_to=topic_id)
                    sent_records.append((batch_id, target, c_title, sent_msg.id, full_caption))
                else:
                    sent_msg1 = await client.send_file(target, img_path, caption=caption, reply_to=topic_id)
                    sent_records.append((batch_id, target, c_title, sent_msg1.id, caption))
                    if tag_line:
                        await asyncio.sleep(0.6)
                        sent_msg2 = await client.send_message(target, tag_line, reply_to=topic_id)
                        sent_records.append((batch_id, target, c_title, sent_msg2.id, tag_line))
            else:
                sent_msg = await client.send_message(target, full_caption, reply_to=topic_id)
                sent_records.append((batch_id, target, c_title, sent_msg.id, full_caption))

            success_count += 1
            await asyncio.sleep(round(random.uniform(2.0, 3.5), 2))
        except errors.FloodWaitError as e:
            print(f"[!] FloodWait: Đợi {e.seconds}s...")
            await asyncio.sleep(e.seconds + 1)
            try:
                from telegram_sender import get_forum_rau_topic_id
                topic_id = await get_forum_rau_topic_id(client, target)

                if img_path and os.path.exists(img_path):
                    if len(full_caption) <= 1024:
                        sent_msg = await client.send_file(target, img_path, caption=full_caption, reply_to=topic_id)
                        sent_records.append((batch_id, target, c_title, sent_msg.id, full_caption))
                    else:
                        sent_msg1 = await client.send_file(target, img_path, caption=caption, reply_to=topic_id)
                        sent_records.append((batch_id, target, c_title, sent_msg1.id, caption))
                        if tag_line:
                            await asyncio.sleep(0.6)
                            sent_msg2 = await client.send_message(target, tag_line, reply_to=topic_id)
                            sent_records.append((batch_id, target, c_title, sent_msg2.id, tag_line))
                else:
                    sent_msg = await client.send_message(target, full_caption, reply_to=topic_id)
                    sent_records.append((batch_id, target, c_title, sent_msg.id, full_caption))

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
