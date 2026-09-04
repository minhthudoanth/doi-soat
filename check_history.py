import os
import sys
import shutil
import sqlite3

if sys.platform == 'win32':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

src = os.path.expandvars(r'%LOCALAPPDATA%\Google\Chrome\User Data\Default\History')
dst = 'temp_history.db'

try:
    shutil.copy2(src, dst)
    conn = sqlite3.connect(dst)
    c = conn.cursor()
    c.execute("""
        SELECT url, title, datetime(last_visit_time/1000000-11644473600, 'unixepoch', 'localtime') as visit_time
        FROM urls 
        WHERE url LIKE '%drive.google.com%' OR url LIKE '%docs.google.com%'
        ORDER BY last_visit_time DESC 
        LIMIT 40
    """)
    rows = c.fetchall()
    conn.close()
    for row in rows:
        url, title, vtime = row
        print(f"[{vtime}] {title} --> {url}")
except Exception as e:
    print("Error:", e)
finally:
    try:
        if os.path.exists(dst):
            os.remove(dst)
    except Exception:
        pass
