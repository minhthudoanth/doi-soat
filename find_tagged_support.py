import os
import sys

if sys.platform == 'win32':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
        sys.stderr.reconfigure(encoding='utf-8')
    except Exception:
        pass

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

import sqlite3
from config import DB_PATH

def find_tagged():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Tìm các tin nhắn có tag @minhthudoan hoặc gọi Thư nhờ hỗ trợ/giúp
    query = """
        SELECT id, chat_title, sender_name, message_text, created_at
        FROM raw_messages
        WHERE (
            message_text LIKE '%minhthudoan%' 
            OR message_text LIKE '%@minhthudoan%'
            OR message_text LIKE '%8552986824%'
            OR (
                (message_text LIKE '%thư%' OR message_text LIKE '%thu %' OR message_text LIKE '%chị thư%' OR message_text LIKE '%c thư%')
                AND (message_text LIKE '%hỗ trợ%' OR message_text LIKE '%giúp%' OR message_text LIKE '%nhờ%' OR message_text LIKE '%check%' OR message_text LIKE '%xử lý%' OR message_text LIKE '%duyệt%')
            )
        )
        AND sender_name NOT LIKE '%Thư Đoàn%'
        ORDER BY id DESC
    """
    cursor.execute(query)
    rows = cursor.fetchall()
    
    print(f"================================================================")
    print(f" >>> TÌM THẤY {len(rows)} TIN NHẮN ST TAG @minhthudoan / NHỜ HỖ TRỢ:")
    print(f"================================================================")
    for r in rows:
        print(f"[{r[4]}] #{r[0]} [{r[1]}] {r[2]}:")
        print(f"   👉 {r[3]}\n")
        
    conn.close()

if __name__ == "__main__":
    find_tagged()
