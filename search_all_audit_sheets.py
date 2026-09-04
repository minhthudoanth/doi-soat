import os
import sys
import shutil
import sqlite3

if sys.platform == 'win32':
    try:
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    except Exception:
        pass

profile_history = os.path.expandvars(r'%LOCALAPPDATA%\Google\Chrome\User Data\Profile 6\History')
dst = 'temp_p6_audit_sheets.db'
shutil.copy2(profile_history, dst)
conn = sqlite3.connect(dst)
c = conn.cursor()

print("=== ALL 'Đối Soát Kho Rau' OR RECONCILIATION SHEETS IN PROFILE 6 ===")
c.execute("""
    SELECT id, url, title, datetime(last_visit_time/1000000-11644473600, 'unixepoch', 'localtime') as visit_time
    FROM urls
    WHERE title LIKE '%Đối Soát%' OR title LIKE '%Chênh lệch%' OR url LIKE '%spreadsheets%'
    ORDER BY last_visit_time DESC
    LIMIT 100
""")
for r in c.fetchall():
    if any(k in r[2].lower() for k in ['đối soát', 'chênh lệch', 'rau', 'tháng', 'ghknn', 'kho']):
        print(f"[{r[3]}] {r[2]}\n   {r[1]}")

conn.close()
os.remove(dst)
