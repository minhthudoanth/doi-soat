import sys
if sys.platform == 'win32':
    try:
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    except Exception:
        pass
import urllib.request
import csv
import io

headers = {'User-Agent': 'Mozilla/5.0'}

def get_rows(sid, gid=0):
    url = f"https://docs.google.com/spreadsheets/d/{sid}/export?format=csv&gid={gid}"
    req = urllib.request.Request(url, headers=headers)
    content = urllib.request.urlopen(req, timeout=20).read().decode('utf-8', errors='replace')
    return list(csv.reader(content.splitlines()))

print("=== 1. SOURCE INVOICE FILE (1YfpVHQbowoSj6lN-8KW0d1UmCKy4sy2PesB7g9yNG4M) ===")
src_rows = get_rows("1YfpVHQbowoSj6lN-8KW0d1UmCKy4sy2PesB7g9yNG4M", 0)
print(f"Total rows in src: {len(src_rows)}")
for i, r in enumerate(src_rows[:15]):
    print(f"Row {i:02d}: {r}")

print("\n=== 2. TARGET FILE (1WfXxYmuc8gY0BUMMM2lABFUvYkjZjgdbTi3dQBrIpVo) ===")
tgt_rows = get_rows("1WfXxYmuc8gY0BUMMM2lABFUvYkjZjgdbTi3dQBrIpVo", 0)
print(f"Total rows in tgt: {len(tgt_rows)}")
for i, r in enumerate(tgt_rows[:15]):
    print(f"Row {i:02d}: {r}")
