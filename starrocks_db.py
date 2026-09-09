import os
import sys
import time
import uuid
import socket
import logging
from datetime import datetime
import pymysql
from pymysql.cursors import DictCursor

from config import (
    STARROCKS_HOST,
    STARROCKS_PORT,
    STARROCKS_USER,
    STARROCKS_PASSWORD,
    STARROCKS_DB,
    STARROCKS_WRITE_LOCKED,
    STARROCKS_ISOLATION_MODE,
    DATA_OWNER,
    TABLE_DISCREPANCIES_THU,
    TABLE_MESSAGES_THU,
    DB_PATH
)

logger = logging.getLogger("starrocks_db")

# Namespace cố định để sinh deterministic UUIDv5 chống duplicate
NAMESPACE_SCM_MSG = uuid.UUID("3fa85f64-5717-4562-b3fc-2c963f66afa6")
NAMESPACE_SCM_DISC = uuid.UUID("7b958c21-1248-43d9-952b-47e93051a8d4")

def get_starrocks_conn(timeout=15, retries=3):
    """
    Tạo kết nối tới cơ sở dữ liệu StarRocks qua giao thức MySQL với cơ chế tự động thử lại (retry).
    """
    last_err = None
    for attempt in range(1, retries + 1):
        try:
            return pymysql.connect(
                host=STARROCKS_HOST,
                port=STARROCKS_PORT,
                user=STARROCKS_USER,
                password=STARROCKS_PASSWORD,
                database=STARROCKS_DB,
                charset="utf8mb4",
                connect_timeout=timeout,
                read_timeout=timeout,
                write_timeout=timeout,
                autocommit=True
            )
        except Exception as e:
            last_err = e
            if attempt < retries:
                time.sleep(1.5 * attempt)
    raise last_err

def check_vpn_and_starrocks():
    """
    Kiểm tra toàn diện trạng thái mạng VPN và kết nối cơ sở dữ liệu StarRocks:
    1. Socket TCP kết nối tới port 9030
    2. Xác thực tài khoản và quyền truy cập DB kfm_scm
    3. Thống kê số lượng bản ghi các bảng chính (bao gồm bảng riêng đã cô lập)
    """
    result = {
        "success": False,
        "vpn_reachable": False,
        "starrocks_connected": False,
        "host": STARROCKS_HOST,
        "port": STARROCKS_PORT,
        "database": STARROCKS_DB,
        "user": STARROCKS_USER,
        "data_owner": DATA_OWNER,
        "isolation_mode": STARROCKS_ISOLATION_MODE,
        "isolated_tables": {
            "discrepancies": TABLE_DISCREPANCIES_THU,
            "messages": TABLE_MESSAGES_THU
        },
        "mode": f"BẢO VỆ CÔ LẬP DỮ LIỆU RIÊNG ({DATA_OWNER}) - Chống bot khác can thiệp" if STARROCKS_ISOLATION_MODE else "DÙNG CHUNG",
        "version": None,
        "tables": {},
        "error": None
    }

    # 1. Thử kết nối TCP Socket
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(2.5)
        res = s.connect_ex((STARROCKS_HOST, STARROCKS_PORT))
        s.close()
        result["vpn_reachable"] = (res == 0)
        if res != 0:
            result["error"] = f"Không thể kết nối cổng {STARROCKS_PORT} trên {STARROCKS_HOST} (mã lỗi socket: {res}). Hãy kiểm tra lại kết nối WireGuard VPN."
            return result
    except Exception as e:
        result["error"] = f"Lỗi kiểm tra kết nối socket VPN: {e}"
        return result

    # 2. Thử đăng nhập StarRocks
    try:
        conn = get_starrocks_conn(timeout=5)
        with conn.cursor() as cur:
            cur.execute("SELECT VERSION();")
            ver = cur.fetchone()
            result["version"] = ver[0] if ver else "Unknown"

            all_check_tables = [
                TABLE_DISCREPANCIES_THU,
                TABLE_MESSAGES_THU,
                "krc_dashboard_messages",
                "krc_dashboard_discrepancies",
                "krc_dashboard_telegram_groups"
            ]
            for tbl in all_check_tables:
                try:
                    cur.execute(f"SELECT COUNT(*) FROM `{tbl}`;")
                    cnt = cur.fetchone()[0]
                    result["tables"][tbl] = cnt
                except Exception as te:
                    result["tables"][tbl] = f"Chưa tạo hoặc lỗi: {te}"

        conn.close()
        result["starrocks_connected"] = True
        result["success"] = True
    except Exception as e:
        result["error"] = f"Lỗi kết nối StarRocks: {e}"

    return result

def save_message_to_starrocks(msg_id, chat_id, chat_title, sender_id, sender_name,
                              text, category=None, priority=None, issue_type=None,
                              created_at=None, image_path="", completed=0, feedback_text=""):
    """
    Lưu hoặc cập nhật một tin nhắn Telegram vào StarRocks bảng krc_dashboard_messages.
    Nếu STARROCKS_WRITE_LOCKED = True, thao tác ghi sẽ bị khóa an toàn để không ảnh hưởng dữ liệu web.
    """
    if STARROCKS_WRITE_LOCKED:
        return True

    try:
        # Tạo UUID định danh duy nhất theo chat_id và msg_id
        unique_key = f"{chat_id}_{msg_id}"
        rec_id = str(uuid.uuid5(NAMESPACE_SCM_MSG, unique_key))
        
        c_at = created_at or datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        ts_str = str(c_at)

        target_tbl = TABLE_MESSAGES_THU if STARROCKS_ISOLATION_MODE else "krc_dashboard_messages"
        conn = get_starrocks_conn(timeout=15)
        with conn.cursor() as cur:
            sql = f"""
                INSERT INTO `{target_tbl}` (
                    `id`, `telegram_msg_id`, `group_name`, `group_id`,
                    `sender_name`, `sender_id`, `text`, `image_path`,
                    `message_type`, `timestamp`, `completed`, `feedback_text`,
                    `completed_by`, `group_type`, `created_at`
                ) VALUES (
                    %s, %s, %s, %s,
                    %s, %s, %s, %s,
                    %s, %s, %s, %s,
                    %s, %s, %s
                )
            """
            cur.execute(sql, (
                rec_id,
                int(msg_id) if msg_id else None,
                str(chat_title or "")[:500],
                int(chat_id) if chat_id else None,
                str(sender_name or "")[:255],
                int(sender_id) if sender_id else None,
                str(text or ""),
                str(image_path or ""),
                "text" if not image_path else "photo",
                ts_str,
                int(completed),
                str(feedback_text or ""),
                str(DATA_OWNER),
                "krc",
                c_at
            ))
        conn.close()
        return True
    except Exception as e:
        logger.warning(f"Không thể lưu tin nhắn vào StarRocks: {e}")
        return False

def batch_save_messages_to_starrocks(messages_list):
    """
    Lưu hàng loạt tin nhắn vào StarRocks krc_dashboard_messages.
    Nếu STARROCKS_WRITE_LOCKED = True, thao tác sẽ bị chặn an toàn.
    """
    if STARROCKS_WRITE_LOCKED:
        logger.info("STARROCKS_WRITE_LOCKED=True: Khóa ghi an toàn, bỏ qua lưu tin nhắn lên StarRocks VPN.")
        return 0

    if not messages_list:
        return 0

    conn = get_starrocks_conn(timeout=60)
    inserted = 0
    batch_size = 200
    target_tbl = TABLE_MESSAGES_THU if STARROCKS_ISOLATION_MODE else "krc_dashboard_messages"

    sql = f"""
        INSERT INTO `{target_tbl}` (
            `id`, `telegram_msg_id`, `group_name`, `group_id`,
            `sender_name`, `sender_id`, `text`, `image_path`,
            `message_type`, `timestamp`, `completed`, `feedback_text`,
            `completed_by`, `group_type`, `created_at`
        ) VALUES (
            %s, %s, %s, %s,
            %s, %s, %s, %s,
            %s, %s, %s, %s,
            %s, %s, %s
        )
    """

    for i in range(0, len(messages_list), batch_size):
        chunk = messages_list[i:i + batch_size]
        params = []
        for m in chunk:
            msg_id = m.get("msg_id")
            chat_id = m.get("chat_id")
            unique_key = f"{chat_id}_{msg_id}" if chat_id and msg_id else str(uuid.uuid4())
            rec_id = str(uuid.uuid5(NAMESPACE_SCM_MSG, unique_key))

            c_at = m.get("created_at") or datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            params.append((
                rec_id,
                int(msg_id) if msg_id else None,
                str(m.get("chat_title") or "")[:500],
                int(chat_id) if chat_id else None,
                str(m.get("sender_name") or "")[:255],
                int(m.get("sender_id")) if m.get("sender_id") else None,
                str(m.get("message_text") or m.get("text") or ""),
                str(m.get("image_path") or ""),
                str(m.get("message_type") or "text"),
                str(c_at),
                int(m.get("completed", 0)),
                str(m.get("feedback_text") or ""),
                str(DATA_OWNER if STARROCKS_ISOLATION_MODE else (m.get("completed_by") or DATA_OWNER)),
                str(m.get("group_type") or "krc"),
                c_at
            ))

        with conn.cursor() as cur:
            cur.executemany(sql, params)
            inserted += len(params)

    conn.close()
    return inserted

def batch_save_discrepancies_to_starrocks(disc_list):
    """
    Lưu hàng loạt ca chênh lệch vào StarRocks krc_dashboard_discrepancies.
    Nếu STARROCKS_WRITE_LOCKED = True, thao tác sẽ bị chặn an toàn.
    """
    if STARROCKS_WRITE_LOCKED:
        logger.info("STARROCKS_WRITE_LOCKED=True: Khóa ghi an toàn, bỏ qua lưu chênh lệch lên StarRocks VPN.")
        return 0

    if not disc_list:
        return 0

    conn = get_starrocks_conn(timeout=60)
    inserted = 0
    batch_size = 200
    target_tbl = TABLE_DISCREPANCIES_THU if STARROCKS_ISOLATION_MODE else "krc_dashboard_discrepancies"

    sql = f"""
        INSERT INTO `{target_tbl}` (
            `id`, `nguoi_xu_ly`, `ngay`, `chi_nhanh`, `id_st`,
            `ma_hang`, `ten_hang`, `dvt`, `sl_chuyen`, `sl_nhan`,
            `chenh_lech`, `pt_chuyen_hang`, `sl_nhan_thuc`, `sl_bs_st`, `sl_cl_dxl`,
            `pt_tra_ton_st`, `pt_tra_ton_dc`, `pt_dc_pick_du`, `note`, `trang_thai`,
            `loi`, `hao_hut`, `noi_nhan`, `kho_rau`, `xu_ly`,
            `link_hinh`, `dc_xac_nhan`, `note_dc`, `kfm_xac_nhan`, `note_kfm`,
            `clv2`, `tote`, `loai_hang`, `phan_tram`, `don_gia`,
            `thanh_tien`, `tien_tra_st`, `tien_tra_dc`, `tien_dc_pick`, `tien_con_lai`,
            `gsm`, `rsm`, `khu_vuc`, `tho_note`, `lich_di_hang`,
            `clv3`, `clv4`, `updated_at`
        ) VALUES (
            %s, %s, %s, %s, %s,
            %s, %s, %s, %s, %s,
            %s, %s, %s, %s, %s,
            %s, %s, %s, %s, %s,
            %s, %s, %s, %s, %s,
            %s, %s, %s, %s, %s,
            %s, %s, %s, %s, %s,
            %s, %s, %s, %s, %s,
            %s, %s, %s, %s, %s,
            %s, %s, %s
        )
    """

    for i in range(0, len(disc_list), batch_size):
        chunk = disc_list[i:i + batch_size]
        params = []
        now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        for d in chunk:
            # Tạo unique key deterministic
            ngay = str(d.get("transfer_date") or d.get("ngay") or "")
            st_id = str(d.get("store_id") or d.get("id_st") or "")
            sku = str(d.get("sku_code") or d.get("ma_hang") or "")
            pt = str(d.get("pt_transfer") or d.get("pt_chuyen_hang") or "")
            item_name = str(d.get("item_name") or d.get("ten_hang") or "")
            
            unique_key = f"{ngay}_{st_id}_{sku}_{pt}_{item_name}"
            rec_id = str(uuid.uuid5(NAMESPACE_SCM_DISC, unique_key))

            def _f(val):
                try:
                    return float(val) if val is not None and val != '' else 0.0
                except (ValueError, TypeError):
                    return 0.0

            params.append((
                rec_id,
                str(DATA_OWNER if STARROCKS_ISOLATION_MODE else (d.get("nguoi_xu_ly") or DATA_OWNER)),
                ngay,
                str(d.get("branch_name") or d.get("chi_nhanh") or ""),
                st_id,
                sku,
                item_name,
                str(d.get("uom") or d.get("dvt") or ""),
                _f(d.get("qty_transfer") or d.get("sl_chuyen")),
                _f(d.get("qty_receive") or d.get("sl_nhan")),
                _f(d.get("qty_diff") or d.get("chenh_lech")),
                pt,
                _f(d.get("qty_receive") or d.get("sl_nhan_thuc")),
                _f(d.get("qty_diff_cxd") or d.get("sl_bs_st")),
                _f(d.get("qty_loss") or d.get("sl_cl_dxl")),
                str(d.get("pt_return_st") or d.get("pt_tra_ton_st") or ""),
                str(d.get("pt_return_dc") or d.get("pt_tra_ton_dc") or ""),
                str(d.get("pt_dc_pick_du") or ""),
                str(d.get("note") or ""),
                str(d.get("status") or d.get("trang_thai") or ""),
                str(d.get("error_type") or d.get("loi") or ""),
                str(d.get("loss_type") or d.get("hao_hut") or ""),
                str(d.get("st_responsible") or d.get("noi_nhan") or ""),
                str(d.get("kho_responsible") or d.get("kho_rau") or ""),
                str(d.get("process_status") or d.get("xu_ly") or ""),
                str(d.get("image_link") or d.get("link_hinh") or ""),
                str(d.get("dc_confirm") or d.get("dc_xac_nhan") or ""),
                str(d.get("dc_note") or d.get("note_dc") or ""),
                str(d.get("kfm_response") or d.get("kfm_xac_nhan") or ""),
                str(d.get("kfm_note") or d.get("note_kfm") or ""),
                str(d.get("clv2") or ""),
                str(d.get("box_code") or d.get("tote") or ""),
                str(d.get("item_type") or d.get("loai_hang") or ""),
                str(d.get("loss_percent") or d.get("phan_tram") or ""),
                _f(d.get("unit_price") or d.get("don_gia")),
                _f(d.get("total_amount") or d.get("thanh_tien")),
                _f(d.get("st_amount") or d.get("tien_tra_st")),
                _f(d.get("kho_amount") or d.get("tien_tra_dc")),
                _f(d.get("tien_dc_pick")),
                _f(d.get("loss_amount") or d.get("tien_con_lai")),
                str(d.get("gsm") or ""),
                str(d.get("rsm") or ""),
                str(d.get("area") or d.get("khu_vuc") or ""),
                str(d.get("pho_note") or d.get("tho_note") or ""),
                str(d.get("shipping_schedule") or d.get("lich_di_hang") or ""),
                str(d.get("clv3") or ""),
                str(d.get("clv4") or ""),
                now_str
            ))

        with conn.cursor() as cur:
            cur.executemany(sql, params)
            inserted += len(params)

    conn.close()
    return inserted

def sync_sqlite_to_starrocks(limit_messages=1000, limit_discrepancies=5000):
    """
    Đồng bộ dữ liệu từ CSDL cục bộ SQLite (scm_monitor.db) lên StarRocks kfm_scm.
    Nếu STARROCKS_WRITE_LOCKED = True, thao tác sẽ bị chặn để bảo vệ hệ thống web.
    """
    if STARROCKS_WRITE_LOCKED:
        return {
            "messages_synced": 0,
            "discrepancies_synced": 0,
            "locked": True,
            "error": "Database trên VPN đang ở chế độ KHÓA GHI (Read-Only) để không làm ảnh hưởng đến dữ liệu web công ty."
        }

    import sqlite3
    stats = {
        "messages_synced": 0,
        "discrepancies_synced": 0,
        "error": None
    }

    if not os.path.exists(DB_PATH):
        stats["error"] = f"Không tìm thấy file SQLite tại {DB_PATH}"
        return stats

    # Kiểm tra kết nối trước
    probe = check_vpn_and_starrocks()
    if not probe["success"]:
        stats["error"] = probe.get("error", "Không thể kết nối đến StarRocks qua VPN")
        return stats

    conn_sq = sqlite3.connect(DB_PATH)
    conn_sq.row_factory = sqlite3.Row
    cur_sq = conn_sq.cursor()

    # 1. Đồng bộ tin nhắn
    try:
        cur_sq.execute(f"SELECT * FROM raw_messages ORDER BY id DESC LIMIT {int(limit_messages)}")
        rows = [dict(r) for r in cur_sq.fetchall()]
        if rows:
            stats["messages_synced"] = batch_save_messages_to_starrocks(rows)
    except Exception as me:
        stats["error_messages"] = str(me)

    # 2. Đồng bộ chênh lệch
    try:
        cur_sq.execute(f"SELECT * FROM sheet_audit_records ORDER BY id DESC LIMIT {int(limit_discrepancies)}")
        rows = [dict(r) for r in cur_sq.fetchall()]
        if rows:
            stats["discrepancies_synced"] = batch_save_discrepancies_to_starrocks(rows)
    except Exception as de:
        stats["error_discrepancies"] = str(de)

    conn_sq.close()
    if stats.get("error_messages") or stats.get("error_discrepancies"):
        stats["error"] = "; ".join(filter(None, [stats.get("error_messages"), stats.get("error_discrepancies")]))

    return stats
