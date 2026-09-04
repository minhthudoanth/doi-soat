import sys
if sys.platform == 'win32':
    try:
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    except Exception:
        pass
import urllib.request
import csv
import io
import re

headers = {'User-Agent': 'Mozilla/5.0'}

def inspect_sheet(label, sid, gid=0):
    print(f"\n{'='*20} {label} ({sid}, gid={gid}) {'='*20}")
    url = f"https://docs.google.com/spreadsheets/d/{sid}/export?format=csv&gid={gid}"
    try:
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req, timeout=20) as resp:
            content = resp.read().decode('utf-8', errors='replace')
            lines = content.splitlines()
            print(f"Total lines: {len(lines)}")
            reader = csv.reader(lines)
            rows = list(reader)
            for i, r in enumerate(rows[:25]):
                print(f"Row {i:02d}: {r}")
            if len(rows) > 25:
                print("...")
                for i in range(max(25, len(rows)-5), len(rows)):
                    print(f"Row {i:02d}: {rows[i]}")
            return rows
    except Exception as e:
        print(f"Error inspecting {label}: {e}")
        return None

# 1. Source invoice sheet
src_rows = inspect_sheet("Source Invoices (1YfpVHQbowoSj6lN...)", "1YfpVHQbowoSj6lN-8KW0d1UmCKy4sy2PesB7g9yNG4M", 0)

# 2. Target spreadsheet sent by user
target_rows = inspect_sheet("Target Google Sheet (1WfXxYmuc8gY0BUMMM2lABFUvYkjZjgdbTi3dQBrIpVo)", "1WfXxYmuc8gY0BUMMM2lABFUvYkjZjgdbTi3dQBrIpVo", 0)
