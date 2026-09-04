import urllib.request
import csv
import io
import sys
import re

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
print(f"Total rows: {len(non_empty)}")

# Group by Date or Description to understand what periods/months are present
dates = {}
invoices = {}

for r in non_empty:
    doc_type = r[0].strip()
    ref_nbr = r[1].strip()
    date_val = r[2].strip()
    desc = r[4].strip()
    so_hd = r[7].strip()
    ngay_hd = r[8].strip()
    kho = r[14].strip()
    tax_rate = r[18].strip()
    pre_tax = r[17].strip()
    post_tax = r[20].strip()
    month_col = r[24].strip() if len(r) > 24 else ""
    
    # Extract date year / month
    # Find invoice numbers
    if so_hd:
        if so_hd not in invoices:
            invoices[so_hd] = {
                'ngay_hd': ngay_hd,
                'desc': desc,
                'kho': kho,
                'month_col': month_col,
                'items': []
            }
        invoices[so_hd]['items'].append({
            'pre_tax': pre_tax,
            'tax_rate': tax_rate,
            'post_tax': post_tax
        })

print(f"\nTotal unique Hóa đơn (Số HD): {len(invoices)}")
print("\nList of all unique Hóa đơn:")
for so_hd, inv in sorted(invoices.items(), key=lambda x: x[1]['ngay_hd']):
    total_pre = sum(float(it['pre_tax'].replace(',', '')) for it in inv['items'] if it['pre_tax'])
    total_post = sum(float(it['post_tax'].replace(',', '')) for it in inv['items'] if it['post_tax'])
    print(f"HĐ: {so_hd:>6s} | Ngày: {inv['ngay_hd']:>10s} | Tháng: '{inv['month_col']}' | Kho: {inv['kho'][:25]:25s} | Chưa VAT: {total_pre:>13,.0f} | Gồm VAT: {total_post:>13,.0f} | {len(inv['items'])} dòng")
    print(f"    Desc: {inv['desc'][:110]}")
