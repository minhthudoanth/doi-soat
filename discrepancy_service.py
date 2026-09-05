# -*- coding: utf-8 -*-
"""
Module: discrepancy_service.py
Dịch vụ Quản lý & Gửi Thông Báo Lệch Kho (DC Giao Thiếu):
1. Quét dữ liệu từ bảng sheet_audit_records theo Ngày đổ dữ liệu.
2. Lọc danh sách các Siêu Thị có lỗi "DC giao thiếu".
3. Kết xuất ảnh bảng thống kê màu cam chuẩn theo Hình 1 (PIL).
4. Chuẩn bị nội dung tin nhắn Telegram chuẩn format.
5. Gửi tin nhắn và hình ảnh tự động qua Telethon vào đúng nhóm chat của ST.
"""

import os
import sys
import re
import io
import time
import random
import sqlite3
from datetime import datetime

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from config import DB_PATH, API_ID, API_HASH, SESSION_NAME
from telegram_sender import (
    find_krc_store_chat,
    get_all_store_chats,
    get_store_manager_tag_line,
    get_forum_rau_topic_id
)

EXPORT_DIR = os.path.join(BASE_DIR, 'static', 'exports', 'chenh_lech')
os.makedirs(EXPORT_DIR, exist_ok=True)


def get_discrepancy_dates():
    """
    Lấy danh sách tất cả các ngày có dữ liệu DC giao thiếu từ CSDL,
    sắp xếp từ ngày mới nhất trở về trước.
    """
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("""
        SELECT DISTINCT transfer_date 
        FROM sheet_audit_records 
        WHERE error_type = 'DC giao thiếu' AND transfer_date IS NOT NULL AND transfer_date != ''
        ORDER BY id DESC
    """)
    raw_dates = [r[0].strip() for r in c.fetchall() if r[0]]
    conn.close()

    # Sắp xếp theo ngày thực tế (nếu định dạng MM/DD/YYYY hoặc DD/MM/YYYY)
    def parse_dt(d_str):
        for fmt in ('%m/%d/%Y', '%d/%m/%Y', '%Y-%m-%d'):
            try:
                return datetime.strptime(d_str, fmt)
            except Exception:
                pass
        return datetime.min

    sorted_dates = sorted(list(set(raw_dates)), key=parse_dt, reverse=True)
    return sorted_dates


def format_date_to_d_format(date_str):
    """
    Chuyển ngày MM/DD/YYYY hoặc DD/MM/YYYY thành định dạng 'DD.MM' (ví dụ 04.09).
    """
    if not date_str:
        return datetime.now().strftime('%d.%m')
    date_clean = date_str.strip()
    
    # Thử parse
    for fmt in ('%m/%d/%Y', '%d/%m/%Y', '%Y-%m-%d'):
        try:
            dt = datetime.strptime(date_clean, fmt)
            return dt.strftime('%d.%m')
        except Exception:
            pass

    parts = re.split(r'[/.-]', date_clean)
    if len(parts) >= 2:
        # Trường hợp Google sheet format MM/DD/YYYY: part 0 là MM, part 1 là DD
        if int(parts[0]) <= 12 and int(parts[1]) <= 31:
            return f"{int(parts[1]):02d}.{int(parts[0]):02d}"
        return f"{int(parts[0]):02d}.{int(parts[1]):02d}"
    return date_clean


def generate_discrepancy_table_image(store_id, items, date_str="", force=False):
    """
    Vẽ ảnh bảng danh sách mã hàng thiếu theo đúng chuẩn Hình 1:
    - Thanh Header màu cam nổi bật (#F26522), chữ trắng in đậm:
      ID ST | Mã hàng | Tên Hàng | ĐVT | SL chuyển
    - Các dòng chi tiết xen kẽ nền trắng (#FFFFFF) và xám nhạt (#FAFAFA)
    - Định dạng số lượng: ví dụ 10,00 hoặc 5,00
    - Lưu file vào static/exports/chenh_lech/
    """
    safe_date = re.sub(r'[^\w]', '_', date_str) if date_str else 'today'
    filename = f"dc_thieu_{store_id}_{safe_date}.png"
    filepath = os.path.join(EXPORT_DIR, filename)
    rel_url = f"/static/exports/chenh_lech/{filename}"

    if not force and os.path.exists(filepath):
        return filepath, rel_url

    from PIL import Image, ImageDraw, ImageFont

    def get_font(size, bold=False):
        font_paths = [
            "C:\\Windows\\Fonts\\segoeuib.ttf" if bold else "C:\\Windows\\Fonts\\segoeui.ttf",
            "C:\\Windows\\Fonts\\arialbd.ttf" if bold else "C:\\Windows\\Fonts\\arial.ttf",
            "C:\\Windows\\Fonts\\tahomabd.ttf" if bold else "C:\\Windows\\Fonts\\tahoma.ttf",
        ]
        for fp in font_paths:
            if os.path.exists(fp):
                try:
                    return ImageFont.truetype(fp, size)
                except Exception:
                    pass
        return ImageFont.load_default()

    # Cấu hình kích thước cột chuẩn: ID ST (75px) | Mã hàng (145px) | Tên Hàng (390px) | ĐVT (85px) | SL chuyển (105px)
    col_widths = [75, 145, 390, 85, 105]
    total_table_width = sum(col_widths) # 800px
    padding_x = 16
    image_width = total_table_width + padding_x * 2 # 832px

    header_height = 46
    row_height = 44
    num_rows = max(len(items), 1)
    image_height = header_height + (num_rows * row_height) + 16

    img = Image.new('RGB', (image_width, image_height), color='#ffffff')
    draw = ImageDraw.Draw(img)

    font_header = get_font(14, bold=True)
    font_cell = get_font(13, bold=False)
    font_cell_bold = get_font(13, bold=True)

    # 1. Vẽ thanh Header màu cam chuẩn (#F26522)
    header_color = '#F26522'
    draw.rectangle([padding_x, 8, image_width - padding_x, 8 + header_height], fill=header_color)

    headers = ["ID ST", "Mã hàng", "Tên Hàng", "ĐVT", "SL chuyển"]

    curr_x = padding_x
    for i, h in enumerate(headers):
        w = col_widths[i]
        # Căn giữa ĐVT và SL chuyển, căn trái cho các cột còn lại
        if h == "ĐVT":
            bbox = font_header.getbbox(h)
            tw = bbox[2] - bbox[0]
            tx = curr_x + (w - tw) // 2
        elif h == "SL chuyển":
            bbox = font_header.getbbox(h)
            tw = bbox[2] - bbox[0]
            tx = curr_x + w - tw - 16
        else:
            tx = curr_x + 14
        
        draw.text((tx, 8 + 14), h, fill='#ffffff', font=font_header)
        curr_x += w

    # 2. Vẽ các dòng dữ liệu
    curr_y = 8 + header_height
    for idx, it in enumerate(items):
        row_bg = '#ffffff' if idx % 2 == 0 else '#fafafa'
        draw.rectangle([padding_x, curr_y, image_width - padding_x, curr_y + row_height], fill=row_bg)

        # Viền mờ ngăn cách từng dòng
        draw.line([(padding_x, curr_y + row_height), (image_width - padding_x, curr_y + row_height)], fill='#eeeeee', width=1)

        curr_x = padding_x

        # 1. ID ST
        st_id_val = str(it.get('store_id') or store_id or '').strip()
        draw.text((curr_x + 14, curr_y + 13), st_id_val, fill='#262626', font=font_cell)
        curr_x += col_widths[0]

        # 2. Mã hàng
        sku_val = str(it.get('sku_code') or '').strip()
        draw.text((curr_x + 14, curr_y + 13), sku_val, fill='#262626', font=font_cell)
        curr_x += col_widths[1]

        # 3. Tên Hàng (cắt ngắn nếu quá dài để không bị tràn)
        item_name = str(it.get('item_name') or '').strip()
        if len(item_name) > 42:
            item_name = item_name[:39] + '...'
        draw.text((curr_x + 14, curr_y + 13), item_name, fill='#171717', font=font_cell)
        curr_x += col_widths[2]

        # 4. ĐVT
        uom_val = str(it.get('uom') or '').strip().upper()
        bbox_uom = font_cell.getbbox(uom_val)
        tw_uom = bbox_uom[2] - bbox_uom[0] if uom_val else 0
        tx_uom = curr_x + (col_widths[3] - tw_uom) // 2
        draw.text((tx_uom, curr_y + 13), uom_val, fill='#595959', font=font_cell)
        curr_x += col_widths[3]

        # 5. SL chuyển (định dạng 10,00 hoặc 5,00)
        qty_val = it.get('qty_transfer')
        try:
            qty_num = float(qty_val) if qty_val is not None else 0.0
            qty_str = f"{qty_num:,.2f}".replace('.', ',')
        except Exception:
            qty_str = str(qty_val or '0,00')
        bbox_qty = font_cell_bold.getbbox(qty_str)
        tw_qty = bbox_qty[2] - bbox_qty[0]
        tx_qty = curr_x + col_widths[4] - tw_qty - 16
        draw.text((tx_qty, curr_y + 13), qty_str, fill='#262626', font=font_cell_bold)
        curr_x += col_widths[4]

        curr_y += row_height

    # Viền bao quanh toàn bảng
    draw.rectangle([padding_x, 8, image_width - padding_x, curr_y], outline='#e8e8e8', width=1)

    # Lưu ảnh ra đĩa
    img.save(filepath, format='PNG', optimize=True)
    return filepath, rel_url


def format_discrepancy_message_template(date_display):
    """
    Sinh nội dung tin nhắn văn bản đúng 100% theo mẫu yêu cầu:
    RAU CỦ QUẢ
    [ngày D]
    ST kiểm tra lại giúp Thư sáng nay có nhập sót SL các mã hàng trên do đếm sót/hàng không đạt chất lượng ST tự trừ thực nhận mà không nhập bên hàng hư hỏng

    - Với mã hàng nhận thiếu item (nếu có chụp hình QUÊN up trong phiếu): cung cấp hình ảnh SL thực nhận 

    NOTE:
     Với hàng dư ST add trực tiếp trong phiếu HẬU KIỂM
    """
    return f"""RAU CỦ QUẢ
{date_display}
ST kiểm tra lại giúp Thư sáng nay có nhập sót SL các mã hàng trên do đếm sót/hàng không đạt chất lượng ST tự trừ thực nhận mà không nhập bên hàng hư hỏng

- Với mã hàng nhận thiếu item (nếu có chụp hình QUÊN up trong phiếu): cung cấp hình ảnh SL thực nhận 

NOTE:
 Với hàng dư ST add trực tiếp trong phiếu HẬU KIỂM"""


def get_discrepancy_data_by_date(date_str=None):
    """
    Trích xuất toàn bộ các ca 'DC giao thiếu' theo ngày,
    nhóm theo từng Siêu thị, tạo ảnh bảng và định dạng tin nhắn xem trước.
    """
    all_dates = get_discrepancy_dates()
    if not date_str:
        date_str = all_dates[0] if all_dates else datetime.now().strftime('%m/%d/%Y')

    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()

    c.execute("""
        SELECT id, transfer_date, store_id, branch_name, sku_code, item_name, uom, 
               qty_transfer, qty_receive, qty_diff, pt_transfer, box_code, to_code
        FROM sheet_audit_records
        WHERE error_type = 'DC giao thiếu'
          AND (transfer_date = ? OR transfer_date LIKE ?)
        ORDER BY store_id ASC, id ASC
    """, (date_str, f"%{date_str}%"))
    rows = c.fetchall()
    conn.close()

    date_display = format_date_to_d_format(date_str)
    all_stores = get_all_store_chats()

    # Tải toàn bộ cache tag từ store_tag_cache
    tag_cache_map = {}
    try:
        conn_tag = sqlite3.connect(DB_PATH)
        c_t = conn_tag.cursor()
        c_t.execute("CREATE TABLE IF NOT EXISTS store_tag_cache (chat_id TEXT PRIMARY KEY, tag_line TEXT, updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)")
        c_t.execute("SELECT chat_id, tag_line FROM store_tag_cache WHERE tag_line IS NOT NULL AND tag_line != '' AND tag_line != '@sm @tc @gsm'")
        for r in c_t.fetchall():
            tag_cache_map[str(r[0])] = r[1]
        conn_tag.close()
    except Exception:
        pass

    # Nhóm theo store_id
    grouped = {}
    for r in rows:
        sid = r['store_id'] or 'UNKNOWN'
        if sid not in grouped:
            grouped[sid] = {
                'store_id': sid,
                'branch_name': r['branch_name'] or sid,
                'items': []
            }
        grouped[sid]['items'].append(dict(r))

    batch_list = []
    total_missing_items = 0
    total_qty_missing = 0.0

    msg_template = format_discrepancy_message_template(date_display)

    for sid, sdata in grouped.items():
        items = sdata['items']
        total_missing_items += len(items)

        # Tính tổng SL thiếu của ST
        store_qty_missing = 0.0
        for it in items:
            try:
                store_qty_missing += float(it.get('qty_diff') or it.get('qty_transfer') or 0.0)
            except Exception:
                pass
        total_qty_missing += store_qty_missing

        # Tìm group Telegram
        target_chat = find_krc_store_chat(sid, all_stores)
        if not target_chat:
            target_chat = find_krc_store_chat(sdata['branch_name'], all_stores)

        chat_id = target_chat['chat_id'] if target_chat else None
        chat_title = target_chat['chat_title'] if target_chat else f"[Chưa kết nối KRC/DC] {sdata['branch_name']}"

        # Sinh ảnh bảng màu cam chuẩn theo Hình 1
        img_abs_path, img_rel_url = generate_discrepancy_table_image(sid, items, date_str)

        # Lấy dòng tag quản lý cửa hàng (ưu tiên từ cache CSDL)
        tag_line = tag_cache_map.get(str(chat_id)) if chat_id else None
        if not tag_line:
            tag_line = "@sm @tc @gsm"

        full_msg_preview = f"{msg_template}\n\n{tag_line}" if tag_line else msg_template

        batch_list.append({
            'store_id': sid,
            'store_name': sdata['branch_name'],
            'chat_id': chat_id,
            'chat_title': chat_title,
            'is_chat_connected': bool(chat_id),
            'items': items,
            'count_items': len(items),
            'total_qty_missing': round(store_qty_missing, 2),
            'image_path': img_abs_path,
            'image_url': img_rel_url,
            'message_text': full_msg_preview,
            'raw_message': msg_template,
            'tag_line': tag_line
        })

    return {
        'success': True,
        'selected_date': date_str,
        'date_display': date_display,
        'available_dates': all_dates,
        'total_stores': len(batch_list),
        'total_missing_items': total_missing_items,
        'total_qty_missing': round(total_qty_missing, 2),
        'batch_list': batch_list
    }


async def send_discrepancy_telethon(alerts):
    """
    Gửi tin nhắn thông báo DC giao thiếu đến các group Telegram của Siêu Thị:
    - Ảnh bảng danh sách mã thiếu (Hình 1 màu cam)
    - Kèm nội dung thông báo chuẩn mẫu
    - Tự động đẩy vào Topic RAU nếu group là Forum
    - Ghi nhận lịch sử gửi vào sent_broadcast_history
    """
    from telethon import TelegramClient, errors

    if not alerts:
        return {"success": False, "sent_count": 0, "error": "Danh sách gửi trống"}

    client = TelegramClient(SESSION_NAME, API_ID, API_HASH)
    await client.connect()

    if not await client.is_user_authorized():
        await client.disconnect()
        return {"success": False, "sent_count": 0, "error": "Tài khoản Telegram chưa được ủy quyền"}

    batch_id = datetime.now().strftime('DC_THIEU_%Y%m%d_%H%M%S')
    from progress_tracker import reset_broadcast_progress, update_broadcast_progress, finish_broadcast_progress
    reset_broadcast_progress(len(alerts), batch_id)

    success_count = 0
    failed = []
    sent_records = []
    adaptive_delay = 0.0

    for idx, a in enumerate(alerts):
        cid = a.get('chat_id')
        msg_text = a.get('message_text') or ""
        img_path = a.get('image_path')
        c_title = a.get('chat_title') or f"ST_{cid}"
        sid = a.get('store_id') or "ST"

        if not cid:
            failed.append({"store_id": sid, "store_name": a.get('store_name'), "error": "Chưa tìm thấy nhóm Telegram của ST này"})
            continue

        target = int(cid)
        try:
            now_t = datetime.now().strftime('%H:%M:%S')
            update_broadcast_progress(idx, len(alerts), f"[{sid}] {c_title}", f"Đang gửi {idx+1}/{len(alerts)}: [{sid}] {c_title}...", success_count, len(failed))

            # Topic forum (nếu có)
            topic_id = await get_forum_rau_topic_id(client, target)

            # Lấy tag quản lý real-time nếu có kết nối
            try:
                tag_str = await get_store_manager_tag_line(target, client=client)
                if tag_str and tag_str != "@sm @tc @gsm":
                    # Thay thế tag mặc định bằng tag thực tế
                    if "@sm @tc @gsm" in msg_text:
                        msg_text = msg_text.replace("@sm @tc @gsm", tag_str)
            except Exception as e:
                print(f"[!] Lỗi lấy tag quản lý cho {sid} ({target}): {e}")

            # 1. Giả lập hành vi người thật: gửi action Typing / Uploading Photo trước khi gửi
            try:
                from telethon.tl import types, functions
                action = types.SendMessageUploadPhotoAction() if (img_path and os.path.exists(img_path)) else types.SendMessageTypingAction()
                await client(functions.messages.SetTypingRequest(peer=target, action=action))
                await asyncio.sleep(round(random.uniform(0.6, 1.2), 2))
            except Exception:
                pass

            if img_path and os.path.exists(img_path):
                if len(msg_text) <= 1024:
                    # Gửi ảnh kèm caption là toàn bộ nội dung tin nhắn
                    sent_msg = await client.send_file(target, img_path, caption=msg_text, reply_to=topic_id)
                    sent_records.append((batch_id, target, c_title, sent_msg.id, msg_text))
                else:
                    # Gửi ảnh trước, tin nhắn ngay sau
                    sent_msg1 = await client.send_file(target, img_path, reply_to=topic_id)
                    sent_records.append((batch_id, target, c_title, sent_msg1.id, "[Ảnh danh sách DC giao thiếu]"))
                    await asyncio.sleep(0.6)
                    sent_msg2 = await client.send_message(target, msg_text, reply_to=topic_id)
                    sent_records.append((batch_id, target, c_title, sent_msg2.id, msg_text))
            else:
                sent_msg = await client.send_message(target, msg_text, reply_to=topic_id)
                sent_records.append((batch_id, target, c_title, sent_msg.id, msg_text))

            success_count += 1
            now_t = datetime.now().strftime('%H:%M:%S')
            update_broadcast_progress(idx + 1, len(alerts), f"[{sid}] {c_title}", f"Đã gửi {idx+1}/{len(alerts)} ST: [{sid}] {c_title}", success_count, len(failed), log_entry=f"[{now_t}] ✅ [{sid}] {c_title} - Gửi thành công")

            # 3. Smart Jitter Delay (ngẫu nhiên 2.5s - 4.2s + độ trễ thích ứng)
            delay_sec = round(random.uniform(2.5, 4.2) + adaptive_delay, 2)
            await asyncio.sleep(delay_sec)

            # 2. Cơ chế nghỉ giải lao (Batch Chunking & Smart Cooldown): cứ 15 ST nghỉ 12s - 18s
            if (idx + 1) % 15 == 0 and (idx + 1) < len(alerts):
                cooldown = round(random.uniform(12.0, 18.0), 1)
                now_t = datetime.now().strftime('%H:%M:%S')
                update_broadcast_progress(idx + 1, len(alerts), f"[{sid}] {c_title}", f"⏳ [Anti-Spam] Nghỉ giải lao {cooldown}s sau {idx+1} ST...", success_count, len(failed), log_entry=f"[{now_t}] ☕ Nghỉ giải lao chống SpamBot {cooldown}s...")
                print(f"[*] Đã gửi {idx+1}/{len(alerts)} ST. Nghỉ giải lao {cooldown}s (Anti-Spam Cooldown)...", flush=True)
                await asyncio.sleep(cooldown)

        except errors.FloodWaitError as e:
            # 4. Tự động xử lý & thích ứng FloodWait (Auto-Backoff)
            wait_time = e.seconds + 2
            now_t = datetime.now().strftime('%H:%M:%S')
            update_broadcast_progress(idx, len(alerts), f"[{sid}] {c_title}", f"⚠️ Telegram FloodWait: Tạm dừng {wait_time}s...", success_count, len(failed), log_entry=f"[{now_t}] ⚠️ Chờ FloodWait {wait_time}s...")
            print(f"[!] Gặp FloodWait: Chờ {wait_time}s và tự động tăng độ trễ thích ứng...", flush=True)
            adaptive_delay += 1.5
            await asyncio.sleep(wait_time)
            try:
                topic_id = await get_forum_rau_topic_id(client, target)
                if img_path and os.path.exists(img_path):
                    sent_msg = await client.send_file(target, img_path, caption=msg_text, reply_to=topic_id)
                else:
                    sent_msg = await client.send_message(target, msg_text, reply_to=topic_id)
                sent_records.append((batch_id, target, c_title, sent_msg.id, msg_text))
                success_count += 1
                update_broadcast_progress(idx + 1, len(alerts), f"[{sid}] {c_title}", f"Đã gửi lại thành công [{sid}] {c_title}", success_count, len(failed), log_entry=f"[{now_t}] ✅ [{sid}] {c_title} (sau FloodWait) - Thành công")
            except Exception as e2:
                failed.append({"store_id": sid, "store_name": a.get('store_name'), "error": str(e2)})
                update_broadcast_progress(idx + 1, len(alerts), f"[{sid}] {c_title}", f"Lỗi gửi [{sid}]", success_count, len(failed), log_entry=f"[{now_t}] ❌ [{sid}] {c_title} - Lỗi: {e2}")

        except Exception as e:
            failed.append({"store_id": sid, "store_name": a.get('store_name'), "error": str(e)})
            now_t = datetime.now().strftime('%H:%M:%S')
            update_broadcast_progress(idx + 1, len(alerts), f"[{sid}] {c_title}", f"Lỗi gửi [{sid}]", success_count, len(failed), log_entry=f"[{now_t}] ❌ [{sid}] {c_title} - Lỗi: {e}")

    await client.disconnect()
    finish_broadcast_progress(success_count, len(failed))

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
