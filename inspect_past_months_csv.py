import urllib.request
import csv
import io
import sys

if sys.platform == 'win32':
    try:
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    except Exception:
        pass

sheets = {
    'T05 (Thang 05.2026)': '1suHerEzgKzxB7g1UbrGIZPNaxK5a96xFnmxcIQywpko',
    'T06 (Thang 06.2026)': '1065akVGAsBNjONniCS6ccU_mmsRFXb663_Qms8U053Q',
    'T07 (Thang 07.2026)': '1wdbowphojL8YULVlPwDHK-hofacdt6J5K_PFZbWz-as',
    'T08 (Thang 08.2026)': '1vPHHrZf5prEgE_09j_RbQQC1gNWhUmV0Q6aah6Z3mjQ'
}

for label, sid in sheets.items():
    print(f"\n==================== {label} ====================")
    url = f"https://docs.google.com/spreadsheets/d/{sid}/export?format=csv&gid=1422896115"
    try:
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        content = urllib.request.urlopen(req, timeout=30).read().decode('utf-8', errors='ignore')
        rows = list(csv.reader(io.StringIO(content)))
        print(f"Total rows: {len(rows)}")
        if len(rows) > 2:
            print("Header (row 2):", rows[2][:15])
            print("First data row (row 3):", rows[3][:15])
            print("Last data row:", rows[-1][:15])
            
            # Find date column index
            header = rows[2]
            date_idx = None
            for idx, col in enumerate(header):
                if 'ngày' in col.lower():
                    date_idx = idx
                    break
            if date_idx is not None:
                dates = [r[date_idx].strip() for r in rows[3:] if len(r) > date_idx and r[date_idx].strip()]
                unique_dates = sorted(list(set(dates)))
                print(f"Date range: min={unique_dates[0] if unique_dates else None} -> max={unique_dates[-1] if unique_dates else None} (distinct dates: {len(unique_dates)})")
    except Exception as e:
        print(f"Error {label}: {e}")
