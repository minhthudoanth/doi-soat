import urllib.request
import csv
import io
import sys

if sys.platform == 'win32':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

url = 'https://docs.google.com/spreadsheets/d/1ve3IoARSwWmAv_Gz6O8wAJ1YXuNWJNEpQVR7R3iPm-s/export?format=csv&gid=441247078'
req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
content = urllib.request.urlopen(req).read().decode('utf-8', errors='ignore')

reader = csv.reader(io.StringIO(content))
rows = list(reader)
print(f"Total rows in Link_Tong: {len(rows)}")
for i, r in enumerate(rows[:25]):
    print(f"Row {i}: {r}")
