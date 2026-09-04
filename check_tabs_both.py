import urllib.request
import re
import sys

if sys.platform == 'win32':
    try:
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    except Exception:
        pass

headers = {'User-Agent': 'Mozilla/5.0'}

def get_tabs(sid, label):
    print(f"\n{'='*20} Tabs in {label} ({sid}) {'='*20}")
    url = f"https://docs.google.com/spreadsheets/d/{sid}/edit"
    try:
        req = urllib.request.Request(url, headers=headers)
        html = urllib.request.urlopen(req, timeout=15).read().decode('utf-8', errors='ignore')
        # Check sheet tabs
        tabs = re.findall(r'(\d{1,10}),0,"([^"]+)"', html)
        if tabs:
            print(f"Found {len(tabs)} tabs via pattern 1:")
            for gid, name in tabs:
                print(f"  - GID: {gid} | Name: '{name}'")
        else:
            tabs2 = re.findall(r'"name":"([^"]+)".*?"sheetId":(\d+)', html)
            if tabs2:
                print(f"Found {len(tabs2)} tabs via pattern 2:")
                for name, gid in tabs2:
                    print(f"  - GID: {gid} | Name: '{name}'")
            else:
                # search for gids
                gids = set(re.findall(r'gid=(\d+)', html))
                print("Found gids:", gids)
    except Exception as e:
        print("Error:", e)

get_tabs("1YfpVHQbowoSj6lN-8KW0d1UmCKy4sy2PesB7g9yNG4M", "Source Invoice Sheet")
get_tabs("1WfXxYmuc8gY0BUMMM2lABFUvYkjZjgdbTi3dQBrIpVo", "Target Sheet (SCF thanh toan KFM)")
