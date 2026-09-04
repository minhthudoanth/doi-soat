import os
import sys
import shutil
import sqlite3
import re

if sys.platform == 'win32':
    try:
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    except Exception:
        pass

user_dir = os.path.expanduser('~')
chrome_ud = os.path.join(user_dir, r'AppData\Local\Google\Chrome\User Data')
edge_ud = os.path.join(user_dir, r'AppData\Local\Microsoft\Edge\User Data')

history_files = []
for base in [chrome_ud, edge_ud]:
    if not os.path.exists(base): continue
    for root, dirs, files in os.walk(base):
        if 'History' in files and 'Cache' not in root and 'Network' not in root:
            history_files.append(os.path.join(root, 'History'))

dst = 'temp_sheets_only.db'

# We want Google Sheets related to Đối Soát, Kho Rau, Chênh lệch
sheets_found = {}

for hf in history_files:
    try:
        shutil.copy2(hf, dst)
        conn = sqlite3.connect(dst)
        c = conn.cursor()
        c.execute("""
            SELECT url, title, datetime(last_visit_time/1000000-11644473600, 'unixepoch', 'localtime') as vt
            FROM urls
            WHERE url LIKE '%docs.google.com/spreadsheets/d/%'
            ORDER BY last_visit_time DESC
        """)
        for url, title, vt in c.fetchall():
            m = re.search(r'/spreadsheets/d/([a-zA-Z0-9-_]+)', url)
            if not m: continue
            sid = m.group(1)
            t = (title or '').strip()
            if not t or t.startswith('http'): continue
            
            # Filter for relevant sheets
            t_low = t.lower()
            if any(k in t_low for k in ['rau', 'đối soát', 'chênh lệch', 'krc', 'tháng', 'ghknn', 'kho']):
                if sid not in sheets_found or vt > sheets_found[sid]['vt']:
                    sheets_found[sid] = {'title': t, 'url': f'https://docs.google.com/spreadsheets/d/{sid}/edit', 'vt': vt, 'source': hf}
        conn.close()
    except Exception as e:
        pass
    finally:
        if os.path.exists(dst):
            try: os.remove(dst)
            except: pass

print(f"=== ALL RELEVANT GOOGLE SHEETS FOUND ({len(sheets_found)}) ===")
# Sort by title
for sid, info in sorted(sheets_found.items(), key=lambda x: x[1]['title']):
    print(f"[{info['vt']}] {info['title']}\n  ID: {sid}\n  URL: {info['url']}\n")
