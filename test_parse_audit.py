import sys, re, sqlite3

if sys.platform == 'win32':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

conn = sqlite3.connect('scm_monitor.db')
cursor = conn.cursor()
cursor.execute('''
    SELECT id, created_at, sender_name, message_text 
    FROM raw_messages 
    WHERE chat_title = 'SCM - KRC (Đối soát)'
    AND message_text NOT LIKE '%phản hồi giúp e case này%'
    AND message_text NOT LIKE '%phản hồi case này giúp e%'
    AND message_text NOT LIKE '%có cam nhận hàng hem%'
    AND message_text NOT LIKE '%mở quyền%'
    AND message_text NOT LIKE '%add giá cost%'
    AND message_text NOT LIKE '%các nhóm hàng còn lại rà lại%'
    AND message_text NOT LIKE '%mấy case này đã phản hồi%'
    AND sender_name NOT LIKE '%Thư Đoàn%'
    AND sender_name NOT LIKE '%SC017084%'
''')
rows = cursor.fetchall()

def parse_full_audit(text, created_at):
    lines = [l.strip() for l in text.split('\n') if l.strip()]
    
    # 1. Ngày
    date_match = re.search(r'(\d{1,2}[\/\.\-]\d{1,2}(?:[\/\.\-]\d{2,4})?)', text)
    date_str = date_match.group(1) if date_match else created_at.split()[0]
    
    # 2. Tên ST
    st_name = ''
    st_match = re.search(r'(?:KFM_[A-Z0-9_]+|ST\s+[A-Z0-9]+)\s*[-:]?\s*([^\n\r]+)', text)
    if st_match:
        st_name = st_match.group(0).strip()
    elif len(lines) > 0 and ('KFM' in lines[0] or 'ST' in lines[0]):
        st_name = lines[0]
        
    # 3. Mã PT
    pt_match = re.search(r'(PT\d+)', text, re.IGNORECASE)
    pt_code = pt_match.group(1) if pt_match else '---'
    
    # 4. Mã hàng & Tên hàng
    sku_code = ''
    item_name = ''
    pt_line_match = re.search(r'PT\d+\s+([0-9]{4,14})', text)
    if pt_line_match:
        sku_code = pt_line_match.group(1)
    else:
        sku_match = re.search(r'\b([0-9]{5,13})\b', text)
        if sku_match:
            sku_code = sku_match.group(1)
            
    for l in lines:
        if l == lines[0] or 'PT' in l or 'Chuyển' in l or 'chuyển' in l or 'Nhờ' in l or 'ST nhận' in l:
            continue
        if re.search(r'[A-ZÀ-Ỵ]{3,}', l) and not l.startswith('KFM'):
            item_name = re.sub(r'\b[0-9]{4,14}\b', '', l).strip()
            break
    if not item_name and len(lines) >= 2:
        for l in lines[1:]:
            if not l.startswith('PT') and not l.startswith('Chuyển') and not l.startswith('chuyển') and not l.startswith('Nhờ'):
                item_name = l
                break

    # 5. Số lượng / Chênh lệch
    cl_match = re.search(r'chuyển\s*([\d,\.]+)\s*nhận\s*([\d,\.]+)\s*(?:cl|chênh lệch)\s*([\d,\.]+)', text, re.IGNORECASE)
    qty_info = ''
    issue_type = 'Thiếu'
    if cl_match:
        qty_info = f"Chuyển: {cl_match.group(1)} | Nhận: {cl_match.group(2)} | CL: {cl_match.group(3)}"
    elif re.search(r'(?:cl|chênh lệch)\s*([\d,\.]+)', text, re.IGNORECASE):
        cl_match_simple = re.search(r'(?:cl|chênh lệch)\s*([\d,\.]+)', text, re.IGNORECASE)
        qty_info = "Lệch: " + cl_match_simple.group(1)

        
    # 6. ST ghi nhận dư & Hướng dẫn tra cứu PT chuyển
    st_du = ''
    lower = text.lower()
    has_other_st = False
    du_match = re.search(r'st\s+nhận\s+([^\n\r]+)', lower)
    if du_match and not any(w in du_match.group(1) for w in ['rổ', 'cân', 'thiếu', 'đủ']):
        st_du = du_match.group(1).strip()
        has_other_st = True
    elif 'a178 nhận' in lower:
        st_du = 'A178'
        has_other_st = True
    elif any(k in lower for k in ['st nhận vh', 'st nhận hmn', 'st nhận bcg']):
        st_du = re.search(r'(vh\d+|hmn|bcg)', lower).group(1).upper()
        has_other_st = True

    if has_other_st or 'dư' in lower or 'thừa' in lower:
        if not any(w in lower for w in ['chỉ cân', 'nhưng chỉ cân']):
            issue_type = 'Thừa'

    return {
        'date': date_str,
        'st_name': st_name or '---',
        'pt_code': pt_code,
        'sku_code': sku_code or '---',
        'item_name': item_name or '---',
        'qty_info': qty_info or '---',
        'issue_type': issue_type,
        'st_du': st_du.upper() if st_du else '---',
        'content': text
    }

for r in rows:
    res = parse_full_audit(r[3], r[1])
    print('================================================================')
    print(f"NGÀY: {res['date']} | ST: {res['st_name']}")
    print(f"MÃ PT: {res['pt_code']} | MÃ HÀNG: {res['sku_code']} | TÊN HÀNG: {res['item_name']}")
    print(f"PHÂN LOẠI: [{res['issue_type']}] | SL: {res['qty_info']}")
    if res['issue_type'] == 'Thừa':
        print(f"-> ST GHI NHẬN DƯ: {res['st_du']}")
        print(f"-> TRA CỨU PT KRC: Nơi chuyển KRC -> Nơi nhận: {res['st_du']} -> Ngày chuyển: {res['date']}")
