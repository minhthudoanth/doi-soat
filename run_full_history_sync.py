import urllib.request
import csv
import io
import sys
import sqlite3
import os

if sys.platform == 'win32':
    try:
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    except Exception:
        pass

from config import DB_PATH
from sheet_sync import init_sheet_db, parse_num, sync_ds_st_data

SHEET_CONFIGS = [
    {
        'id': 'T05_2026',
        'name': 'Đối Soát Kho Rau tháng 05.2026 (25.04 - 25.05.2026)',
        'sheet_id': '1suHerEzgKzxB7g1UbrGIZPNaxK5a96xFnmxcIQywpko',
        'gid': '1422896115',
        'priority': 1
    },
    {
        'id': 'T06_2026',
        'name': 'Đối Soát Kho Rau tháng 06.2026 (26.05 - 24.06.2026)',
        'sheet_id': '1065akVGAsBNjONniCS6ccU_mmsRFXb663_Qms8U053Q',
        'gid': '1422896115',
        'priority': 2
    },
    {
        'id': 'T07_2026',
        'name': 'Đối Soát Kho Rau tháng 25.06.2026 - 07.2026',
        'sheet_id': '1wdbowphojL8YULVlPwDHK-hofacdt6J5K_PFZbWz-as',
        'gid': '1422896115',
        'priority': 3
    },
    {
        'id': 'T08_2026',
        'name': 'Đối Soát Kho Rau tháng 08.2026',
        'sheet_id': '1vPHHrZf5prEgE_09j_RbQQC1gNWhUmV0Q6aah6Z3mjQ',
        'gid': '1422896115',
        'priority': 4
    },
    {
        'id': 'T09_2026',
        'name': 'Đối Soát Kho Rau tháng 09.2026',
        'sheet_id': '1XBNLjZLsgaaHDBqVKsbCSYhzD4v-4qMA6rjGXGG4ThM',
        'gid': '1422896115',
        'priority': 5
    }
]

def load_sheet_data(cfg):
    url = f"https://docs.google.com/spreadsheets/d/{cfg['sheet_id']}/export?format=csv&gid={cfg['gid']}"
    print(f"[*] Đang nạp {cfg['name']}...", flush=True)
    req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
    content = urllib.request.urlopen(req, timeout=40).read().decode('utf-8', errors='ignore')
    reader = csv.reader(io.StringIO(content))
    rows = list(reader)
    data_rows = rows[3:] if len(rows) > 3 else []
    print(f"    -> Đã đọc {len(data_rows):,} dòng.", flush=True)
    return data_rows

def run_migration():
    init_sheet_db()
    records_by_key = {}

    for cfg in SHEET_CONFIGS:
        rows = load_sheet_data(cfg)
        for r in rows:
            if len(r) < 10:
                continue
            transfer_date = r[1].strip() if len(r) > 1 else ""
            store_id = r[3].strip() if len(r) > 3 else ""
            sku_code = r[4].strip() if len(r) > 4 else ""
            pt_transfer = r[10].strip() if len(r) > 10 else ""
            
            key = (transfer_date, store_id, pt_transfer, sku_code)
            
            nguoi_xu_ly = r[0].strip() if len(r) > 0 else ""
            branch_name = r[2].strip() if len(r) > 2 else ""
            item_name = r[5].strip() if len(r) > 5 else ""
            uom = r[6].strip() if len(r) > 6 else ""
            qty_transfer = parse_num(r[7]) if len(r) > 7 else 0.0
            qty_receive = parse_num(r[8]) if len(r) > 8 else 0.0
            qty_diff = parse_num(r[9]) if len(r) > 9 else 0.0
            box_code = r[11].strip() if len(r) > 11 else ""
            to_code = r[12].strip() if len(r) > 12 else ""
            qty_loss = parse_num(r[13]) if len(r) > 13 else 0.0
            qty_return_st = parse_num(r[14]) if len(r) > 14 else 0.0
            qty_diff_cxd = parse_num(r[15]) if len(r) > 15 else 0.0
            pt_return_st = r[16].strip() if len(r) > 16 else ""
            pt_return_dc = r[17].strip() if len(r) > 17 else ""
            pt_dc_pick_du = r[18].strip() if len(r) > 18 else ""
            note = r[19].strip() if len(r) > 19 else ""
            status = r[20].strip() if len(r) > 20 else ""
            error_type = r[21].strip() if len(r) > 21 else ""
            loss_type = r[22].strip() if len(r) > 22 else ""
            st_responsible = r[23].strip() if len(r) > 23 else ""
            kho_responsible = r[24].strip() if len(r) > 24 else ""
            process_status = r[25].strip() if len(r) > 25 else "Đang xử lý"
            image_link = r[26].strip() if len(r) > 26 else ""
            dc_confirm = r[27].strip() if len(r) > 27 else ""
            dc_note = r[28].strip() if len(r) > 28 else ""
            kfm_response = r[29].strip() if len(r) > 29 else ""
            kfm_note = r[30].strip() if len(r) > 30 else ""
            item_type = r[31].strip() if len(r) > 31 else ""
            package_type = r[32].strip() if len(r) > 32 else ""
            loss_percent = r[33].strip() if len(r) > 33 else ""
            unit_price = parse_num(r[34]) if len(r) > 34 else 0.0
            total_amount = parse_num(r[35]) if len(r) > 35 else 0.0
            loss_amount = parse_num(r[36]) if len(r) > 36 else 0.0
            st_amount = parse_num(r[37]) if len(r) > 37 else 0.0
            kho_amount = parse_num(r[38]) if len(r) > 38 else 0.0
            cxd_amount = parse_num(r[39]) if len(r) > 39 else 0.0
            gsm = r[40].strip() if len(r) > 40 else ""
            rsm = r[41].strip() if len(r) > 41 else ""
            area = r[42].strip() if len(r) > 42 else ""
            pho_note = r[43].strip() if len(r) > 43 else ""
            shipping_schedule = r[44].strip() if len(r) > 44 else ""
            clv3 = r[45].strip() if len(r) > 45 else ""
            clv4 = r[46].strip() if len(r) > 46 else ""
            
            record = (
                nguoi_xu_ly, transfer_date, branch_name, store_id, sku_code, item_name, uom,
                qty_transfer, qty_receive, qty_diff, pt_transfer, box_code, to_code,
                qty_loss, qty_return_st, qty_diff_cxd, pt_return_st, pt_return_dc, pt_dc_pick_du,
                note, status, error_type, loss_type, st_responsible, kho_responsible,
                process_status, image_link, dc_confirm, dc_note, kfm_response, kfm_note, item_type, package_type,
                loss_percent, unit_price, total_amount, loss_amount, st_amount, kho_amount, cxd_amount,
                gsm, rsm, area, pho_note, shipping_schedule, clv3, clv4
            )
            records_by_key[key] = record

    total_records = len(records_by_key)
    print(f"[*] Đang lưu {total_records:,} dòng vào cơ sở dữ liệu SQLite...", flush=True)

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("DELETE FROM sheet_audit_records")

    insert_sql = """
        INSERT INTO sheet_audit_records (
            nguoi_xu_ly, transfer_date, branch_name, store_id, sku_code, item_name, uom,
            qty_transfer, qty_receive, qty_diff, pt_transfer, box_code, to_code,
            qty_loss, qty_return_st, qty_diff_cxd, pt_return_st, pt_return_dc, pt_dc_pick_du,
            note, status, error_type, loss_type, st_responsible, kho_responsible,
            process_status, image_link, dc_confirm, dc_note, kfm_response, kfm_note, item_type, package_type,
            loss_percent, unit_price, total_amount, loss_amount, st_amount, kho_amount, cxd_amount,
            gsm, rsm, area, pho_note, shipping_schedule, clv3, clv4
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """

    all_values = list(records_by_key.values())
    batch_size = 2000
    for i in range(0, len(all_values), batch_size):
        batch = all_values[i:i+batch_size]
        cursor.executemany(insert_sql, batch)

    conn.commit()

    # Query summary
    cursor.execute("""
        SELECT 
            CASE 
                WHEN transfer_date LIKE '__/__/____' THEN SUBSTR(transfer_date, 4, 2) || '/' || SUBSTR(transfer_date, 7, 4)
                WHEN transfer_date LIKE '____-__-__' THEN SUBSTR(transfer_date, 6, 2) || '/' || SUBSTR(transfer_date, 1, 4)
                ELSE SUBSTR(transfer_date, 1, 7)
            END as m,
            COUNT(*),
            COUNT(DISTINCT store_id),
            COALESCE(SUM(total_amount), 0)
        FROM sheet_audit_records
        GROUP BY m
        ORDER BY m DESC
    """)
    summary = cursor.fetchall()
    conn.close()

    print("\n=== KẾT QUẢ ĐỒNG BỘ TOÀN BỘ CÁC THÁNG ===")
    for row in summary:
        print(f"  Tháng {row[0]}: {row[1]:,} case | {row[2]} siêu thị | {row[3]:,.0f} VNĐ")

    sync_ds_st_data()
    print("\n[SUCCESS] Hoàn tất nạp dữ liệu đa tháng thành công!")

if __name__ == '__main__':
    run_migration()
