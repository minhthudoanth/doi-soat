import os
import sys

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

import sqlite3
from config import DB_PATH
from classifier import is_auto_or_broadcast

def cleanup():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    cursor.execute("SELECT id, content, sender_name FROM priority_cases")
    rows = cursor.fetchall()
    
    deleted_count = 0
    for case_id, content, sender_name in rows:
        if is_auto_or_broadcast(content, sender_name):
            cursor.execute("DELETE FROM priority_cases WHERE id = ?", (case_id,))
            deleted_count += 1
            
    conn.commit()
    
    # Cập nhật raw_messages category cho các tin tự động
    cursor.execute("SELECT id, message_text, sender_name FROM raw_messages")
    raw_rows = cursor.fetchall()
    updated_raw = 0
    for r_id, msg_text, sender_name in raw_rows:
        if is_auto_or_broadcast(msg_text, sender_name):
            cursor.execute("UPDATE raw_messages SET category = 'Thông Báo / Quy Trình', priority = '🟢 P3 - Thông tin' WHERE id = ?", (r_id,))
            updated_raw += 1
            
    conn.commit()
    
    cursor.execute("SELECT COUNT(*) FROM priority_cases")
    remaining_cases = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(*) FROM priority_cases WHERE category LIKE '%KRC%' OR category LIKE '%Đối soát%'")
    krc_remaining = cursor.fetchone()[0]
    
    conn.close()
    
    print("================================================================")
    print(" >>> DA LOC VA LOAI BO TOAN BO TIN NHAN NHAC NHO TU DONG:")
    print(f" [+] So case tu dong da xoa khoi bang Uu tien: {deleted_count}")
    print(f" [+] So tin nhan tu dong da chuyen ve nhom Thong Bao: {updated_raw}")
    print(f" [+] So case thuc te can xu ly con lai: {remaining_cases}")
    print(f" [+] So case KRC - Doi soat thuc te: {krc_remaining}")
    print("================================================================")

if __name__ == "__main__":
    cleanup()
