import os
import sys
import time

if sys.platform == 'win32':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
        sys.stderr.reconfigure(encoding='utf-8')
    except Exception:
        pass

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from starrocks_db import check_vpn_and_starrocks, sync_sqlite_to_starrocks

def main():
    print("================================================================")
    print("      KINGFOOD SCM - ĐỒNG BỘ CSDL LÊN STARROCKS (kfm_scm)")
    print("================================================================")
    print("[*] 1. Kiểm tra trạng thái mạng VPN WireGuard và StarRocks...")
    
    status = check_vpn_and_starrocks()
    if not status["success"]:
        print(f"[!] THẤT BẠI: {status.get('error')}")
        print("[!] Vui lòng chạy file KET_NOI_VPN.bat trước khi đồng bộ.")
        sys.exit(1)

    print(f"[*] Kết nối VPN: OK | StarRocks: {status['host']}:{status['port']}")
    print(f"[*] Phiên bản StarRocks: {status['version']} | DB: {status['database']}")
    print(f"[*] Chế độ bảo vệ: {status.get('mode')}")
    print(f"[*] Bảng lưu trữ riêng: {status.get('isolated_tables')}")
    print(f"[*] Số lượng bản ghi hiện tại:")
    for tbl, cnt in status["tables"].items():
        if isinstance(cnt, int):
            print(f"    - {tbl}: {cnt:,} dòng")
        else:
            print(f"    - {tbl}: {cnt}")
    print("----------------------------------------------------------------")
    print("[*] 2. Bắt đầu đẩy dữ liệu từ SQLite (scm_monitor.db) -> StarRocks...")

    t0 = time.time()
    res = sync_sqlite_to_starrocks(limit_messages=2000, limit_discrepancies=5000)
    dur = time.time() - t0

    if res.get("error"):
        print(f"[!] Có lỗi trong quá trình đồng bộ: {res['error']}")
    else:
        print(f"[+] Đồng bộ an toàn hoàn tất trong {dur:.2f}s:")
        print(f"    - Bảng tin nhắn riêng ({status['isolated_tables']['messages']}): +{res.get('messages_synced', 0):,} bản ghi")
        print(f"    - Bảng đối soát riêng ({status['isolated_tables']['discrepancies']}): +{res.get('discrepancies_synced', 0):,} bản ghi")
    print("================================================================")

if __name__ == '__main__':
    main()
