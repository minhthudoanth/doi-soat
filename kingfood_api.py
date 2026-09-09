import urllib.request
import json
import re
from datetime import datetime, timedelta
import sqlite3
import os
from config import DB_PATH

# ================================================================
# KDB ACCESS FLAG: HOÀN TOÀN DỪNG VÀO KDB THEO YÊU CẦU
# ================================================================
ENABLE_KDB_ACCESS = False

DEFAULT_KINGFOOD_TOKEN = ""

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
    'VH7': 'Vinhomes',
    'HMN': 'Harmona',
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
    'NTD': '160A Nguyễn Thị Định',
    'A232': '376 Nguyễn Thị Định',
    'TNH': 'Thống Nhất',
    'BQU': 'Bình Quới',
    'LTC': 'Lê Thị Chợ',
    'PTH': 'Phú Thuận',
    'TMY': 'Tân Mỹ',
    'HHT': '22 Hoàng Hoa Thám',
    'HHM': '165 Hoàng Hoa Thám',
    'NTT': 'Nguyễn Thị Thập',
    'VHT': 'Vũ Huy Tấn',
    'BBA': 'Bùi Văn Ba',
    'NHG': 'Nguyên Hồng',
    'KHO': 'Khánh Hội',
    'NVT': 'Nguyễn Văn Tăng',
    'THD': 'Tân Hòa Đông',
    'THĐ': 'Tân Hòa Đông',
    'CKE': 'Cây Keo',
    'LVL': 'Lê Văn Lương',
    'LVB': 'Lâm Văn Bền',
    'NDT': '305 Nguyễn Duy Trinh',
    'NDH': '1426 Nguyễn Duy Trinh',
    'A187': '560 Nguyễn Duy Trinh',
    'A204': '67A Nguyễn Duy Trinh',
    'GLD': 'Golden Star'
}



PRODUCT_NAME_CACHE = {}

def lookup_product_name_by_barcode(barcode):
    """
    Tra cứu tên sản phẩm (đã tắt truy cập KDB theo yêu cầu)
    """
    return ''

def get_headers():
    token = get_kingfood_token()
    return {
        'Authorization': f'Bearer {token}',
        'x-access-token': token,
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
        'Accept': 'application/json, text/plain, */*'
    }


def load_branches():
    global BRANCH_CACHE
    if BRANCH_CACHE:
        return BRANCH_CACHE
    # Đọc danh sách chi nhánh từ SQLite nội bộ thay vì gọi KDB
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("SELECT store_name, store_id FROM sheet_store_list")
        rows = cursor.fetchall()
        conn.close()
        BRANCH_CACHE = [{'name': r[0], 'code': r[1], 'name_abbreviate': r[1], 'id': r[1]} for r in rows]
    except Exception as e:
        print("Lỗi load_branches từ SQLite:", e)
        BRANCH_CACHE = []
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
    Đã tắt truy cập KDB theo yêu cầu.
    """
    return '---'

# KHO XỬ LÝ CHÊNH LỆCH CHUYỂN HÀNG (KCL)
KCL_RAU_ID = '6982f5f1d360600007807f7b'
KCL_ABA_ID = '691189c10be6a5000755e9bc'

KDB_SURPLUS_CACHE = {}

def verify_surplus_in_kdb(surplus_store_str, sku_code, target_date_str=''):
    """
    Đã tắt truy cập KDB theo yêu cầu người dùng.
    """
    return {'pt_goc': '---', 'add_du': '---', 'summary': '---'}


