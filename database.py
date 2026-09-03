import sqlite3
from datetime import datetime
from config import DB_PATH

def get_optimized_conn():
    conn = sqlite3.connect(DB_PATH, timeout=30)
    conn.execute("PRAGMA journal_mode = WAL;")
    conn.execute("PRAGMA synchronous = NORMAL;")
    conn.execute("PRAGMA cache_size = -64000;") # 64MB cache
    conn.execute("PRAGMA temp_store = MEMORY;")
    return conn

def init_db():
    conn = get_optimized_conn()
    cursor = conn.cursor()
    
    # Bảng lưu toàn bộ tin nhắn
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS raw_messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            msg_id INTEGER,
            chat_id INTEGER,
            chat_title TEXT,
            sender_id INTEGER,
            sender_name TEXT,
            username TEXT,
            message_text TEXT,
            category TEXT,
            priority TEXT,
            issue_type TEXT,
            reply_to_msg_id INTEGER DEFAULT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            is_read INTEGER DEFAULT 0,
            is_dismissed INTEGER DEFAULT 0
        )
    """)
    try:
        cursor.execute("ALTER TABLE raw_messages ADD COLUMN reply_to_msg_id INTEGER DEFAULT NULL")
    except Exception:
        pass

    
    # Bảng theo dõi các Case cần xử lý (P1, P2)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS priority_cases (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            msg_id INTEGER,
            chat_title TEXT,
            sender_name TEXT,
            category TEXT,
            priority TEXT,
            content TEXT,
            status TEXT DEFAULT 'Chờ xử lý',
            note TEXT DEFAULT '',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            is_read INTEGER DEFAULT 0,
            is_dismissed INTEGER DEFAULT 0
        )
    """)

    # Bảng lưu trạng thái Check & Xử lý của các case Đối Soát
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS audit_case_status (
            msg_id INTEGER PRIMARY KEY,
            is_checked INTEGER DEFAULT 0,
            process_status TEXT DEFAULT 'Chờ xử lý',
            note TEXT DEFAULT '',
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # Bảng lưu lịch sử các tin nhắn gửi tự động đến ST để hỗ trợ thu hồi tin nhắn
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS sent_broadcast_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            batch_id TEXT,
            chat_id INTEGER,
            chat_title TEXT,
            msg_id INTEGER,
            message_text TEXT,
            is_recalled INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_broadcast_batch ON sent_broadcast_history (batch_id, is_recalled);")

    # Indexes tối ưu hóa tốc độ truy vấn
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_raw_chat_title ON raw_messages (chat_title);")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_raw_created_at ON raw_messages (created_at);")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_raw_msg_chat ON raw_messages (msg_id, chat_id);")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_raw_sender ON raw_messages (sender_name);")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_priority_status ON priority_cases (status, is_read, is_dismissed);")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_priority_chat ON priority_cases (chat_title);")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_audit_status ON audit_case_status (process_status, is_checked);")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_sheet_date_st ON sheet_audit_records (transfer_date, store_id);")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_sheet_error_date ON sheet_audit_records (error_type, transfer_date);")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_sheet_sku ON sheet_audit_records (sku_code);")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_inv_date_st ON store_inventory_records (date, store_id);")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_inv_category ON store_inventory_records (category_name);")
    
    conn.commit()
    conn.close()



def save_message(msg_id, chat_id, chat_title, sender_id, sender_name, username, text, category, priority):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    cursor.execute("""
        INSERT INTO raw_messages (msg_id, chat_id, chat_title, sender_id, sender_name, username, message_text, category, priority)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (msg_id, chat_id, chat_title, sender_id, sender_name, username, text, category, priority))
    
    if "P1" in priority or "P2" in priority:
        cursor.execute("""
            INSERT INTO priority_cases (msg_id, chat_title, sender_name, category, priority, content, status)
            VALUES (?, ?, ?, ?, ?, ?, 'Chờ xử lý')
        """, (msg_id, chat_title, sender_name, category, priority, text))
        
    conn.commit()
    conn.close()

def get_recent_cases(limit=10, p1_only=False):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    query = "SELECT id, chat_title, sender_name, category, priority, content, status, created_at FROM priority_cases WHERE status = 'Chờ xử lý'"
    if p1_only:
        query += " AND priority LIKE '%P1%'"
    query += " ORDER BY id DESC LIMIT ?"
    
    cursor.execute(query, (limit,))
    rows = cursor.fetchall()
    conn.close()
    return rows

def get_stats_today():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT category, COUNT(*) FROM raw_messages 
        WHERE DATE(created_at) = DATE('now', 'localtime')
        GROUP BY category
    """)
    cat_stats = cursor.fetchall()
    
    cursor.execute("""
        SELECT priority, COUNT(*) FROM raw_messages 
        WHERE DATE(created_at) = DATE('now', 'localtime')
        GROUP BY priority
    """)
    pri_stats = cursor.fetchall()
    
    conn.close()
    return cat_stats, pri_stats
