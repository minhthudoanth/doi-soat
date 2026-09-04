import urllib.request
import csv
import sys

if sys.platform == 'win32':
    try:
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    except Exception:
        pass

url = "https://docs.google.com/spreadsheets/d/1WfXxYmuc8gY0BUMMM2lABFUvYkjZjgdbTi3dQBrIpVo/export?format=csv&gid=0"
req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
content = urllib.request.urlopen(req, timeout=20).read().decode('utf-8', errors='replace')
rows = list(csv.reader(content.splitlines()))

non_empty = [r for r in rows[2:] if any(c.strip() for c in r)]

empty_month_invoices = {}
for idx, r in enumerate(non_empty):
    so_hd = r[7].strip() if len(r) > 7 else ""
    thang = r[24].strip() if len(r) > 24 else ""
    ngay_hd = r[8].strip() if len(r) > 8 else ""
    desc = r[4].strip() if len(r) > 4 else ""
    kho = r[14].strip() if len(r) > 14 else ""
    tien_chua_vat = float(r[17].replace(',', '') or 0) if len(r) > 17 else 0.0
    tien_gom_vat = float(r[20].replace(',', '') or 0) if len(r) > 20 else 0.0
    
    if not thang:
        if so_hd not in empty_month_invoices:
            empty_month_invoices[so_hd] = {
                'row_start': idx + 3,
                'ngay_hd': ngay_hd,
                'kho': kho,
                'desc': desc,
                'chua_vat': 0.0,
                'gom_vat': 0.0,
                'count': 0
            }
        empty_month_invoices[so_hd]['chua_vat'] += tien_chua_vat
        empty_month_invoices[so_hd]['gom_vat'] += tien_gom_vat
        empty_month_invoices[so_hd]['count'] += 1

print(f"Total invoices with EMPTY 'Tháng Hóa đơn': {len(empty_month_invoices)}")
for so_hd, data in sorted(empty_month_invoices.items(), key=lambda x: (x[1]['ngay_hd'], x[0])):
    print(f"\nHĐ: {so_hd} | Ngày: {data['ngay_hd']} | Kho: {data['kho']}")
    print(f"   Dòng: {data['count']} | Chưa VAT: {data['chua_vat']:,.0f} | Gồm VAT: {data['gom_vat']:,.0f}")
    print(f"   Desc: {data['desc']}")
