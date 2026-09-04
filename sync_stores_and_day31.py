import urllib.request, json, sqlite3, sys
sys.stdout.reconfigure(encoding='utf-8')
from kingfood_api import get_kingfood_token

token = get_kingfood_token()

# 1. CẬP NHẬT MÃ, TÊN ST, CÁC CẤP QUẢN LÝ (KFM_HCM...) TỪ NEXT.KINGFOOD.CO
url_branches = 'https://api.kingfood.co/v1/branches?limit=500'
req = urllib.request.Request(url_branches, headers={'Authorization': f'Bearer {token}', 'User-Agent': 'Mozilla/5.0'})
res = urllib.request.urlopen(req)
b_data = json.loads(res.read())
branches = b_data.get('items', [])

hcm_branches = [b for b in branches if b.get('name', '').startswith('KFM_HCM')]
print(f"[*] Tìm thấy {len(hcm_branches)} chi nhánh KFM_HCM từ hệ thống Kingfood Next.")

url_depts = 'https://api.kingfood.co/v1/users-departments/departments/fulldata'
req_d = urllib.request.Request(url_depts, headers={'Authorization': f'Bearer {token}', 'User-Agent': 'Mozilla/5.0'})
res_d = urllib.request.urlopen(req_d)
depts = json.loads(res_d.read())

dept_by_hrw = {d.get('hrw_derparment_id'): d for d in depts if d.get('hrw_derparment_id')}
dept_by_branch = {d.get('branch_id'): d for d in depts if d.get('branch_id')}

conn = sqlite3.connect('scm_monitor.db')
cursor = conn.cursor()

# Xóa các ST KFM_HCM cũ hoặc cập nhật toàn bộ
updated_stores = 0
for b in hcm_branches:
    b_id = b.get('id')
    b_code = b.get('code') or b.get('name_abbreviate')
    b_name = b.get('name')
    
    d = dept_by_branch.get(b_id)
    sm_list = []
    gsm_list = []
    rsm_list = []
    
    if d:
        for m in d.get('manager', []):
            jname = (m.get('hrw_job') or {}).get('name', '')
            emp = f"{m.get('employee_code')} - {m.get('employee_name')}"
            if 'Store Manager' in jname and 'Group' not in jname and 'Regional' not in jname:
                sm_list.append(emp)
            elif 'Group Store Manager' in jname:
                gsm_list.append(emp)
            elif 'Regional' in jname:
                rsm_list.append(emp)
            else:
                sm_list.append(emp)
                
        curr = d
        while curr and curr.get('hrw_parent_derparment_id'):
            p_id = curr.get('hrw_parent_derparment_id')
            p = dept_by_hrw.get(p_id)
            if not p:
                break
            for m in p.get('manager', []):
                jname = (m.get('hrw_job') or {}).get('name', '')
                emp = f"{m.get('employee_code')} - {m.get('employee_name')}"
                if 'Regional' in jname or 'RSM' in jname:
                    if emp not in rsm_list:
                        rsm_list.append(emp)
                elif 'Group' in jname or 'GSM' in jname:
                    if emp not in gsm_list:
                        gsm_list.append(emp)
                elif 'Store Manager' in jname and not sm_list:
                    sm_list.append(emp)
            curr = p
            
    sm_str = ", ".join(sm_list)
    gsm_str = ", ".join(gsm_list)
    rsm_str = ", ".join(rsm_list)
    
    # Kiểm tra xem store_id đã tồn tại chưa
    cursor.execute("SELECT id FROM sheet_store_list WHERE store_id = ? OR store_name = ?", (b_code, b_name))
    row = cursor.fetchone()
    if row:
        cursor.execute("""
            UPDATE sheet_store_list 
            SET store_id = ?, store_name = ?, sm = ?, gsm = ?, rsm = ?, updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
        """, (b_code, b_name, sm_str, gsm_str, rsm_str, row[0]))
    else:
        cursor.execute("""
            INSERT INTO sheet_store_list (store_id, store_name, sm, gsm, rsm, is_done)
            VALUES (?, ?, ?, ?, ?, 0)
        """, (b_code, b_name, sm_str, gsm_str, rsm_str))
    updated_stores += 1

conn.commit()
print(f"[+] Đã cập nhật thành công {updated_stores} ST KFM_HCM vào CSDL (bảng sheet_store_list)!")

# 2. BỔ SUNG CÁC CASE NGÀY 31/08 TỪ TELEGRAM GROUP SCM - KRC (ĐỐI SOÁT)
chat_id = -1003511338216
chat_title = 'SCM - KRC (Đối soát)'

# Tin 1: SAFIRA Khang Điền SFR (Đậu rồng 200g)
msg1_id = 9815
msg1_text = """08/31/2026
KFM_HCM_TDU - D1-1.24 SAFIRA Khang Điền SFR
11364 ĐẬU RỒNG 200G
PT1743341
Chuyển 3 nhận 0 CL 3
Nhờ team kiểm tra giùm em mã này với ạ, ST nhận IAP,
@minhthudoan @nynguyen09"""

cursor.execute("SELECT id FROM raw_messages WHERE msg_id = ? AND chat_id = ?", (msg1_id, chat_id))
if not cursor.fetchone():
    cursor.execute("""
        INSERT INTO raw_messages (msg_id, chat_id, chat_title, sender_id, sender_name, username, message_text, category, priority, issue_type, created_at, is_read, is_dismissed)
        VALUES (?, ?, ?, 0, 'SGN2-CTV-Ly Ly', '', ?, 'Rau Củ', 'P2', 'Thừa', '2026-08-31 14:37:00', 0, 0)
    """, (msg1_id, chat_id, chat_title, msg1_text))
    print(f"[+] Đã thêm case ngày 31/08 (MsgID {msg1_id} - SFR - ĐẬU RỒNG)!")

# Tin 2: Diamond Celadon City CLD (Bơ Booth)
msg2_id = 9816
msg2_text = """08/31/2026 KFM_HCM_TPH - S1.0.38 Block A5 Diamond Celadon City CLD
BƠ BOOTH
PT1743281 1100942
Chuyển 12,00 nhận 9,11 CL 2,895
Nhờ team check lại giúp e mã này ạ"""

cursor.execute("SELECT id FROM raw_messages WHERE msg_id = ? AND chat_id = ?", (msg2_id, chat_id))
if not cursor.fetchone():
    cursor.execute("""
        INSERT INTO raw_messages (msg_id, chat_id, chat_title, sender_id, sender_name, username, message_text, category, priority, issue_type, created_at, is_read, is_dismissed)
        VALUES (?, ?, ?, 0, 'SNG2-CTV- Huỳnh', '', ?, 'Trái Cây', 'P2', 'Thiếu', '2026-08-31 15:40:00', 0, 0)
    """, (msg2_id, chat_id, chat_title, msg2_text))
    print(f"[+] Đã thêm case ngày 31/08 (MsgID {msg2_id} - CLD - BƠ BOOTH)!")

# Tin 3: Tin trả lời của Thư Đoàn
msg3_id = 9817
msg3_text = "đang check ST nào á team ơi, này cam của NDT không phải CLD á"
cursor.execute("SELECT id FROM raw_messages WHERE msg_id = ? AND chat_id = ?", (msg3_id, chat_id))
if not cursor.fetchone():
    cursor.execute("""
        INSERT INTO raw_messages (msg_id, chat_id, chat_title, sender_id, sender_name, username, message_text, category, priority, issue_type, reply_to_msg_id, created_at, is_read, is_dismissed)
        VALUES (?, ?, ?, 0, 'Thư Đoàn', '', ?, 'Khác', 'P3', 'Khác', ?, '2026-08-31 15:45:00', 0, 0)
    """, (msg3_id, chat_id, chat_title, msg3_text, msg2_id))
    print(f"[+] Đã thêm tin nhắn phản hồi của bạn vào case MsgID {msg2_id}!")

conn.commit()
conn.close()
print("[*] Hoàn tất cập nhật đồng bộ CSDL thành công!")
