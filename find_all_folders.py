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

dst = 'temp_folders_only.db'
folders_found = {}

for hf in history_files:
    try:
        shutil.copy2(hf, dst)
        conn = sqlite3.connect(dst)
        c = conn.cursor()
        c.execute("""
            SELECT url, title, datetime(last_visit_time/1000000-11644473600, 'unixepoch', 'localtime') as vt
            FROM urls
            WHERE url LIKE '%drive.google.com/drive/folders/%'
            ORDER BY last_visit_time DESC
        """)
        for url, title, vt in c.fetchall():
            m = re.search(r'/drive/folders/([a-zA-Z0-9-_]+)', url)
            if not m: continue
            fid = m.group(1)
            t = (title or '').strip()
            if fid not in folders_found or vt > folders_found[fid]['vt']:
                folders_found[fid] = {'title': t, 'url': f'https://drive.google.com/drive/folders/{fid}?hl=vi', 'vt': vt, 'source': hf}
        conn.close()
    except Exception:
        pass
    finally:
        if os.path.exists(dst):
            try: os.remove(dst)
            except: pass

print(f"=== ALL GOOGLE DRIVE FOLDERS FOUND ({len(folders_found)}) ===")
for fid, info in sorted(folders_found.items(), key=lambda x: x[1]['vt'], reverse=True):
    print(f"[{info['vt']}] {info['title']}\n  ID: {fid}\n  URL: {info['url']}\n")
