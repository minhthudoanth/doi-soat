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
dst = 'temp_p6_drive_all.db'
shutil.copy2(profile_history, dst)
conn = sqlite3.connect(dst)
c = conn.cursor()

print("=== ALL DRIVE FOLDERS & FILES IN PROFILE 6 ===")
c.execute("""
    SELECT DISTINCT title, url
    FROM urls
    WHERE url LIKE '%drive.google.com%' OR url LIKE '%docs.google.com%'
    ORDER BY last_visit_time DESC
    LIMIT 60
""")
for r in c.fetchall():
    print(f"- [{r[0]}]\n  {r[1]}")

conn.close()
os.remove(dst)
