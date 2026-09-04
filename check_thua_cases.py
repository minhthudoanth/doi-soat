import sys
import sqlite3
from app import parse_full_audit

sys.stdout.reconfigure(encoding='utf-8')
conn = sqlite3.connect('scm_monitor.db')
c = conn.cursor()
c.execute("""
    SELECT message_text, created_at FROM raw_messages 
    WHERE chat_title = 'SCM - KRC (Đối soát)'
    AND sender_name NOT LIKE '%Thư Đoàn%'
    AND sender_name NOT LIKE '%SC017084%'
""")
rows = c.fetchall()
thua_cases = []
for text, created_at in rows:
    p = parse_full_audit(text, created_at)
    if p.get('issue_type') == 'Thừa' and p.get('st_du') and p.get('st_du') != '---':
        thua_cases.append((p.get('st_du'), p.get('sku_code'), p.get('date')))

print(f'Total Thừa cases with st_du: {len(thua_cases)}')
for item in thua_cases[:10]:
    print(item)
