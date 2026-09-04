import sys
import sqlite3
sys.stdout.reconfigure(encoding='utf-8')

conn = sqlite3.connect('scm_monitor.db')
c = conn.cursor()

print("--- AUDIT MESSAGES STATUS ---")
rows = c.execute("""
    SELECT r.msg_id, r.message_text, r.created_at, COALESCE(s.is_checked, 0), COALESCE(s.process_status, 'Chưa có status')
    FROM raw_messages r
    LEFT JOIN audit_case_status s ON r.msg_id = s.msg_id
    WHERE r.chat_title LIKE '%Đối soát%'
    ORDER BY r.id DESC
    LIMIT 10
""").fetchall()

for r in rows:
    msg_id, text, created_at, is_checked, status = r
    first_line = text.split('\n')[0] if text else ''
    print(f"ID: {msg_id} | Created: {created_at} | Checked: {is_checked} | Status: {status} | Line: {first_line[:60]}")
