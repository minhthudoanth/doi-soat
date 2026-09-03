import urllib.request
import json
import re
from datetime import datetime, timedelta
import sqlite3
import os
from config import DB_PATH

DEFAULT_KINGFOOD_TOKEN = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ1c2VyIjp7ImlkIjoiNjk4MTYwYzkzMzljOTkwMDA3MTFjMTE3IiwiZnVsbF9uYW1lIjoixJBvw6BuIFRo4buLIE1pbmggVGjGsCIsImVtYWlsIjoidGh1LmRvYW50aGltaW5oQGtpbmdmb29kbWFydC5jb20iLCJlbXBsb3llZV9jb2RlIjoiU0MwMTcwODQiLCJsYXN0X2xvZ2luIjoxNzg4MDYzMjE3ODc1LCJleHRlbmRfcm9sZXMiOnt9LCJ1dWlkIjoiZDUwOThhNDBlNWQ0ODhkOTZlZTZjNmYxODQ3ZWNhNjgiLCJyYmFjIjpudWxsfSwiaWF0IjoxNzg4MDYzMjE3LCJleHAiOjE3ODg2NjgwMTd9.C49GIJ5ykwTuRnqkv-5doXbhVUrvL8qsJjOWclw9Wj4'

def get_kingfood_token():
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("CREATE TABLE IF NOT EXISTS app_settings (key TEXT PRIMARY KEY, value TEXT)")
        cursor.execute("SELECT value FROM app_settings WHERE key = 'kingfood_token'")
        row = cursor.fetchone()
        conn.close()
        if row and row[0] and row[0].strip():
            return row[0].strip()
    except Exception:
        pass
    return DEFAULT_KINGFOOD_TOKEN

def set_kingfood_token(token):
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("CREATE TABLE IF NOT EXISTS app_settings (key TEXT PRIMARY KEY, value TEXT)")
        cursor.execute("INSERT OR REPLACE INTO app_settings (key, value) VALUES ('kingfood_token', ?)", (token.strip(),))
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        print(f"Lỗi set_kingfood_token: {e}")
        return False

KINGFOOD_TOKEN = get_kingfood_token()


# ID CHUẨN CỦA KHO RAU CỦ (KRC)
KRC_BRANCH_ID = '5fdc170ebd89c10006f15b7c'

BRANCH_CACHE = []

STORE_ALIAS_MAP = {
    'CTH': 'Citihome',
    'SFR': 'Safira',
    'PHG': 'Phạm Hùng',
    'PHI': 'Phan Huy Ích',
    'TR': 'Rivana',
    'HTP': 'Huỳnh Tấn Phát',
    'QHG': 'Quốc Hương',
    'THN': 'Tạ Hiện',
    'LVY': 'Lê Văn Sỹ',
    'NKM': 'Nguyễn Kiệm',
    'NVQ': 'Nguyễn Văn Quá',
    'BCG': 'BCons Garden',
    'NVK': 'Nguyễn Văn Khối',
    'A154': 'Liên Phường',
    'TSO': 'Trường Sơn',
    'ERT': 'Era Town',
    'CLN': 'Chợ Lớn',
    'AV4': 'The Sun Avenue',
    'VH3': 'Vinhomes',
    'VH7': 'Chợ Lớn',
    'HMN': 'Him Lam',
    'OPAL': 'Opal',
    'SKY9': 'Sky 9',
    'MIDTOWN': 'Midtown',
    'GOLDEN': 'Golden Star',
    'NH': 'Nguyên Hồng',
    'LVT': 'Lê Văn Thọ',
    'DQH': 'Dương Quảng Hàm',
    'TN': 'Thống Nhất',
    'LDT': 'Lê Đức Thọ',
    'PVB': 'Phạm Văn Bạch',
    'NVD': 'Nguyễn Văn Dung',
    'CLP': 'Cityland',
    'MAN': 'Man Thiện',
    'DXH': 'Đỗ Xuân Hợp',
    'ECG': 'Eco Green',
    'RIC': 'Richstar',
    'MKI': 'Mizuki',
    'PEG': 'Pegasuite',
    'HMO': 'Harmona',
    'VLA': 'Vườn Lài',
    'AKA': 'Akari',
    'EHO': 'EHomeS',
    'TNA': 'Trần Não',
    'GHA': 'Gia Hòa',
    'IMP': 'Imperia',
    'SUN': 'The Sun Avenue',
    'MID': 'Midtown',
    'HML': 'Him Lam',
    'MAS': 'Masterise',
    'MIA': 'Saigon Mia',
    'MEL': 'Melody',
    'THV': 'Thuận Việt',
    'BTU': 'Bùi Đình Túy',
    'TTN': 'Tân Thới Nhất',
    'NTO': 'Ngô Tất Tố',
    'SSR': 'Saigon South',
    'BTH': 'Bình Thành',
    'NTN': 'Nguyễn Thị Nhung',
    'HTN': 'Hồ Thị Nhung',
    'OSK': 'Opal Skyline',
    'LTI': 'Lê Văn Thịnh',
    'LVY': '236A Lê Văn Sỹ',
    'A126': '274 Lê Văn Sỹ',

    'PVH': 'Phan Văn Hân',
    'TTC': 'Trần Thị Cờ',
    'LQD': 'Lê Quang Định',
    'RIV': 'The Rivana',
    'TTH': 'Thành Thái',
    'VTU': 'Vũ Tùng',
    'NTU': 'Nguyễn Thị Tú',
    'NTD': 'Nguyễn Thị Định',
    'TNH': 'Thống Nhất',
    'BQU': 'Bình Quới',
    'LTC': 'Lê Thị Chợ',
    'PTH': 'Phú Thuận',
    'TMY': 'Tân Mỹ',
    'HHT': 'Hoàng Hoa Thám',
    'NTT': 'Nguyễn Thị Thập',
    'VHT': 'Vũ Huy Tấn',
    'BBA': 'Bùi Văn Ba',
    'NHG': 'Nguyên Hồng',
    'KHO': 'Khánh Hội',
    'NVT': 'Nguyễn Văn Tăng',
    'CKE': 'Cây Keo',
    'LVL': 'Lê Văn Lương',
    'LVB': 'Lâm Văn Bền',
    'NDT': 'Nguyễn Duy Trinh',
    'GLD': 'Golden Star'
}



PRODUCT_NAME_CACHE = {}

def lookup_product_name_by_barcode(barcode):
    """
    Tra cứu tên sản phẩm chính xác theo mã Barcode / SKU từ Kingfood API
    """
    if not barcode or str(barcode).strip() in ['---', '']:
        return ''
    b = str(barcode).strip()
    if b in PRODUCT_NAME_CACHE:
        return PRODUCT_NAME_CACHE[b]
        
    try:
        url = f'https://api.kingfood.co/v1/variants?barcode={b}'
        req = urllib.request.Request(url, headers=get_headers())
        with urllib.request.urlopen(req, timeout=5) as resp:
            data = json.loads(resp.read().decode('utf-8'))
            items = data.get('items', [])
            if items:
                name = items[0].get('name', '')
                PRODUCT_NAME_CACHE[b] = name
                return name
    except Exception as e:
        print(f"Lỗi lookup_product_name_by_barcode cho {b}: {e}")
        
    return ''

def get_headers():
    token = get_kingfood_token()
    return {
        'Authorization': f'Bearer {token}',
        'x-access-token': token,
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
        'Accept': 'application/json, text/plain, */*',
        'Referer': 'https://kdb.kingfood.co/'
    }


def load_branches():
    global BRANCH_CACHE
    if BRANCH_CACHE:
        return BRANCH_CACHE
    try:
        url = 'https://api.kingfood.co/v1/branches?status=1&limit=500'
        req = urllib.request.Request(url, headers=get_headers())
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read().decode('utf-8'))
            BRANCH_CACHE = data.get('items', [])
    except Exception as e:
        print("Lỗi load_branches:", e)
    return BRANCH_CACHE

def find_branch(search_str):
    branches = load_branches()
    s = search_str.strip().upper()
    
    alias_target = STORE_ALIAS_MAP.get(s, s).upper()
    
    # 1. Tìm theo Code
    for b in branches:
        if b.get('code', '').upper() == s or b.get('code', '').upper() == alias_target:
            return b
            
    # 2. Tìm theo Tên
    for b in branches:
        name = b.get('name', '').upper()
        if alias_target in name:
            return b
            
    # 3. Tìm tương đối
    for b in branches:
        name = b.get('name', '').upper()
        if s in name:
            return b
            
    return None

def lookup_pt_kingfood(to_store_code, date_str):
    """
    Tự động tìm Mã Phiếu Chuyển (PT) HÀNG HÓA (LOẠI BỎ THÙNG RỔ)
    TỪ ĐÚNG KHO RAU CỦ (KRC) đến ST ghi nhận dư theo ĐÚNG NGÀY
    """
    if not to_store_code or to_store_code == '---':
        return '---'
        
    branch = find_branch(to_store_code)
    if not branch:
        return '---'
        
    branch_id = branch.get('id')
    
    target_dt = None
    if date_str and date_str != '---':
        for fmt in ('%m/%d/%Y', '%d/%m/%Y', '%Y-%m-%d', '%d.%m', '%d/%m'):
            try:
                target_dt = datetime.strptime(date_str, fmt).date()
                break
            except Exception:
                pass

    try:
        # Lọc nghiêm ngặt: Nơi chuyển = KHO RAU CỦ, Nơi nhận = ST ghi nhận dư, Loại phiếu = transit (hàng hóa)
        url = f'https://api.kingfood.co/v1/transfers?from_branch_id={KRC_BRANCH_ID}&to_branch_id={branch_id}&type=transit&limit=50'
        req = urllib.request.Request(url, headers=get_headers())
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read().decode('utf-8'))
            items = data.get('items', [])
            
        if not items:
            return '---'
            
        matched_pts = []
        for it in items:
            # Loại bỏ hoàn toàn các phiếu thùng rổ (sku <= 2 hoặc type normal)
            sku_count = it.get('sku') or it.get('total_sku') or 0
            if sku_count <= 2 and it.get('type') != 'transit':
                continue
                
            t_date_str = it.get('transfer_date') or it.get('created_at')
            if t_date_str and target_dt:
                try:
                    # Chuyển đổi UTC sang Giờ Việt Nam (+7)
                    t_dt_vn = (datetime.fromisoformat(t_date_str.replace('Z', '+00:00')) + timedelta(hours=7)).date()
                    if t_dt_vn == target_dt:
                        matched_pts.append(it.get('code'))
                except Exception:
                    pass
                    
        if matched_pts:
            return ", ".join(matched_pts)
            
        # Nếu không có chuyến đúng ngày, lấy chuyến hàng hóa gần ngày nhất
        for it in items:
            sku_count = it.get('sku') or it.get('total_sku') or 0
            if sku_count > 2 or it.get('type') == 'transit':
                return it.get('code', '---')
                
        return items[0].get('code', '---')
    except Exception as e:
        print(f"Lỗi lookup_pt_kingfood cho {to_store_code}: {e}")
        return '---'

# KHO XỬ LÝ CHÊNH LỆCH CHUYỂN HÀNG (KCL)
KCL_RAU_ID = '6982f5f1d360600007807f7b'
KCL_ABA_ID = '691189c10be6a5000755e9bc'

KDB_SURPLUS_CACHE = {}

def verify_surplus_in_kdb(surplus_store_str, sku_code, target_date_str=''):
    """
    Quy trình kiểm tra case nhận dư:
    1. Kiểm tra trong phiếu chuyển gốc của ST từ KRC:
       -> Có: "PT gốc [Mã PT] có mã đó (SL: X)"
       -> Không có: "PT gốc: Không có mã"
    2. Kiểm tra trong Thẻ kho KDB xem ST có add dư từ Kho Chênh Lệch không:
       -> Có: "PT bổ sung: [Mã PT] (SL: Y)"
       -> Không có: "ST chưa add dư"
    """
    if not surplus_store_str or surplus_store_str == '---' or not sku_code:
        return {'pt_goc': '---', 'add_du': '---', 'summary': '---'}
        
    cache_key = f"{surplus_store_str}_{sku_code}_{target_date_str}"
    if cache_key in KDB_SURPLUS_CACHE:
        return KDB_SURPLUS_CACHE[cache_key]

    branch = find_branch(surplus_store_str)
    if not branch:
        res = {'pt_goc': f"Không tìm thấy ST {surplus_store_str}", 'add_du': '---', 'summary': f"Không tìm thấy ST {surplus_store_str}"}
        KDB_SURPLUS_CACHE[cache_key] = res
        return res
        
    branch_id = branch.get('id')
    sku = str(sku_code).strip()
    headers = get_headers()
    
    target_dt = None
    if target_date_str and target_date_str != '---':
        for fmt in ('%m/%d/%Y', '%d/%m/%Y', '%Y-%m-%d', '%d.%m', '%d/%m'):
            try:
                target_dt = datetime.strptime(target_date_str, fmt).date()
                break
            except Exception:
                pass

    pt_goc_result = "PT gốc: Không có mã"
    matched_pt_goc_code = None
    
    # BƯỚC 1: Kiểm tra trong phiếu chuyển gốc từ KRC đến ST
    try:
        url_krc = f"https://api.kingfood.co/v1/transfers?from_branch_id={KRC_BRANCH_ID}&to_branch_id={branch_id}&type=transit&limit=15"
        req = urllib.request.Request(url_krc, headers=headers)
        with urllib.request.urlopen(req, timeout=5) as resp:
            data = json.loads(resp.read().decode('utf-8'))
            items = data.get('items', [])
            
        if target_dt:
            def date_score(it):
                t_str = it.get('transfer_date') or it.get('created_at')
                if not t_str: return 999
                try:
                    dt_vn = (datetime.fromisoformat(t_str.replace('Z', '+00:00')) + timedelta(hours=7)).date()
                    return abs((dt_vn - target_dt).days)
                except Exception:
                    return 999
            items.sort(key=date_score)

        for pt in items:
            pt_code = pt.get('code')
            for c in pt.get('container_lines', []):
                for prod in c.get('product_lines', []):
                    bcode = str(prod.get('barcode', '')).strip()
                    sku_val = str(prod.get('sku', '')).strip()
                    if bcode == sku or sku_val == sku or (sku and len(sku) >= 4 and sku in bcode):
                        qty = prod.get('total_transfer_quantity', 0) or prod.get('transfer_quantity', 0)
                        pt_goc_result = f"PT gốc {pt_code} có mã đó (SL: {qty})"
                        matched_pt_goc_code = pt_code
                        break
                if matched_pt_goc_code: break
            if matched_pt_goc_code: break
    except Exception as e:
        print(f"[!] Lỗi check PT gốc KRC: {e}")

    # BƯỚC 2: Kiểm tra Thẻ kho KDB xem có PT bổ sung từ Kho Chênh Lệch không
    add_du_result = "ST chưa add dư"
    matched_kcl_code = None
    try:
        for kcl_id in [KCL_RAU_ID, KCL_ABA_ID]:
            url_kcl = f"https://api.kingfood.co/v1/transfers?from_branch_id={kcl_id}&to_branch_id={branch_id}&limit=10"
            req = urllib.request.Request(url_kcl, headers=headers)
            with urllib.request.urlopen(req, timeout=5) as resp:
                data = json.loads(resp.read().decode('utf-8'))
                kcl_items = data.get('items', [])
                for kcl_pt in kcl_items:
                    kcl_pt_code = kcl_pt.get('code')
                    for c in kcl_pt.get('container_lines', []):
                        for p in c.get('product_lines', []):
                            bcode = str(p.get('barcode', '')).strip()
                            sku_val = str(p.get('sku', '')).strip()
                            if bcode == sku or sku_val == sku or (sku and len(sku) >= 4 and sku in bcode):
                                qty = p.get('total_transfer_quantity', 0) or p.get('transfer_quantity', 0)
                                add_du_result = f"PT bổ sung: {kcl_pt_code} (SL: {qty})"
                                matched_kcl_code = kcl_pt_code
                                break
                        if matched_kcl_code: break
                    if matched_kcl_code: break
            if matched_kcl_code: break
    except Exception as e:
        print(f"[!] Lỗi check Kho Chênh Lệch: {e}")


    summary = f"{pt_goc_result} | {add_du_result}"
    res = {
        'pt_goc': pt_goc_result,
        'add_du': add_du_result,
        'summary': summary
    }
    KDB_SURPLUS_CACHE[cache_key] = res
    return res


