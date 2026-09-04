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
url = "https://docs.google.com/spreadsheets/d/1WfXxYmuc8gY0BUMMM2lABFUvYkjZjgdbTi3dQBrIpVo/export?format=csv&gid=0"
req = urllib.request.Request(url, headers=headers)
content = urllib.request.urlopen(req, timeout=20).read().decode('utf-8', errors='replace')
rows = list(csv.reader(content.splitlines()))

non_empty = [r for r in rows[2:] if any(c.strip() for c in r)]

print(f"Total non-empty rows: {len(non_empty)}")

# Check rows where 'Tháng Hóa đơn' is empty or where Date is in 2026
for i, r in enumerate(non_empty):
    so_hd = r[7] if len(r) > 7 else ""
    ngay_hd = r[8] if len(r) > 8 else ""
    desc = r[4] if len(r) > 4 else ""
    kho = r[14] if len(r) > 14 else ""
    tien_chua_vat = r[17] if len(r) > 17 else ""
    tong_tien = r[20] if len(r) > 20 else ""
    thang = r[24] if len(r) > 24 else ""
    status = r[23] if len(r) > 23 else ""
    
    # print rows with empty month or month from T05, T06, T07, T08
    if not thang or any(f'T{m:02d}/2026' in thang for m in [5, 6, 7, 8, 9]):
        print(f"Row {i:03d}: HĐ: {so_hd:>6s} | Ngày: {ngay_hd:>10s} | Kho: {kho[:20]:20s} | Chưa VAT: {tien_chua_vat:>14s} | Tổng: {tong_tien:>14s} | Tháng: '{thang}' | Status: '{status}'")
        print(f"       Desc: {desc[:100]}")
