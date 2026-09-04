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


import sqlite3, sys

if sys.platform == 'win32':
    try:
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    except Exception:
        pass

conn = sqlite3.connect('scm_monitor.db')
c = conn.cursor()
import sqlite3, sys

if sys.platform == 'win32':
    try:
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    except Exception:
        pass

import sys
if sys.platform == 'win32':
    try:
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    except Exception:
        pass

import sqlite3

conn = sqlite3.connect('scm_monitor.db')
c = conn.cursor()
c.execute("SELECT store_id, store_name FROM sheet_store_list ORDER BY store_id ASC")
rows = c.fetchall()
print(f"Total stores in sheet_store_list: {len(rows)}")
for r in rows[:20]:
    print(r)







