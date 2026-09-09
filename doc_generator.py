import os
import sys
import re
from datetime import datetime
import docx
from docx.shared import Pt, Inches, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_TABLE_ALIGNMENT, WD_CELL_VERTICAL_ALIGNMENT
from docx.oxml import OxmlElement
from docx.oxml.ns import qn

# --- CHUYỂN SỐ THÀNH CHỮ TIẾNG VIỆT CHUẨN ---
def num_to_vietnamese_words(number, include_dong=True):
    try:
        n = int(round(abs(float(number))))
    except:
        return "Không đồng" if include_dong else "Không"
        
    if n == 0:
        return "Không đồng" if include_dong else "Không"
        
    units = ["", "một", "hai", "ba", "bốn", "năm", "sáu", "bảy", "tám", "chín"]
    
    def read_hundreds(num, is_highest=False):
        h = num // 100
        t = (num % 100) // 10
        u = num % 10
        res = []
        
        if h > 0 or not is_highest:
            res.append(f"{units[h]} trăm")
            
        if t > 1:
            res.append(f"{units[t]} mươi")
            if u == 1:
                res.append("mốt")
            elif u == 5:
                res.append("lăm")
            elif u > 0:
                res.append(units[u])
        elif t == 1:
            res.append("mười")
            if u == 5:
                res.append("lăm")
            elif u > 0:
                res.append(units[u])
        elif t == 0 and u > 0:
            if h > 0 or not is_highest:
                res.append(f"lẻ {units[u]}")
            else:
                res.append(units[u])
                
        return " ".join(res)

    scales = ["", "nghìn", "triệu", "tỷ", "nghìn tỷ", "triệu tỷ"]
    groups = []
    temp = n
    while temp > 0:
        groups.append(temp % 1000)
        temp //= 1000
        
    res_parts = []
    for i in reversed(range(len(groups))):
        g = groups[i]
        if g > 0:
            part = read_hundreds(g, is_highest=(i == len(groups)-1))
            res_parts.append(f"{part} {scales[i]}".strip())
            
    text = " ".join(res_parts).strip()
    text = text.replace("mươi năm", "mươi lăm")
    text = text.replace("mươi một", "mươi mốt")
    text = text[0].upper() + text[1:]
    if include_dong:
        text += " đồng"
    return text


def set_cell_margins(cell, top=80, bottom=80, left=100, right=100):
    tcPr = cell._element.get_or_add_tcPr()
    tcMar = OxmlElement('w:tcMar')
    for m, val in [('top', top), ('bottom', bottom), ('left', left), ('right', right)]:
        node = OxmlElement(f'w:{m}')
        node.set(qn('w:w'), str(val))
        node.set(qn('w:type'), 'dxa')
        tcMar.append(node)
    tcPr.append(tcMar)


def set_cell_border(cell, **kwargs):
    tc = cell._element
    tcPr = tc.get_or_add_tcPr()
    tcBorders = OxmlElement('w:tcBorders')
    for edge in ('top', 'left', 'bottom', 'right', 'insideH', 'insideV'):
        edge_data = kwargs.get(edge)
        if edge_data:
            b = OxmlElement(f'w:{edge}')
            for key, val in edge_data.items():
                b.set(qn(f'w:{key}'), str(val))
            tcBorders.append(b)
        else:
            b = OxmlElement(f'w:{edge}')
            b.set(qn('w:val'), 'none')
            tcBorders.append(b)
    tcPr.append(tcBorders)


def clean_warehouse_name(w):
    if not w:
        return "KHO SEEDLOG"
    s = str(w).strip()
    u = s.upper()
    if "SEEDLOG" in u or "SEEDCOM" in u or "KHO TỔNG" in u:
        return "KHO SEEDLOG"
    if "MEAT" in u or "THỊT" in u:
        return "KHO MEATFISH"
    if "RAU" in u or "KRC" in u:
        return "KHO RAU CỦ"
    if "ĐÔNG MÁT" in u or "BÌNH TÂN" in u or "ABA" in u:
        return "KHO ĐÔNG MÁT"
    if "ĐÔNG" in u:
        return "KHO ĐÔNG"
    if "MÁT" in u:
        return "KHO MÁT"
    import re
    cleaned = re.sub(r'\(.*?\)', '', s).strip()
    if not cleaned.upper().startswith("KHO ") and not cleaned.upper().startswith("DC "):
        cleaned = f"KHO {cleaned}"
    return cleaned.upper()


def format_co_display(co_val, content_val=None):
    """
    Quy tắc định dạng cột CO chuẩn theo yêu cầu:
    1. Nếu là Hủy hàng Hậu kiểm (chứa từ khóa HẬU KIỂM, HAU KIEM, HỦY HÀNG HK hoặc mã HK) -> hiển thị 'HK'
    2. Nếu có mã CO (tìm thấy mã dạng CO... trong co_val hoặc content) -> hiển thị mã CO
    3. Nếu không có CO và không phải Hậu kiểm -> để trống '' (không điền tên hóa đơn hay diễn giải dài vào ô CO)
    """
    co_str = str(co_val or '').strip()
    content_str = str(content_val or '').strip()
    combined = f"{co_str} {content_str}".strip()
    combined_upper = combined.upper()

    # 1. Kiểm tra Hủy hàng Hậu kiểm / HK
    if any(k in combined_upper for k in ['HẬU KIỂM', 'HAU KIEM', 'HỦY HÀNG HK', 'HUY HANG HK']) or co_str.upper() == 'HK':
        return 'HK'

    # 2. Tìm mã CO dạng CO... trong co_val hoặc content
    co_matches = re.findall(r'CO[-\s]?\d+', combined, re.IGNORECASE)
    if co_matches:
        seen = set()
        distinct = []
        for m in co_matches:
            m_norm = re.sub(r'\s+', '', m).upper()
            if m_norm not in seen:
                seen.add(m_norm)
                distinct.append(m_norm)
        return ', '.join(distinct)

    # 3. Nếu người dùng nhập trực tiếp một mã ngắn gọn hợp lệ (không phải văn bản/nội dung hóa đơn dài)
    noise_keywords = ['XHD', 'TRUY THU', 'BIÊN BẢN', 'HÓA ĐƠN', 'THEO', 'NGÀY', 'THANH LÝ', 'HƯ HỎNG', 'THẤT THOÁT', 'CLAIM']
    if co_str and len(co_str) <= 25 and not any(k in co_str.upper() for k in noise_keywords):
        return co_str

    # 4. Không có CO -> để trống
    return ''


# --- 1. TẠO QUYẾT ĐỊNH TRUY THU (.DOCX) ---
def generate_quyet_dinh_docx(data, output_path):
    doc = docx.Document()
    
    # Chuẩn căn lề văn bản hành chính Việt Nam (Nghị định 30/2020/NĐ-CP):
    # Khổ A4: 210mm x 297mm (8.27 in x 11.69 in)
    # Lề trái: 25.4mm (1.0 in) để bấm kim/đóng tập
    # Lề phải: 20.0mm (0.79 in)
    # Lề trên: 20.0mm (0.79 in)
    # Lề dưới: 20.0mm (0.79 in)
    # Vùng in khả dụng: 6.48 in
    for sec in doc.sections:
        sec.top_margin = Inches(0.79)
        sec.bottom_margin = Inches(0.79)
        sec.left_margin = Inches(1.0)
        sec.right_margin = Inches(0.79)

    w_name = clean_warehouse_name(data.get('warehouse_name', 'KHO SEEDLOG'))
    month = str(data.get('month', '07')).zfill(2)
    year = str(data.get('year', '2026'))

    # 1. Header Table (Quốc hiệu & Tên công ty) - Không viền
    table_header = doc.add_table(rows=1, cols=2)
    table_header.alignment = WD_TABLE_ALIGNMENT.CENTER
    table_header.autofit = False
    table_header.columns[0].width = Inches(3.15)
    table_header.columns[1].width = Inches(3.33)

    c0 = table_header.cell(0, 0)
    p0 = c0.paragraphs[0]
    p0.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p0.paragraph_format.line_spacing = 1.15
    p0.paragraph_format.space_after = Pt(0)
    r0 = p0.add_run("CÔNG TY CỔ PHẦN\nKING FOOD MARKET\n")
    r0.bold = True
    r0.font.size = Pt(10.5)
    r0.font.name = "Times New Roman"
    r0_sub = p0.add_run("*****")
    r0_sub.font.bold = True
    r0_sub.font.size = Pt(10.5)
    r0_sub.font.name = "Times New Roman"

    c1 = table_header.cell(0, 1)
    p1 = c1.paragraphs[0]
    p1.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p1.paragraph_format.line_spacing = 1.15
    p1.paragraph_format.space_after = Pt(0)
    r1 = p1.add_run("CỘNG HÒA XÃ HỘI CHỦ NGHĨA VIỆT NAM\nĐộc lập – Tự do – Hạnh phúc\n")
    r1.bold = True
    r1.font.size = Pt(10.5)
    r1.font.name = "Times New Roman"
    
    # Ngày văn bản
    doc_date_str = data.get('doc_date', datetime.now().strftime('%d/%m/%Y'))
    try:
        dp = doc_date_str.split('/')
        date_text = f"TPHCM, ngày {dp[0]} tháng {dp[1]} năm {dp[2]}"
    except:
        date_text = f"TPHCM, ngày {datetime.now().day} tháng {datetime.now().month} năm {datetime.now().year}"
        
    r1_sub = p1.add_run(f"********\n{date_text}")
    r1_sub.font.italic = True
    r1_sub.font.size = Pt(10)
    r1_sub.font.name = "Times New Roman"

    # 2. Tiêu đề QUYẾT ĐỊNH
    p_title = doc.add_paragraph()
    p_title.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p_title.paragraph_format.space_before = Pt(14)
    p_title.paragraph_format.space_after = Pt(6)
    p_title.paragraph_format.line_spacing = 1.15
    r_t1 = p_title.add_run("QUYẾT ĐỊNH\n")
    r_t1.bold = True
    r_t1.font.size = Pt(14)
    r_t1.font.name = "Times New Roman"
    
    r_t2 = p_title.add_run(f"Về việc truy thu giá trị claim {w_name} tháng {month}/{year}\n-------------------------")
    r_t2.bold = True
    r_t2.font.size = Pt(11.5)
    r_t2.font.name = "Times New Roman"

    # 3. Căn cứ
    p_cc = doc.add_paragraph()
    p_cc.paragraph_format.space_before = Pt(4)
    p_cc.paragraph_format.space_after = Pt(6)
    p_cc.paragraph_format.line_spacing = 1.15
    p_cc.alignment = WD_ALIGN_PARAGRAPH.LEFT
    r_cc = p_cc.add_run(f"- Căn cứ vào kết quả giao nhận và kiểm tra thực tế tháng {month}/{year}\n- Căn cứ kết quả đối chiếu của KFM và SCF")
    r_cc.font.size = Pt(10.5)
    r_cc.font.name = "Times New Roman"

    # 4. Điều 1
    p_d1 = doc.add_paragraph()
    p_d1.paragraph_format.space_before = Pt(4)
    p_d1.paragraph_format.space_after = Pt(6)
    p_d1.paragraph_format.line_spacing = 1.15
    p_d1.alignment = WD_ALIGN_PARAGRAPH.LEFT
    r_d1 = p_d1.add_run("Điều 1: ")
    r_d1.bold = True
    r_d1.font.size = Pt(10.5)
    r_d1.font.name = "Times New Roman"
    r_d1_txt = p_d1.add_run("Ghi nhận truy thu/bồi hoàn số lượng và giá trị theo thông tin bên dưới và bảng kê đính kèm:")
    r_d1_txt.font.size = Pt(10.5)
    r_d1_txt.font.name = "Times New Roman"

    # 5. Xử lý dữ liệu bảng kê 7 CỘT CHUẨN
    table_items = []
    inv_list = data.get('invoices', [])
    if inv_list and len(inv_list) > 0:
        for it in inv_list:
            sl = abs(float(it.get('qty') or 0))
            pre = abs(float(it.get('pre_tax') or 0.0))
            post = abs(float(it.get('post_tax') or 0.0))
            if post == 0 and pre > 0:
                post = round(pre * 1.08)
            if pre == 0 and post > 0:
                pre = round(post / 1.08)
            co = format_co_display(it.get('co_number') or it.get('co'), it.get('content'))
            table_items.append({'co': co, 'sl': sl, 'pre': pre, 'post': post})

    if not table_items:
        sl = abs(float(data.get('total_qty', 0)))
        amt = abs(float(data.get('total_amount', 0)))
        vat_type = data.get('vat_type', 'Chưa VAT')
        is_post_vat = ('gồm' in str(vat_type).lower())
        if is_post_vat:
            post = amt
            pre = round(amt / 1.08)
        else:
            pre = amt
            post = round(amt * 1.08)
        co = format_co_display(data.get('co_number') or data.get('co'), data.get('content'))
        table_items.append({'co': co, 'sl': sl, 'pre': pre, 'post': post})

    num_rows = len(table_items)
    tot_sl = sum(it['sl'] for it in table_items)
    tot_pre = sum(it['pre'] for it in table_items)
    tot_post = sum(it['post'] for it in table_items)

    table_data = doc.add_table(rows=num_rows + 2, cols=7)
    table_data.alignment = WD_TABLE_ALIGNMENT.CENTER
    table_data.autofit = False

    headers = ["Tháng", "Tên kho", "CO", "SL Chênh lệch", "Giá trị", "Giá trị (VAT)", "Ghi chú"]
    col_widths = [Inches(0.70), Inches(1.15), Inches(0.90), Inches(0.80), Inches(1.05), Inches(1.05), Inches(0.83)]

    for j, w_col in enumerate(col_widths):
        table_data.columns[j].width = w_col

    # Dòng Header (index 0)
    for j, h in enumerate(headers):
        cell = table_data.cell(0, j)
        cell.width = col_widths[j]
        p = cell.paragraphs[0]
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        p.paragraph_format.line_spacing = 1.15
        p.paragraph_format.space_before = Pt(2)
        p.paragraph_format.space_after = Pt(2)
        r = p.add_run(h)
        r.bold = True
        r.font.size = Pt(9.5)
        r.font.name = "Times New Roman"
        set_cell_margins(cell, 60, 60, 60, 60)
        set_cell_border(cell, top=dict(val='single', sz='6', color='000000'),
                              bottom=dict(val='single', sz='6', color='000000'),
                              left=dict(val='single', sz='6', color='000000'),
                              right=dict(val='single', sz='6', color='000000'))

    # Các dòng dữ liệu (index 1 đến num_rows)
    for i, it in enumerate(table_items):
        row_idx = i + 1
        sl_str = f"({it['sl']:,.0f})" if it['sl'] else "-"
        pre_str = f"({it['pre']:,.0f})" if it['pre'] else "-"
        post_str = f"({it['post']:,.0f})" if it['post'] else "-"

        # Set borders & padding cho từng cell
        for j in range(7):
            cell = table_data.cell(row_idx, j)
            cell.width = col_widths[j]
            set_cell_margins(cell, 50, 50, 60, 60)
            set_cell_border(cell, top=dict(val='single', sz='6', color='000000'),
                                  bottom=dict(val='single', sz='6', color='000000'),
                                  left=dict(val='single', sz='6', color='000000'),
                                  right=dict(val='single', sz='6', color='000000'))

        # Cột CO (j=2)
        cell_co = table_data.cell(row_idx, 2)
        p_co = cell_co.paragraphs[0]
        p_co.alignment = WD_ALIGN_PARAGRAPH.LEFT
        p_co.paragraph_format.line_spacing = 1.15
        p_co.paragraph_format.space_before = Pt(2)
        p_co.paragraph_format.space_after = Pt(2)
        r_co = p_co.add_run(it['co'])
        r_co.font.size = Pt(9)
        r_co.font.name = "Times New Roman"

        # Cột SL Chênh lệch (j=3)
        cell_sl = table_data.cell(row_idx, 3)
        p_sl = cell_sl.paragraphs[0]
        p_sl.alignment = WD_ALIGN_PARAGRAPH.RIGHT
        p_sl.paragraph_format.line_spacing = 1.15
        p_sl.paragraph_format.space_before = Pt(2)
        p_sl.paragraph_format.space_after = Pt(2)
        r_sl = p_sl.add_run(sl_str)
        r_sl.font.size = Pt(9)
        r_sl.font.name = "Times New Roman"

        # Cột Giá trị (j=4)
        cell_pre = table_data.cell(row_idx, 4)
        p_pre = cell_pre.paragraphs[0]
        p_pre.alignment = WD_ALIGN_PARAGRAPH.RIGHT
        p_pre.paragraph_format.line_spacing = 1.15
        p_pre.paragraph_format.space_before = Pt(2)
        p_pre.paragraph_format.space_after = Pt(2)
        r_pre = p_pre.add_run(pre_str)
        r_pre.font.size = Pt(9)
        r_pre.font.name = "Times New Roman"

        # Cột Giá trị (VAT) (j=5)
        cell_post = table_data.cell(row_idx, 5)
        p_post = cell_post.paragraphs[0]
        p_post.alignment = WD_ALIGN_PARAGRAPH.RIGHT
        p_post.paragraph_format.line_spacing = 1.15
        p_post.paragraph_format.space_before = Pt(2)
        p_post.paragraph_format.space_after = Pt(2)
        r_post = p_post.add_run(post_str)
        r_post.font.size = Pt(9)
        r_post.font.name = "Times New Roman"

    # Merge các cột Tháng (0), Tên kho (1), Ghi chú (6) xuyên suốt tất cả các dòng dữ liệu
    if num_rows > 1:
        c0 = table_data.cell(1, 0).merge(table_data.cell(num_rows, 0))
        c1 = table_data.cell(1, 1).merge(table_data.cell(num_rows, 1))
        c6 = table_data.cell(1, 6).merge(table_data.cell(num_rows, 6))
    else:
        c0 = table_data.cell(1, 0)
        c1 = table_data.cell(1, 1)
        c6 = table_data.cell(1, 6)

    for c, val in [(c0, f"Tháng {month}"), (c1, w_name), (c6, "Claim DC 100%")]:
        c.vertical_alignment = WD_CELL_VERTICAL_ALIGNMENT.CENTER
        p = c.paragraphs[0]
        p.text = ""
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        p.paragraph_format.line_spacing = 1.15
        p.paragraph_format.space_before = Pt(2)
        p.paragraph_format.space_after = Pt(2)
        r = p.add_run(val)
        r.font.size = Pt(9)
        r.font.name = "Times New Roman"

    # Dòng Tổng cộng Grand Total (index num_rows + 1)
    tot_sl_str = f"({tot_sl:,.0f})" if tot_sl else "-"
    tot_pre_str = f"({tot_pre:,.0f})" if tot_pre else "-"
    tot_post_str = f"({tot_post:,.0f})" if tot_post else "-"
    last_row_vals = ["", "Grand Total", "", tot_sl_str, tot_pre_str, tot_post_str, ""]

    for j, val in enumerate(last_row_vals):
        cell = table_data.cell(num_rows + 1, j)
        cell.width = col_widths[j]
        p = cell.paragraphs[0]
        p.paragraph_format.line_spacing = 1.15
        p.paragraph_format.space_before = Pt(2)
        p.paragraph_format.space_after = Pt(2)
        if j in [3, 4, 5]:
            p.alignment = WD_ALIGN_PARAGRAPH.RIGHT
        elif j == 1:
            p.alignment = WD_ALIGN_PARAGRAPH.LEFT
        else:
            p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        r = p.add_run(val)
        r.bold = True
        r.font.size = Pt(9.5)
        r.font.name = "Times New Roman"
        set_cell_margins(cell, 60, 60, 60, 60)
        set_cell_border(cell, top=dict(val='single', sz='6', color='000000'),
                              bottom=dict(val='single', sz='6', color='000000'),
                              left=dict(val='single', sz='6', color='000000'),
                              right=dict(val='single', sz='6', color='000000'))

    # 6. Chi tiết diễn giải bên dưới bảng
    p_exp = doc.add_paragraph()
    p_exp.paragraph_format.space_before = Pt(10)
    p_exp.paragraph_format.space_after = Pt(6)
    p_exp.paragraph_format.line_spacing = 1.25
    p_exp.alignment = WD_ALIGN_PARAGRAPH.LEFT
    
    words = num_to_vietnamese_words(tot_post, include_dong=True)

    r_b1 = p_exp.add_run(f"• Chi phí {w_name} T{month}/{year} (VAT): ")
    r_b1.font.size = Pt(10.5)
    r_b1.font.name = "Times New Roman"
    
    r_b1_amt = p_exp.add_run(f"{tot_post:,.0f} VNĐ\n")
    r_b1_amt.bold = True
    r_b1_amt.font.size = Pt(10.5)
    r_b1_amt.font.name = "Times New Roman"

    r_b2 = p_exp.add_run(
        f"- Tổng giá trị chênh lệch kho: ({tot_pre:,.0f}) VNĐ (Chưa VAT)\n"
        f"- Tỷ lệ quy trách nhiệm: DC (SCF) chịu 100% giá trị.\n"
        f"(Bằng chữ: {words})"
    )
    r_b2.font.size = Pt(10.5)
    r_b2.font.name = "Times New Roman"

    # 7. Điều 2 & Điều 3
    p_d2 = doc.add_paragraph()
    p_d2.paragraph_format.space_before = Pt(6)
    p_d2.paragraph_format.space_after = Pt(12)
    p_d2.paragraph_format.line_spacing = 1.25
    p_d2.alignment = WD_ALIGN_PARAGRAPH.LEFT
    
    r_d2_t = p_d2.add_run("Điều 2: ")
    r_d2_t.bold = True
    r_d2_t.font.size = Pt(10.5)
    r_d2_t.font.name = "Times New Roman"
    r_d2 = p_d2.add_run(f"Khoản truy thu này sẽ được ghi nhận vào điều chỉnh năm {year}.\n")
    r_d2.font.size = Pt(10.5)
    r_d2.font.name = "Times New Roman"
    
    r_d3_t = p_d2.add_run("Điều 3: ")
    r_d3_t.bold = True
    r_d3_t.font.size = Pt(10.5)
    r_d3_t.font.name = "Times New Roman"
    r_d3 = p_d2.add_run("Quyết định có hiệu lực kể từ ngày ký. Các Phòng Ban SCF, KFM có nghĩa vụ thực hiện theo quyết định này.")
    r_d3.font.size = Pt(10.5)
    r_d3.font.name = "Times New Roman"

    # 8. Bảng Ký Tên 2 Cột Cân Đối Hoàn Toàn (Không viền)
    table_sign = doc.add_table(rows=1, cols=2)
    table_sign.alignment = WD_TABLE_ALIGNMENT.CENTER
    table_sign.autofit = False
    table_sign.columns[0].width = Inches(3.24)
    table_sign.columns[1].width = Inches(3.24)

    scf_name = data.get('representative_scf', 'Nguyễn Ngọc Xuân Quang')
    kfm_name = data.get('representative_kfm', 'Nguyễn Hoàng Lâm')
    if kfm_name == 'NGUYỄN HOÀNG LÂM':
        kfm_name = 'Nguyễn Hoàng Lâm'

    # Cột Trái: Đại diện SCF
    s0 = table_sign.cell(0, 0)
    ps0 = s0.paragraphs[0]
    ps0.alignment = WD_ALIGN_PARAGRAPH.CENTER
    ps0.paragraph_format.line_spacing = 1.15
    ps0.paragraph_format.space_after = Pt(0)
    
    r_scf_t = ps0.add_run("Đại diện SCF\n")
    r_scf_t.bold = True
    r_scf_t.font.size = Pt(10.5)
    r_scf_t.font.name = "Times New Roman"
    
    r_scf_sub = ps0.add_run("(Ký, họ tên)\n\n\n\n\n")
    r_scf_sub.font.italic = True
    r_scf_sub.bold = False
    r_scf_sub.font.size = Pt(10)
    r_scf_sub.font.name = "Times New Roman"
    
    r_scf_n = ps0.add_run(f"{scf_name}")
    r_scf_n.bold = True
    r_scf_n.font.size = Pt(10.5)
    r_scf_n.font.name = "Times New Roman"

    # Cột Phải: Đại diện KFM
    s1 = table_sign.cell(0, 1)
    ps1 = s1.paragraphs[0]
    ps1.alignment = WD_ALIGN_PARAGRAPH.CENTER
    ps1.paragraph_format.line_spacing = 1.15
    ps1.paragraph_format.space_after = Pt(0)
    
    r_kfm_t = ps1.add_run("Đại diện KFM\n")
    r_kfm_t.bold = True
    r_kfm_t.font.size = Pt(10.5)
    r_kfm_t.font.name = "Times New Roman"
    
    r_kfm_sub = ps1.add_run("(Ký, họ tên)\n\n\n\n\n")
    r_kfm_sub.font.italic = True
    r_kfm_sub.bold = False
    r_kfm_sub.font.size = Pt(10)
    r_kfm_sub.font.name = "Times New Roman"
    
    r_kfm_n = ps1.add_run(f"{kfm_name}")
    r_kfm_n.bold = True
    r_kfm_n.font.size = Pt(10.5)
    r_kfm_n.font.name = "Times New Roman"

    doc.save(output_path)
    return output_path


# --- 2. TẠO ĐỀ NGHỊ THANH TOÁN (.DOCX) ---
def generate_de_nghi_thanh_toan_docx(data, output_path):
    doc = docx.Document()
    
    # Chuẩn căn lề văn bản hành chính Việt Nam (Nghị định 30/2020/NĐ-CP):
    for sec in doc.sections:
        sec.top_margin = Inches(0.79)
        sec.bottom_margin = Inches(0.79)
        sec.left_margin = Inches(1.0)
        sec.right_margin = Inches(0.79)

    # 1. Header Table
    table_header = doc.add_table(rows=1, cols=2)
    table_header.alignment = WD_TABLE_ALIGNMENT.CENTER
    table_header.autofit = False
    table_header.columns[0].width = Inches(3.15)
    table_header.columns[1].width = Inches(3.33)

    c0 = table_header.cell(0, 0)
    p0 = c0.paragraphs[0]
    p0.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p0.paragraph_format.line_spacing = 1.15
    p0.paragraph_format.space_after = Pt(0)
    r0 = p0.add_run("CÔNG TY CỔ PHẦN KINGFOOD MARKET\n")
    r0.bold = True
    r0.font.size = Pt(10.5)
    r0.font.name = "Times New Roman"
    r0_sub = p0.add_run("---------o0o---------")
    r0_sub.font.size = Pt(10.5)
    r0_sub.font.name = "Times New Roman"

    c1 = table_header.cell(0, 1)
    p1 = c1.paragraphs[0]
    p1.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p1.paragraph_format.line_spacing = 1.15
    p1.paragraph_format.space_after = Pt(0)
    r1 = p1.add_run("CỘNG HÒA XÃ HỘI CHỦ NGHĨA VIỆT NAM\nĐộc Lập – Tự Do – Hạnh Phúc\n")
    r1.bold = True
    r1.font.size = Pt(10.5)
    r1.font.name = "Times New Roman"
    
    doc_date_str = data.get('doc_date', datetime.now().strftime('%d/%m/%Y'))
    try:
        dp = doc_date_str.split('/')
        date_text = f"TP.HCM, ngày {dp[0]} tháng {dp[1]} năm {dp[2]}"
    except:
        date_text = f"TP.HCM, ngày {datetime.now().day} tháng {datetime.now().month} năm {datetime.now().year}"
        
    r1_sub = p1.add_run(f"---------o0o---------\n{date_text}")
    r1_sub.font.italic = True
    r1_sub.font.size = Pt(10)
    r1_sub.font.name = "Times New Roman"

    for row in table_header.rows:
        for cell in row.cells:
            set_cell_border(cell)

    # 2. Tiêu đề ĐỀ NGHỊ THANH TOÁN
    p_title = doc.add_paragraph()
    p_title.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p_title.paragraph_format.space_before = Pt(14)
    p_title.paragraph_format.space_after = Pt(6)
    p_title.paragraph_format.line_spacing = 1.15
    r_t1 = p_title.add_run("ĐỀ NGHỊ THANH TOÁN\n")
    r_t1.bold = True
    r_t1.font.size = Pt(13.5)
    r_t1.font.name = "Times New Roman"
    
    w_name = data.get('warehouse_name', 'KHO SEEDLOG').upper()
    month = data.get('month', '07')
    year = data.get('year', '2026')
    w_title = "SLG" if ("SEEDLOG" in w_name or "TỔNG" in w_name or "SLG" in w_name) else w_name
    
    r_t2 = p_title.add_run(f"V/v Đề nghị thanh toán tiền truy thu {w_title} – Hủy hàng tháng {month}/{year}")
    r_t2.font.italic = True
    r_t2.font.size = Pt(11)
    r_t2.font.name = "Times New Roman"

    # 3. Kính gửi
    p_kg = doc.add_paragraph()
    p_kg.paragraph_format.space_before = Pt(8)
    p_kg.paragraph_format.space_after = Pt(6)
    p_kg.paragraph_format.line_spacing = 1.15
    r_kg_t = p_kg.add_run("Kính gửi: ")
    r_kg_t.bold = True
    r_kg_t.font.size = Pt(10.5)
    r_kg_t.font.name = "Times New Roman"
    r_kg = p_kg.add_run("CÔNG TY CỔ PHẦN SEEDCOM FOOD")
    r_kg.bold = True
    r_kg.font.size = Pt(10.5)
    r_kg.font.name = "Times New Roman"

    # 4. Căn cứ & Đề nghị thanh toán
    inv_list = data.get('invoices', [])
    vat_type = data.get('vat_type', 'Chưa VAT')
    is_post_vat = ('gồm' in vat_type.lower())
    vat_label = 'Gồm VAT' if is_post_vat else 'Chưa VAT'

    if inv_list and len(inv_list) > 1:
        tot_pre = sum(it.get('pre_tax', 0.0) for it in inv_list)
        tot_post = sum(it.get('post_tax', 0.0) for it in inv_list)
        amt_val = tot_post if is_post_vat else tot_pre
    else:
        amt_val = abs(float(data.get('total_amount', 0)))

    amt_str = f"{amt_val:,.0f}".replace(',', '.')
    words_no_dong = num_to_vietnamese_words(amt_val, include_dong=False)
    
    wh_desc = "kho linker (DC)" if ("SEEDLOG" in w_name or "TỔNG" in w_name or "SLG" in w_name) else w_name
    p_cc = doc.add_paragraph()
    p_cc.paragraph_format.space_before = Pt(4)
    p_cc.paragraph_format.space_after = Pt(6)
    p_cc.paragraph_format.line_spacing = 1.15
    p_cc.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
    r_cc = p_cc.add_run(
        f"- Căn cứ vào kết quả Hủy hàng tại {wh_desc} trong tháng {month}/{year}\n"
        f"- Căn cứ vào kết quả đối chiếu, kiểm tra chứng từ của KFM và SCF"
    )
    r_cc.font.size = Pt(10.5)
    r_cc.font.name = "Times New Roman"
    
    p_req = doc.add_paragraph()
    p_req.paragraph_format.space_before = Pt(4)
    p_req.paragraph_format.space_after = Pt(6)
    p_req.paragraph_format.line_spacing = 1.15
    p_req.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
    
    r_req1 = p_req.add_run("Chúng tôi kính đề nghị quý Công ty thanh toán số tiền là: ")
    r_req1.font.size = Pt(10.5)
    r_req1.font.name = "Times New Roman"
    
    r_amt = p_req.add_run(f"{amt_str} ({vat_label})\n")
    r_amt.bold = True
    r_amt.font.size = Pt(10.5)
    r_amt.font.name = "Times New Roman"
    
    r_words = p_req.add_run(f"(Bằng chữ: {words_no_dong}.)")
    r_words.font.italic = True
    r_words.font.size = Pt(10.5)
    r_words.font.name = "Times New Roman"
    
    b_acc = data.get('bank_account', '04001010091039')
    b_owner = data.get('bank_owner', 'CÔNG TY CỔ PHẦN KINGFOOD MARKET')
    b_name = data.get('bank_name', 'HANG HAI (MARITIMEBANK-MSB)')
    
    p_bank_intro = doc.add_paragraph()
    p_bank_intro.paragraph_format.space_before = Pt(4)
    p_bank_intro.paragraph_format.space_after = Pt(4)
    p_bank_intro.paragraph_format.line_spacing = 1.15
    p_bank_intro.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
    r_bi = p_bank_intro.add_run("Số tiền trên đề nghị chuyển vào tài khoản:")
    r_bi.font.size = Pt(10.5)
    r_bi.font.name = "Times New Roman"

    # Bảng thông tin tài khoản ngân hàng chuẩn 2 hàng, kẻ viền đen theo mẫu chuẩn Ảnh 1
    table_bank = doc.add_table(rows=2, cols=4)
    table_bank.alignment = WD_TABLE_ALIGNMENT.CENTER
    table_bank.autofit = False
    col_widths = [Inches(1.4), Inches(1.8), Inches(1.3), Inches(1.98)]

    # Hàng 1
    c00 = table_bank.cell(0, 0)
    c00.width = col_widths[0]
    p00 = c00.paragraphs[0]
    p00.paragraph_format.line_spacing = 1.15
    r00 = p00.add_run("Số tài khoản:")
    r00.font.italic = True
    r00.font.size = Pt(10)
    r00.font.name = "Times New Roman"

    c01 = table_bank.cell(0, 1)
    c01.width = col_widths[1]
    p01 = c01.paragraphs[0]
    p01.paragraph_format.line_spacing = 1.15
    r01 = p01.add_run(str(b_acc))
    r01.font.size = Pt(10)
    r01.font.name = "Times New Roman"

    c02 = table_bank.cell(0, 2)
    c02.width = col_widths[2]
    p02 = c02.paragraphs[0]
    p02.paragraph_format.line_spacing = 1.15
    r02 = p02.add_run("Chủ tài khoản:")
    r02.font.italic = True
    r02.font.size = Pt(10)
    r02.font.name = "Times New Roman"

    c03 = table_bank.cell(0, 3)
    c03.width = col_widths[3]
    p03 = c03.paragraphs[0]
    p03.paragraph_format.line_spacing = 1.15
    owner_str = "CÔNG TY CỔ PHẦN\nKINGFOOD MARKET" if "KINGFOOD MARKET" in b_owner else b_owner
    r03 = p03.add_run(owner_str)
    r03.font.size = Pt(10)
    r03.font.name = "Times New Roman"

    # Hàng 2: Mở tại ngân hàng: | HANG HAI (MARITIMEBANK-MSB)
    c10 = table_bank.cell(1, 0)
    c10.width = col_widths[0]
    p10 = c10.paragraphs[0]
    p10.paragraph_format.line_spacing = 1.15
    r10 = p10.add_run("Mở tại ngân hàng:")
    r10.font.italic = True
    r10.font.size = Pt(10)
    r10.font.name = "Times New Roman"

    c11 = table_bank.cell(1, 1)
    c13 = table_bank.cell(1, 3)
    c_merged = c11.merge(c13)
    p11 = c_merged.paragraphs[0]
    p11.paragraph_format.line_spacing = 1.15
    r11 = p11.add_run(b_name)
    r11.font.size = Pt(10)
    r11.font.name = "Times New Roman"

    for r in table_bank.rows:
        for c in r.cells:
            set_cell_margins(c, top=60, bottom=60, left=70, right=70)
            set_cell_border(c, top=dict(val='single', sz='4', color='000000'),
                               bottom=dict(val='single', sz='4', color='000000'),
                               left=dict(val='single', sz='4', color='000000'),
                               right=dict(val='single', sz='4', color='000000'))

    p_close = doc.add_paragraph()
    p_close.paragraph_format.space_before = Pt(4)
    p_close.paragraph_format.space_after = Pt(12)
    p_close.paragraph_format.line_spacing = 1.15
    p_close.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
    r_close = p_close.add_run(
        f"Kính mong Quý Công ty vui lòng thanh toán đúng thời hạn số tiền trên.\n"
        f"Trân trọng kính chào!"
    )
    r_close.font.size = Pt(10.5)
    r_close.font.name = "Times New Roman"

    # 5. Chữ ký TM. TỔNG GIÁM ĐỐC (Dùng Table căn phải hoàn hảo, không lệch lề)
    table_sign = doc.add_table(rows=1, cols=2)
    table_sign.alignment = WD_TABLE_ALIGNMENT.CENTER
    table_sign.autofit = False
    table_sign.columns[0].width = Inches(3.24)
    table_sign.columns[1].width = Inches(3.24)

    s1 = table_sign.cell(0, 1)
    ps1 = s1.paragraphs[0]
    ps1.alignment = WD_ALIGN_PARAGRAPH.CENTER
    ps1.paragraph_format.line_spacing = 1.15
    ps1.paragraph_format.space_after = Pt(0)
    
    kfm_name = data.get('representative_kfm', 'NGUYỄN HOÀNG LÂM')
    r_sg_t = ps1.add_run("TM. TỔNG GIÁM ĐỐC\n\n\n\n\n")
    r_sg_t.bold = True
    r_sg_t.font.size = Pt(10.5)
    r_sg_t.font.name = "Times New Roman"
    
    r_sg_n = ps1.add_run(f"{kfm_name}")
    r_sg_n.bold = True
    r_sg_n.font.size = Pt(10.5)
    r_sg_n.font.name = "Times New Roman"

    for row in table_sign.rows:
        for cell in row.cells:
            set_cell_border(cell)

    doc.save(output_path)
    return output_path
