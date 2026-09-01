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


def inspect():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT id, chat_title, sender_name, issue_type, content FROM priority_cases ORDER BY RANDOM() LIMIT 25")
    rows = cursor.fetchall()
    for r in rows:
        print(f"#{r[0]} [{r[3]}] [{r[1]}] {r[2]}:\n   {r[4]}\n")
    conn.close()

if __name__ == "__main__":
    inspect()
