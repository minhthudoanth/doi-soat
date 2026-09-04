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
    if not os.path.exists(base):
        continue
    for root, dirs, files in os.walk(base):
        if 'History' in files:
            fp = os.path.join(root, 'History')
            # avoid nested cache directories
            if 'Cache' not in fp and 'Network' not in fp:
                history_files.append(fp)

print(f"Found {len(history_files)} History files:")
for h in history_files:
    print(" ", h)

dst = 'temp_search_all_histories.db'

keywords = [
    'rau', 'đối soát', 'chênh lệch', 'kho rau', 'krc',
    'tháng 11', 'tháng 12', 'tháng 10', 'tháng 1', 'tháng 2', 'tháng 3', 'tháng 4', 'tháng 5', 'tháng 6',
    't11', 't12', 't10', 't1', 't2', 't3', 't4', 't5', 't6',
    '11.2025', '12.2025', '01.2026', '02.2026', '03.2026', '04.2026', '05.2026', '06.2026',
    '11/2025', '12/2025', '01/2026', '02/2026', '03/2026', '04/2026', '05/2026', '06/2026'
]

found_items = {}

for hf in history_files:
    try:
        shutil.copy2(hf, dst)
        conn = sqlite3.connect(dst)
        c = conn.cursor()
        c.execute("""
            SELECT url, title, datetime(last_visit_time/1000000-11644473600, 'unixepoch', 'localtime') as vt
            FROM urls
            WHERE url LIKE '%docs.google.com/spreadsheets%' OR url LIKE '%drive.google.com%'
            ORDER BY last_visit_time DESC
        """)
        for url, title, vt in c.fetchall():
            title_lower = (title or '').lower()
            url_lower = (url or '').lower()
            if any(k in title_lower or k in url_lower for k in keywords):
                # Clean URL (strip gid/edit hash for unique spreadsheet ID if applicable)
                m = re.search(r'/spreadsheets/d/([a-zA-Z0-9-_]+)', url)
                sid = m.group(1) if m else url
                if sid not in found_items:
                    found_items[sid] = {'title': title, 'url': url, 'vt': vt, 'source': hf}
        conn.close()
    except Exception as e:
        print(f"Error reading {hf}: {e}")
    finally:
        if os.path.exists(dst):
            try: os.remove(dst)
            except: pass

print(f"\nFound {len(found_items)} matching spreadsheets/drives:")
for k, v in found_items.items():
    print(f"[{v['vt']}] {v['title']}\n  URL: {v['url']}\n  From: {v['source']}\n")
