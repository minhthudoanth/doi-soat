import urllib.request
import csv
import io
import sys

if sys.platform == 'win32':
    try:
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    except Exception:
        pass

headers = {'User-Agent': 'Mozilla/5.0'}
url = "https://docs.google.com/spreadsheets/d/1YfpVHQbowoSj6lN-8KW0d1UmCKy4sy2PesB7g9yNG4M/export?format=csv&gid=0"
req = urllib.request.Request(url, headers=headers)
content = urllib.request.urlopen(req, timeout=20).read().decode('utf-8', errors='replace')
rows = list(csv.reader(content.splitlines()))

print(f"Total rows in src_rows: {len(rows)}")
for i, r in enumerate(rows):
    print(f"Row {i:02d}: {r}")
