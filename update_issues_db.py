import sqlite3
import os
import sys

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)
if sys.platform == 'win32':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass



from config import DB_PATH
from classifier import classify_message, is_group_excluded

def update_db():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    cursor.execute("SELECT id, message_text, chat_title, sender_name FROM raw_messages")
    rows = cursor.fetchall()
    
    cursor.execute("DELETE FROM priority_cases")
    
    stats = {
        "Thiếu": 0,
        "Thừa": 0,
        "XCL": 0,
        "Sự cố Tài xế": 0
    }
    
    for r_id, text, chat_title, sender_name in rows:
        if is_group_excluded(chat_title):
            continue
            
        res = classify_message(text, sender_name, chat_title)
        if not res:
            continue
            
        category = res["category"]
        priority = res["priority"]
        issue_type = res["issue_type"]
        
        if issue_type == "Khác":
            continue
            
        cursor.execute("UPDATE raw_messages SET category = ?, priority = ?, issue_type = ? WHERE id = ?", (category, priority, issue_type, r_id))
        
        if issue_type in ["Thiếu", "Thừa", "XCL", "Sự cố Tài xế"]:
            cursor.execute("""
                INSERT INTO priority_cases (msg_id, chat_title, sender_name, category, priority, content, status, issue_type)
                VALUES (?, ?, ?, ?, ?, ?, 'Chờ xử lý', ?)
            """, (r_id, chat_title, sender_name, category, priority, text, issue_type))
            
            stats[issue_type] += 1
            
    conn.commit()
    conn.close()
    
    print("================================================================")
    print(" >>> ĐÃ PHÂN LOẠI LẠI TOÀN BỘ CASE SỰ CỐ CHUẨN XÁC:")
    print(f" [+] Thiếu: {stats['Thiếu']} case")
    print(f" [+] Thừa: {stats['Thừa']} case")
    print(f" [+] XCL (Bể/vỡ/nứt/dập): {stats['XCL']} case")
    print(f" [+] Sự cố Tài xế / Vận hành: {stats['Sự cố Tài xế']} case")
    print("================================================================")

if __name__ == '__main__':
    update_db()
