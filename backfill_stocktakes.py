import sys, os, sqlite3, json, urllib.request, re, time
from datetime import datetime, timedelta
from concurrent.futures import ThreadPoolExecutor, as_completed

sys.path.insert(0, r'd:\MAE\scratch\kingfood_scm_bot')
from kingfood_api import get_headers
from sheet_sync import DB_PATH, is_target_produce_or_bakery

def backfill_to_aug_01():
    conn = sqlite3.connect(DB_PATH, timeout=60)
    cursor = conn.cursor()
    cursor.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_inv_unique ON store_inventory_records (date, store_id, barcode)")
    cursor.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_neg_unique ON store_negative_stock_records (date, store_id, barcode)")
    conn.commit()

    cursor.execute("SELECT store_id, store_name FROM sheet_store_list")
    store_map = {r[0]: r[1] for r in cursor.fetchall()}

    skip = 7400
    limit = 200
    reach_end = False

    while skip < 15000 and not reach_end:
        url = f'https://api.kingfood.co/v1/stocktakes?status=5&sort_by=created_at&sort_type=-1&limit={limit}&skip={skip}'
        try:
            req = urllib.request.Request(url, headers=get_headers())
            with urllib.request.urlopen(req, timeout=12) as resp:
                data = json.loads(resp.read().decode('utf-8'))
                items = data.get('items', [])
                if not items:
                    break
                
                batch_sts = []
                for st in items:
                    dt = (st.get('created_at') or st.get('completed_at') or '')[:10]
                    if dt and dt < '2026-08-01':
                        reach_end = True
                        break
                    if st.get('total_sku', 0) > 0:
                        batch_sts.append(st)
                
                print(f"Skip {skip}: processing {len(batch_sts)} stocktakes (latest: {items[0].get('created_at')[:10]}, oldest: {items[-1].get('created_at')[:10]})...", flush=True)

                def process_st(st):
                    st_id = st.get('id')
                    st_code = st.get('code', '')
                    created_at_str = st.get('created_at') or st.get('completed_at') or ''
                    date_iso = datetime.now().strftime('%Y-%m-%d')
                    if created_at_str:
                        try:
                            dt = datetime.fromisoformat(created_at_str.replace('Z', '+00:00')) + timedelta(hours=7)
                            date_iso = dt.strftime('%Y-%m-%d')
                        except Exception:
                            pass
                    m = re.search(r'^\d{6}-([A-Za-z0-9]+)-', st_code)
                    store_code = m.group(1) if m else st.get('branch_id', '')[:8]
                    store_name = store_map.get(store_code, f"KFM_{store_code}")

                    lines_url = f'https://api.kingfood.co/v1/stocktakes/lines?stocktake_id={st_id}&limit=100'
                    res_items = []
                    try:
                        r_lines = urllib.request.Request(lines_url, headers=get_headers())
                        with urllib.request.urlopen(r_lines, timeout=8) as res_l:
                            l_data = json.loads(res_l.read().decode('utf-8'))
                            for line in l_data.get('items', []):
                                bcode = str(line.get('barcode') or '').strip()
                                pname = str(line.get('name') or '').strip()
                                if not bcode or not pname:
                                    continue
                                cates = line.get('cates', [])
                                is_tgt, cat_name = is_target_produce_or_bakery(cates, pname)
                                if not is_tgt:
                                    continue
                                diff_q = float(line.get('diff_quantity') or 0.0)
                                stock_q = float(line.get('stock_quantity') or 0.0)
                                actual_q = float(line.get('actual_stock_quantity') or 0.0)
                                diff_v = float(line.get('diff_value') or 0.0)
                                cost = float(line.get('cost') or 0.0)
                                price = float(line.get('price') or 0.0)
                                res_items.append((date_iso, store_code, store_name, st_code, bcode, pname, cat_name, stock_q, diff_q, diff_v, cost, price, actual_q))
                    except Exception:
                        pass
                    return res_items

                nang_rows = []
                am_rows = []
                with ThreadPoolExecutor(max_workers=10) as ex:
                    futures = [ex.submit(process_st, st) for st in batch_sts]
                    for f in as_completed(futures):
                        for (date_iso, store_code, store_name, st_code, bcode, pname, cat_name, stock_q, diff_q, diff_v, cost, price, actual_q) in f.result():
                            if diff_v <= 0 and diff_q > 0:
                                diff_v = diff_q * (cost if cost > 0 else price)
                            if diff_q > 0:
                                audit_note = f"Phiếu KK {st_code} (Sổ sách: {stock_q} -> Thực tế: {actual_q})"
                                status_lbl = "Bất thường" if diff_v > 200000 else ("Cần lưu ý" if diff_v > 50000 else "Đã kiểm kê")
                                nang_rows.append((
                                    date_iso, store_code, store_name, bcode, bcode, pname, cat_name,
                                    stock_q, diff_q, round(diff_v, 0), 0.0, 0.0, 0.0, actual_q,
                                    audit_note, status_lbl
                                ))
                            if stock_q < 0:
                                neg_val = abs(stock_q) * (cost if cost > 0 else price)
                                neg_note = f"Tồn sổ sách bị âm ({stock_q}) trước khi kiểm kê {st_code}"
                                am_rows.append((
                                    date_iso, store_code, store_name, bcode, bcode, pname, cat_name,
                                    abs(stock_q), round(neg_val, 0), stock_q, neg_note, "Cần bù tồn"
                                ))

                if nang_rows:
                    cursor.executemany("""
                        INSERT OR REPLACE INTO store_inventory_records (
                            date, store_id, store_name, barcode, sku, product_name, category_name,
                            opening_stock, stocktake_in_qty, stocktake_in_value, stocktake_out_qty, stocktake_out_value, damage_qty, closing_stock,
                            audit_note, status
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """, nang_rows)
                if am_rows:
                    cursor.executemany("""
                        INSERT OR REPLACE INTO store_negative_stock_records (
                            date, store_id, store_name, barcode, sku, product_name, category_name,
                            negative_qty, negative_value, closing_stock, reason, status
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """, am_rows)
                conn.commit()
                print(f"Committed page skip {skip}: +{len(nang_rows)} nang ton, +{len(am_rows)} am ton", flush=True)

                if reach_end:
                    break
                skip += limit
        except Exception as e:
            print(f"Error at skip {skip}: {e}", flush=True)
            break

    cursor.execute('SELECT min(date), max(date), count(*) FROM store_inventory_records')
    print('Final Nang Ton:', cursor.fetchone())
    cursor.execute('SELECT min(date), max(date), count(*) FROM store_negative_stock_records')
    print('Final Am Ton:', cursor.fetchone())
    conn.close()

if __name__ == '__main__':
    backfill_to_aug_01()
