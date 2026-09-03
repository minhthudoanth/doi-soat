import os
import sys
import urllib.request
import csv
import io
import json
import sqlite3
from datetime import datetime, timedelta

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

if sys.platform == 'win32':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
        sys.stderr.reconfigure(encoding='utf-8')
    except Exception:
        pass

from config import DB_PATH
import re

DEFAULT_SHEET_URL = "https://docs.google.com/spreadsheets/d/1XBNLjZLsgaaHDBqVKsbCSYhzD4v-4qMA6rjGXGG4ThM/edit?gid=1422896115#gid=1422896115"

def init_settings_db():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS app_settings (
            key TEXT PRIMARY KEY,
            value TEXT
        )
    """)
    conn.commit()
    conn.close()

def get_sheet_url():
    init_settings_db()
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT value FROM app_settings WHERE key = 'sheet_url'")
    row = cursor.fetchone()
    conn.close()
    if row and row[0]:
        return row[0]
    return DEFAULT_SHEET_URL

def set_sheet_url(url):
    init_settings_db()
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("INSERT OR REPLACE INTO app_settings (key, value) VALUES ('sheet_url', ?)", (url.strip(),))
    conn.commit()
    conn.close()

def parse_csv_export_url(url):
    if not url:
        url = DEFAULT_SHEET_URL
    match_id = re.search(r"/spreadsheets/d/([a-zA-Z0-9-_]+)", url)
    sheet_id = match_id.group(1) if match_id else "1XBNLjZLsgaaHDBqVKsbCSYhzD4v-4qMA6rjGXGG4ThM"
    
    match_gid = re.search(r"[#&?]gid=([0-9]+)", url)
    gid = match_gid.group(1) if match_gid else "1422896115"
    
    return f"https://docs.google.com/spreadsheets/d/{sheet_id}/export?format=csv&gid={gid}"


def init_sheet_db():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS sheet_audit_records (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nguoi_xu_ly TEXT,
            transfer_date TEXT,
            branch_name TEXT,
            store_id TEXT,
            sku_code TEXT,
            item_name TEXT,
            uom TEXT,
            qty_transfer REAL DEFAULT 0,
            qty_receive REAL DEFAULT 0,
            qty_diff REAL DEFAULT 0,
            pt_transfer TEXT,
            box_code TEXT,
            to_code TEXT,
            qty_loss REAL DEFAULT 0,
            qty_return_st REAL DEFAULT 0,
            qty_diff_cxd REAL DEFAULT 0,
            pt_return_st TEXT,
            pt_return_dc TEXT,
            pt_dc_pick_du TEXT,
            note TEXT,
            status TEXT,
            error_type TEXT,
            loss_type TEXT,
            st_responsible TEXT,
            kho_responsible TEXT,
            process_status TEXT,
            image_link TEXT,
            dc_confirm TEXT,
            dc_note TEXT,
            kfm_response TEXT,
            kfm_note TEXT,
            item_type TEXT,
            package_type TEXT,
            loss_percent TEXT,
            unit_price REAL DEFAULT 0,
            total_amount REAL DEFAULT 0,
            loss_amount REAL DEFAULT 0,
            st_amount REAL DEFAULT 0,
            kho_amount REAL DEFAULT 0,
            cxd_amount REAL DEFAULT 0,
            gsm TEXT,
            rsm TEXT,
            area TEXT,
            pho_note TEXT,
            shipping_schedule TEXT,
            clv3 TEXT,
            clv4 TEXT
        )
    """)
    for col_def in [
        "nguoi_xu_ly TEXT", "image_link TEXT", "package_type TEXT",
        "pho_note TEXT", "shipping_schedule TEXT", "clv3 TEXT", "clv4 TEXT"
    ]:
        try:
            cursor.execute(f"ALTER TABLE sheet_audit_records ADD COLUMN {col_def}")
        except Exception:
            pass

    cursor.execute("CREATE INDEX IF NOT EXISTS idx_sheet_date ON sheet_audit_records(transfer_date)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_sheet_store ON sheet_audit_records(store_id)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_sheet_status ON sheet_audit_records(process_status)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_sheet_sku ON sheet_audit_records(sku_code)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_sheet_pt ON sheet_audit_records(pt_transfer, pt_return_st)")
    conn.commit()
    conn.close()

def parse_num(val):
    if not val:
        return 0.0
    s = str(val).strip().replace('.', '').replace(',', '.')
    try:
        return float(s)
    except:
        return 0.0

def sync_sheet_data():
    init_sheet_db()
    current_url = get_sheet_url()
    csv_url = parse_csv_export_url(current_url)
    print(f"[*] Đang tải dữ liệu từ Google Sheet: {csv_url}", flush=True)
    
    req = urllib.request.Request(csv_url, headers={'User-Agent': 'Mozilla/5.0'})
    with urllib.request.urlopen(req, timeout=30) as resp:
        content = resp.read().decode('utf-8')

        
    reader = csv.reader(io.StringIO(content))
    rows = list(reader)
    
    if len(rows) < 3:
        print("[!] File Sheet rỗng hoặc không đúng định dạng!", flush=True)
        return {"success": False, "count": 0}
        
    header = rows[2]
    data_rows = rows[3:]
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("DELETE FROM sheet_audit_records")
    
    inserted = 0
    batch = []
    
    for r in data_rows:
        if len(r) < 10:
            continue
            
        nguoi_xu_ly = r[0].strip() if len(r) > 0 else ""
        transfer_date = r[1].strip() if len(r) > 1 else ""
        branch_name = r[2].strip() if len(r) > 2 else ""
        store_id = r[3].strip() if len(r) > 3 else ""
        sku_code = r[4].strip() if len(r) > 4 else ""
        item_name = r[5].strip() if len(r) > 5 else ""
        uom = r[6].strip() if len(r) > 6 else ""
        
        qty_transfer = parse_num(r[7]) if len(r) > 7 else 0.0
        qty_receive = parse_num(r[8]) if len(r) > 8 else 0.0
        qty_diff = parse_num(r[9]) if len(r) > 9 else 0.0
        
        pt_transfer = r[10].strip() if len(r) > 10 else ""
        box_code = r[11].strip() if len(r) > 11 else ""
        to_code = r[12].strip() if len(r) > 12 else ""
        
        qty_loss = parse_num(r[13]) if len(r) > 13 else 0.0
        qty_return_st = parse_num(r[14]) if len(r) > 14 else 0.0
        qty_diff_cxd = parse_num(r[15]) if len(r) > 15 else 0.0
        
        pt_return_st = r[16].strip() if len(r) > 16 else ""
        pt_return_dc = r[17].strip() if len(r) > 17 else ""
        pt_dc_pick_du = r[18].strip() if len(r) > 18 else ""
        note = r[19].strip() if len(r) > 19 else ""
        status = r[20].strip() if len(r) > 20 else ""
        error_type = r[21].strip() if len(r) > 21 else ""
        loss_type = r[22].strip() if len(r) > 22 else ""
        st_responsible = r[23].strip() if len(r) > 23 else ""
        kho_responsible = r[24].strip() if len(r) > 24 else ""
        process_status = r[25].strip() if len(r) > 25 else "Đang xử lý"
        image_link = r[26].strip() if len(r) > 26 else ""
        dc_confirm = r[27].strip() if len(r) > 27 else ""
        dc_note = r[28].strip() if len(r) > 28 else ""
        kfm_response = r[29].strip() if len(r) > 29 else ""
        kfm_note = r[30].strip() if len(r) > 30 else ""
        item_type = r[31].strip() if len(r) > 31 else ""
        package_type = r[32].strip() if len(r) > 32 else ""
        loss_percent = r[33].strip() if len(r) > 33 else ""
        unit_price = parse_num(r[34]) if len(r) > 34 else 0.0
        total_amount = parse_num(r[35]) if len(r) > 35 else 0.0
        loss_amount = parse_num(r[36]) if len(r) > 36 else 0.0
        st_amount = parse_num(r[37]) if len(r) > 37 else 0.0
        kho_amount = parse_num(r[38]) if len(r) > 38 else 0.0
        cxd_amount = parse_num(r[39]) if len(r) > 39 else 0.0
        gsm = r[40].strip() if len(r) > 40 else ""
        rsm = r[41].strip() if len(r) > 41 else ""
        area = r[42].strip() if len(r) > 42 else ""
        pho_note = r[43].strip() if len(r) > 43 else ""
        shipping_schedule = r[44].strip() if len(r) > 44 else ""
        clv3 = r[45].strip() if len(r) > 45 else ""
        clv4 = r[46].strip() if len(r) > 46 else ""
        
        batch.append((
            nguoi_xu_ly, transfer_date, branch_name, store_id, sku_code, item_name, uom,
            qty_transfer, qty_receive, qty_diff, pt_transfer, box_code, to_code,
            qty_loss, qty_return_st, qty_diff_cxd, pt_return_st, pt_return_dc, pt_dc_pick_du,
            note, status, error_type, loss_type, st_responsible, kho_responsible,
            process_status, image_link, dc_confirm, dc_note, kfm_response, kfm_note, item_type, package_type,
            loss_percent, unit_price, total_amount, loss_amount, st_amount, kho_amount, cxd_amount,
            gsm, rsm, area, pho_note, shipping_schedule, clv3, clv4
        ))
        
        if len(batch) >= 1000:
            cursor.executemany("""
                INSERT INTO sheet_audit_records (
                    nguoi_xu_ly, transfer_date, branch_name, store_id, sku_code, item_name, uom,
                    qty_transfer, qty_receive, qty_diff, pt_transfer, box_code, to_code,
                    qty_loss, qty_return_st, qty_diff_cxd, pt_return_st, pt_return_dc, pt_dc_pick_du,
                    note, status, error_type, loss_type, st_responsible, kho_responsible,
                    process_status, image_link, dc_confirm, dc_note, kfm_response, kfm_note, item_type, package_type,
                    loss_percent, unit_price, total_amount, loss_amount, st_amount, kho_amount, cxd_amount,
                    gsm, rsm, area, pho_note, shipping_schedule, clv3, clv4
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, batch)
            inserted += len(batch)
            batch = []
            
    if batch:
        cursor.executemany("""
            INSERT INTO sheet_audit_records (
                nguoi_xu_ly, transfer_date, branch_name, store_id, sku_code, item_name, uom,
                qty_transfer, qty_receive, qty_diff, pt_transfer, box_code, to_code,
                qty_loss, qty_return_st, qty_diff_cxd, pt_return_st, pt_return_dc, pt_dc_pick_du,
                note, status, error_type, loss_type, st_responsible, kho_responsible,
                process_status, image_link, dc_confirm, dc_note, kfm_response, kfm_note, item_type, package_type,
                loss_percent, unit_price, total_amount, loss_amount, st_amount, kho_amount, cxd_amount,
                gsm, rsm, area, pho_note, shipping_schedule, clv3, clv4
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, batch)
        inserted += len(batch)

        
    conn.commit()
    conn.close()
    
    print(f"[*] Đồng bộ Google Sheet thành công: Đã lưu {inserted} dòng đối soát!", flush=True)
    
    # Đồng bộ luôn tab DS ST
    sync_ds_st_data()
    
    return {"success": True, "count": inserted}

def init_ds_st_db():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS sheet_store_list (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            store_name TEXT,
            store_id TEXT,
            spam TEXT,
            r2 TEXT,
            is_done INTEGER DEFAULT 0,
            phieu_bs TEXT,
            gsm TEXT,
            rsm TEXT,
            sm TEXT,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_store_list_name ON sheet_store_list(store_name)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_store_list_id ON sheet_store_list(store_id)")
    conn.commit()
    conn.close()

def sync_ds_st_data():
    """
    Tự động đồng bộ toàn bộ Danh Sách Siêu Thị (Tab 'DS ST') từ Google Sheet
    """
    init_ds_st_db()
    current_url = get_sheet_url()
    match_id = re.search(r"/spreadsheets/d/([a-zA-Z0-9-_]+)", current_url)
    sheet_id = match_id.group(1) if match_id else "1XBNLjZLsgaaHDBqVKsbCSYhzD4v-4qMA6rjGXGG4ThM"
    
    # URL export CSV cho tab DS ST (gid 1343221916)
    ds_st_url = f"https://docs.google.com/spreadsheets/d/{sheet_id}/export?format=csv&gid=1343221916"
    print(f"[*] Đang đồng bộ Danh Sách Siêu Thị (Tab DS ST): {ds_st_url}", flush=True)
    
    try:
        req = urllib.request.Request(ds_st_url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req, timeout=20) as resp:
            content = resp.read().decode('utf-8')
            
        reader = csv.reader(io.StringIO(content))
        rows = list(reader)
        if len(rows) <= 1:
            return {"success": False, "count": 0}
            
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("DELETE FROM sheet_store_list")
        
        batch = []
        for r in rows[1:]:
            if not r or not r[0].strip():
                continue
            st_name = r[0].strip()
            id_mart = r[1].strip() if len(r) > 1 else ""
            spam = r[2].strip() if len(r) > 2 else ""
            r2 = r[3].strip() if len(r) > 3 else ""
            done_val = r[4].strip() if len(r) > 4 else ""
            is_done = 1 if done_val.lower() == 'x' else 0
            phieu_bs = r[5].strip() if len(r) > 5 else ""
            gsm = r[11].strip() if len(r) > 11 else ""
            rsm = r[12].strip() if len(r) > 12 else ""
            sm = r[13].strip() if len(r) > 13 else ""
            
            batch.append((st_name, id_mart, spam, r2, is_done, phieu_bs, gsm, rsm, sm))
            
        if batch:
            cursor.executemany("""
                INSERT INTO sheet_store_list (store_name, store_id, spam, r2, is_done, phieu_bs, gsm, rsm, sm)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, batch)
            
        conn.commit()
        conn.close()
        print(f"[*] Đồng bộ DS ST thành công: Đã lưu {len(batch)} siêu thị vào CSDL!", flush=True)
        return {"success": True, "count": len(batch)}
    except Exception as e:
        print(f"[!] Lỗi đồng bộ DS ST: {e}", flush=True)
        return {"success": False, "error": str(e)}

def is_target_produce_or_bakery(cates, pname):
    cate_names = [str(c.get('name', '')).upper() for c in cates]
    combined = " ".join(cate_names)
    p_lower = pname.lower()
    
    # Exclude non-target categories
    non_targets = [
        'DAIRY', 'SỮA', 'YOGURT', 'FMCG', 'BEVERAGE', 'NƯỚC NGỌT', 'BIA', 'RƯỢU', 'LIQUOR',
        'CANNED', 'INSTANT', 'MÌ', 'PHỞ', 'BÚN', 'HỦ TIẾU', 'PERSONAL CARE', 'HOUSEHOLD',
        'SEASONING', 'GIA VỊ', 'CONFECTIONERY', 'BÁNH KẸO GÓI', 'SNACK', 'KEM', 'ICE CREAM',
        'COSMETIC', 'DRY FOOD', 'TOBACCO', 'FROZEN', 'MEAT', 'THỊT', 'HEO', 'BÒ', 'GÀ',
        'VỊT', 'POULTRY', 'PORK', 'BEEF', 'FISH', 'CÁ', 'SEAFOOD', 'HẢI SẢN', 'TÔM', 'MỰC',
        'READY TO EAT', 'READY TO COOK', 'RTC', 'RTE'
    ]
    for nt in non_targets:
        if nt in combined:
            return False, None
            
    if '2.FRUITS' in combined or 'TRÁI CÂY' in combined or 'FRUIT' in combined:
        return True, 'Trái Cây'
    if '2.VEGETABLES' in combined or 'RAU' in combined or 'CỦ' in combined or 'NẤM' in combined:
        return True, 'Rau Củ Quả'
    if '2.BAKERY' in combined or 'BÁNH TƯƠI' in combined:
        return True, 'Bánh Tươi / Bakery'
        
    fruit_kw = ['dưa', 'chuối', 'sầu riêng', 'bưởi', 'bơ', 'cam', 'táo', 'nho', 'xoài', 'mận', 'ổi', 'thanh long', 'chanh', 'quýt', 'mít', 'kiwi', 'lê', 'dâu', 'đu đủ', 'chôm chôm', 'măng cụt', 'nhãn', 'vải', 'lựu', 'cóc']
    if any(k in p_lower for k in fruit_kw):
        return True, 'Trái Cây'
        
    veg_kw = ['cải', 'rau', 'xà lách', 'khoai', 'cà rốt', 'cà chua', 'ớt', 'hành', 'tỏi', 'nấm', 'ngò', 'bầu', 'bí', 'mướp', 'khổ qua', 'đậu que', 'đậu bắp', 'bắp cải', 'súp lơ', 'bông cải', 'dưa leo', 'cà tím', 'gừng', 'sả', 'tía tô', 'kinh giới']
    if any(k in p_lower for k in veg_kw):
        return True, 'Rau Củ Quả'
        
    bake_kw = ['bánh mì', 'bánh tươi', 'sandwich', 'croissant', 'danish', 'baguette', 'muffin', 'toast']
    if any(k in p_lower for k in bake_kw) and not any(k in p_lower for k in ['snack', 'bánh quy', 'chocopie', 'oreo', 'custas']):
        return True, 'Bánh Tươi / Bakery'

    return False, None

def sync_inventory_from_sheet():
    """
    Đồng bộ dữ liệu Kiểm kê Nâng tồn (KK NÂNG TỒN) và Mã Âm tồn (DANH SÁCH MÃ ÂM TỒN)
    từ ngày 01/08 đến nay cho các mặt hàng Rau Củ Quả, Trái Cây, Bánh Tươi / Bakery.
    """
    try:
        from kingfood_api import get_headers
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS store_inventory_records (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                date TEXT,
                store_id TEXT,
                store_name TEXT,
                barcode TEXT,
                sku TEXT,
                product_name TEXT,
                category_name TEXT,
                opening_stock REAL DEFAULT 0,
                stocktake_in_qty REAL DEFAULT 0,
                stocktake_in_value REAL DEFAULT 0,
                stocktake_out_qty REAL DEFAULT 0,
                stocktake_out_value REAL DEFAULT 0,
                damage_qty REAL DEFAULT 0,
                closing_stock REAL DEFAULT 0,
                audit_note TEXT,
                status TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS store_negative_stock_records (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                date TEXT,
                store_id TEXT,
                store_name TEXT,
                barcode TEXT,
                sku TEXT,
                product_name TEXT,
                category_name TEXT,
                negative_qty REAL DEFAULT 0,
                negative_value REAL DEFAULT 0,
                closing_stock REAL DEFAULT 0,
                reason TEXT,
                status TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        cursor.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_inv_unique ON store_inventory_records (date, store_id, barcode)")
        cursor.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_neg_unique ON store_negative_stock_records (date, store_id, barcode)")

        cursor.execute("SELECT store_id, store_name FROM sheet_store_list")
        store_map = {r[0]: r[1] for r in cursor.fetchall()}
        
        nang_ton_rows = []
        am_ton_rows = []
        seen_keys = set()

        # 1. Thử lấy từ Kingfood API nếu có token hợp lệ
        try:
            print("[*] Đang đồng bộ dữ liệu Kiểm Kê (Rau, Củ, Quả, Bánh, Trái Cây) từ 01/08/2026 đến nay...", flush=True)
            from concurrent.futures import ThreadPoolExecutor, as_completed
            
            target_stocktakes = []
            skip = 0
            limit = 200
            reach_end = False

            while skip < 3000 and not reach_end:
                url = f'https://api.kingfood.co/v1/stocktakes?status=5&sort_by=created_at&sort_type=-1&limit={limit}&skip={skip}'
                try:
                    req = urllib.request.Request(url, headers=get_headers())
                    with urllib.request.urlopen(req, timeout=12) as resp:
                        st_data = json.loads(resp.read().decode('utf-8'))
                        st_list = st_data.get('items', [])
                        if not st_list:
                            break
                        for st in st_list:
                            dt = (st.get('created_at') or st.get('completed_at') or '')[:10]
                            if dt and dt < '2026-08-01':
                                reach_end = True
                                break
                            if st.get('total_sku', 0) > 0:
                                target_stocktakes.append(st)
                        if reach_end:
                            break
                    skip += limit
                except Exception as e:
                    print(f"[*] Lỗi duyệt trang phiếu kiểm kê skip={skip}: {e}", flush=True)
                    break

            def process_st(st):
                st_id = st.get('id')
                st_code = st.get('code', '')
                created_at_str = st.get('created_at') or st.get('completed_at') or ''
                date_iso = datetime.now().strftime('%Y-%m-%d')
                if created_at_str:
                    try:
                        dt = datetime.fromisoformat(created_at_str.replace('Z', '+00:00')) + timedelta(hours=7)
                        date_iso = dt.strftime('%Y-%m-%d')
                    except Exception:
                        pass
                store_code = ''
                m = re.search(r'^\d{6}-([A-Za-z0-9]+)-', st_code)
                if m:
                    store_code = m.group(1)
                else:
                    store_code = st.get('branch_id', '')[:8]
                store_name = store_map.get(store_code, f"KFM_{store_code}")

                lines_url = f'https://api.kingfood.co/v1/stocktakes/lines?stocktake_id={st_id}&limit=100'
                res_items = []
                try:
                    r_lines = urllib.request.Request(lines_url, headers=get_headers())
                    with urllib.request.urlopen(r_lines, timeout=8) as res_l:
                        l_data = json.loads(res_l.read().decode('utf-8'))
                        for line in l_data.get('items', []):
                            bcode = str(line.get('barcode') or '').strip()
                            pname = str(line.get('name') or '').strip()
                            if not bcode or not pname:
                                continue
                            cates = line.get('cates', [])
                            is_tgt, cat_name = is_target_produce_or_bakery(cates, pname)
                            if not is_tgt:
                                continue
                            diff_q = float(line.get('diff_quantity') or 0.0)
                            stock_q = float(line.get('stock_quantity') or 0.0)
                            actual_q = float(line.get('actual_stock_quantity') or 0.0)
                            diff_v = float(line.get('diff_value') or 0.0)
                            cost = float(line.get('cost') or 0.0)
                            price = float(line.get('price') or 0.0)
                            res_items.append((date_iso, store_code, store_name, st_code, bcode, pname, cat_name, stock_q, diff_q, diff_v, cost, price, actual_q))
                except Exception:
                    pass
                return res_items

            with ThreadPoolExecutor(max_workers=8) as executor:
                futures = [executor.submit(process_st, st) for st in target_stocktakes]
                for f in as_completed(futures):
                    items = f.result()
                    for (date_iso, store_code, store_name, st_code, bcode, pname, cat_name, stock_q, diff_q, diff_v, cost, price, actual_q) in items:
                        key = (date_iso, store_code, bcode)
                        if key in seen_keys:
                            continue
                        seen_keys.add(key)
                        if diff_v <= 0 and diff_q > 0:
                            diff_v = diff_q * (cost if cost > 0 else price)
                        if diff_q > 0:
                            audit_note = f"Phiếu KK {st_code} (Sổ sách: {stock_q} -> Thực tế: {actual_q})"
                            status_lbl = "Bất thường" if diff_v > 200000 else ("Cần lưu ý" if diff_v > 50000 else "Đã kiểm kê")
                            nang_ton_rows.append((
                                date_iso, store_code, store_name, bcode, bcode, pname, cat_name,
                                stock_q, diff_q, round(diff_v, 0), 0.0, 0.0, 0.0, actual_q,
                                audit_note, status_lbl
                            ))
                        if stock_q < 0:
                            neg_val = abs(stock_q) * (cost if cost > 0 else price)
                            neg_note = f"Tồn sổ sách bị âm ({stock_q}) trước khi kiểm kê {st_code}"
                            am_ton_rows.append((
                                date_iso, store_code, store_name, bcode, bcode, pname, cat_name,
                                abs(stock_q), round(neg_val, 0), stock_q, neg_note, "Cần bù tồn"
                            ))
        except Exception as api_err:
            print(f"[*] Kingfood API Stocktakes: {api_err}", flush=True)

        # Lưu vào Database: chỉ lưu khi có dữ liệu kiểm kê thực tế, KHÔNG lấy từ phiếu chuyển
        cursor.execute("DELETE FROM store_inventory_records")
        cursor.execute("DELETE FROM store_negative_stock_records")
        
        if nang_ton_rows:
            cursor.executemany("""
                INSERT INTO store_inventory_records (
                    date, store_id, store_name, barcode, sku, product_name, category_name,
                    opening_stock, stocktake_in_qty, stocktake_in_value, stocktake_out_qty, stocktake_out_value, damage_qty, closing_stock,
                    audit_note, status
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, nang_ton_rows)
            
        if am_ton_rows:
            cursor.executemany("""
                INSERT INTO store_negative_stock_records (
                    date, store_id, store_name, barcode, sku, product_name, category_name,
                    negative_qty, negative_value, closing_stock, reason, status
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, am_ton_rows)
        conn.commit()
        conn.close()
        print(f"[*] Đồng bộ tồn kho hoàn tất từ 01/08/2026 đến nay: {len(nang_ton_rows)} mã KK Nâng Tồn (+), {len(am_ton_rows)} mã Âm Tồn (-) thuộc Rau, Củ, Quả, Bánh, Trái Cây.", flush=True)
        return {"success": True, "increase_count": len(nang_ton_rows), "negative_count": len(am_ton_rows)}
    except Exception as e:
        print(f"[!] Lỗi sync_inventory_from_sheet: {e}", flush=True)
        return {"success": False, "error": str(e)}


DEFAULT_INVOICE_SHEET_URL = "https://docs.google.com/spreadsheets/d/1YfpVHQbowoSj6lN-8KW0d1UmCKy4sy2PesB7g9yNG4M/export?format=csv&gid=0"

def sync_claim_invoices_from_sheet(sheet_url=None):
    if not sheet_url:
        sheet_url = DEFAULT_INVOICE_SHEET_URL
    elif "export?format=csv" not in sheet_url:
        match_id = re.search(r"/spreadsheets/d/([a-zA-Z0-9-_]+)", sheet_url)
        sheet_id = match_id.group(1) if match_id else "1YfpVHQbowoSj6lN-8KW0d1UmCKy4sy2PesB7g9yNG4M"
        match_gid = re.search(r"gid=([0-9]+)", sheet_url)
        gid = match_gid.group(1) if match_gid else "0"
        sheet_url = f"https://docs.google.com/spreadsheets/d/{sheet_id}/export?format=csv&gid={gid}"

    print(f"[*] Đang tải dữ liệu Hóa Đơn Truy Thu từ Google Sheet: {sheet_url}", flush=True)
    try:
        req = urllib.request.Request(sheet_url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req, timeout=30) as response:
            content = response.read().decode('utf-8')

        reader = csv.reader(io.StringIO(content))
        rows = list(reader)

        if not rows or len(rows) < 2:
            print("[!] File Google Sheet hóa đơn không có dữ liệu!", flush=True)
            return {'success': False, 'error': 'Không có dữ liệu'}

        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS warehouse_claim_invoices (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                month TEXT,
                warehouse_code TEXT,
                warehouse_name TEXT,
                invoice_date TEXT,
                content TEXT,
                invoice_number TEXT,
                co_number TEXT,
                pre_tax REAL,
                post_tax REAL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        cursor.execute("DELETE FROM warehouse_claim_invoices")

        current_month = "07"
        current_wh = "MF"
        invoices_to_insert = []

        for r in rows[1:]:
            if not any(r): continue
            month_val = r[0].strip() if len(r) > 0 else ""
            wh_val = r[1].strip() if len(r) > 1 else ""
            date_val = r[2].strip() if len(r) > 2 else ""
            content_val = r[3].strip() if len(r) > 3 else ""
            co_val = r[4].strip() if len(r) > 4 else ""
            pre_tax_str = r[5].strip().replace(',', '') if len(r) > 5 else "0"
            post_tax_str = r[6].strip().replace(',', '') if len(r) > 6 else "0"

            if month_val:
                current_month = month_val.zfill(2)
            if wh_val:
                current_wh = wh_val

            try:
                pre_tax = float(pre_tax_str) if pre_tax_str else 0.0
            except:
                pre_tax = 0.0

            try:
                post_tax = float(post_tax_str) if post_tax_str else 0.0
            except:
                post_tax = 0.0

            inv_num = ""
            m_inv = re.search(r'hóa đơn số\s*:\s*(\d+)', content_val, re.IGNORECASE)
            if m_inv:
                inv_num = m_inv.group(1)

            wh_name = "KHO MEATFISH" if current_wh == "MF" else ("KHO SEEDLOG" if current_wh == "SL" else ("KHO ĐÔNG MÁT" if current_wh == "DM" else f"KHO {current_wh}"))

            invoices_to_insert.append((
                current_month, current_wh, wh_name, date_val, content_val,
                inv_num, co_val, pre_tax, post_tax
            ))

        if invoices_to_insert:
            cursor.executemany("""
                INSERT INTO warehouse_claim_invoices (
                    month, warehouse_code, warehouse_name, invoice_date, content,
                    invoice_number, co_number, pre_tax, post_tax
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, invoices_to_insert)
            conn.commit()
            print(f"[*] Đồng bộ Hóa Đơn Truy Thu thành công: Đã nạp {len(invoices_to_insert)} dòng hóa đơn!", flush=True)

        conn.close()
        return {'success': True, 'count': len(invoices_to_insert)}
    except Exception as e:
        print(f"[!] Lỗi sync_claim_invoices_from_sheet: {e}", flush=True)
        return {'success': False, 'error': str(e)}

if __name__ == '__main__':
    sync_sheet_data()
    sync_ds_st_data()
    sync_inventory_from_sheet()
    sync_claim_invoices_from_sheet()


