import re
from config import CATEGORY_RULES, PRIORITY_KEYWORDS, EXCLUDED_GROUPS

EXCLUDED_SENDERS = [
    "thư đoàn",
    "sc017084",
    "minhthudoan",
    "đối soát scm"
]

EXCLUDE_CHATTER_PATTERNS = [
    # 1. Xác nhận nhận đúng / nhận đủ -> BỎ QUA HOÀN TOÀN
    "thực nhận đúng",
    "thuc nhan dung",
    "nhận đúng",
    "nhan dung",
    "nhận đủ",
    "nhan du",
    "sthị nhận đúng",
    "st nhận đúng",
    "st thực nhận đúng",
    "nhận đúng ạ",
    "nhận đúng a",
    "bạn nhận đúng",
    "nhập đúng tn",
    "nhập đúng tn rồi",
    "đúng tn rồi",
    "nhận đủ ạ",
    "nhận đủ a",
    "nhận đúng sl",
    "nhận đúng theo phiếu",
    "nhận đúng trên phiếu",
    "đúng theo phiếu",
    "đúng trên phiếu",
    "chụp trên kdb",
    "coa chụp trên kdb",
    "kéo data về dashboard",
    "giá trung bình của mã",
    "nguyên nhân mất bot",

    
    # 2. Tin tự hỏi hoặc nhắc nhở
    "check giúp thư",
    "check lại giúp thư",
    "báo giúp thư",
    "gửi giúp thư",
    "chưa thấy st add hàng dư",
    
    # 3. Caption ảnh / câu cụt không có số liệu
    "xác nhận thiếu",
    "xac nhan thieu",
    "các hàng đó bị thiếu",
    "st báo md hỗ trợ",
    "báo md hỗ trợ",
    "không về 2 mã này",
    "không về mã này",
    "em gửi mã hàng giao thiếu",
    "em gửi số lượng hàng thiếu",
    "hàng rau củ thiếu ngày",
    "các mã thiếu và dư",
    "các mã thiếu",
    "em gửi mã giao thiếu",
    "em gửi hình ảnh thiếu",
    "gửi mã thiếu",
    "hàng thiếu nha",
    "hàng thiếu sáng nay",
    "sáng giao thiếu mấy sản phẩm này",
    "2 món này thiếu hàng",
    "mã không về",
    "sáng nay không về",
    "thiếu 1 gói nha chị",
    "thiếu 1 gói nha chi",
    "hàng dư vượt sức bán st báo giúp",
    "hàng dư vượt sức bán",
    
    # 4. Trò chuyện cá nhân / vị trí / chìa khoá / tài xế
    "em ở với em bé",
    "tài xế đứng ngay",
    "nhân viên tên trung",
    "nhân viên tên",
    "hướng dẫn mấy tx",
    "khoan khoá ổ",
    "khoá ổ",
    "phá khóa",
    "phá khoá",
    "ổ khóa",
    "ổ khoá",
    "chìa khóa",
    "chìa khoá",
    "mở ko đc",
    "mở không được",
    "mã mở",
    "pass mở",
    "trên cửa đi",
    "cho em xin 5",
    "cho em xin 10",
    "plssss",
    "để em báo tx",
    "để e báo tx",
    "bên mình còn ai ko",
    "còn ai ở st ko",
    "mở cửa nhận hàng",
    "hỗ trợ mở cửa",
    "tài xế đến rồi",
    "tai xe den roi",
    "tài xế đã tới",
    "tài xế đến nơi",
    "tài xế đang di chuyển",
    "xe đang di chuyển",
    "xe đang đi",
    "tài xế đang tới",
    "thông tin xe giao hàng",
    "xe giao hàng đông mát",
    
    # 5. Phiếu rút tồn / Remind / Chỉ đạo tạo phiếu
    "phiếu rút tồn",
    "gửi phiếu rút tồn",
    "rút tồn trứng bể",
    "gửi phiếu bs chênh lệch",
    "gửi phiếu bổ sung chênh lệch",
    "gửi phiếu bs",
    "ny gửi phiếu",
    "từ chối xử lý",
    "hoàn thành phiếu",
    "phiếu hậu kiểm",
    "lưu ý quan trọng",
    "anh remind",
    "hi gsm/sm",
    "hi team",
    "sau thời gian trên",
    "đóng case này ko hỗ trợ",
    "đóng case này",
    "ko hỗ trợ xử lý nữa",
    "st tạo phiếu về krc",
    "ghi ngày trên ggsheet",
    "ggsheet theo 1 định dạng",
    "ggsheet",
    
    # 6. Tin tự động / Broadcast / Bot thông báo
    "[kfm - scm team]",
    "kfm - scm team",
    "st lưu ý bắt đầu từ nay trở về sau",
    "hoa st nhập đủ sl",
    "chuyển tồn về kho giảm chất lượng",
    "[bot]",
    "kfm_bot",
    "thông báo từ hệ thống",
    "scm thông báo",
    "thông báo quan trọng",
    "nhắc nhở vận hành"
]

def is_group_excluded(chat_title: str) -> bool:
    if not chat_title:
        return False
    lower_title = chat_title.lower()
    for exc in EXCLUDED_GROUPS:
        if exc.lower() in lower_title:
            return True
    return False

def is_chatter_or_resolved(text: str, sender_name: str = "") -> bool:
    if not text:
        return True
        
    lower_sender = (sender_name or "").lower()
    for exc_sender in EXCLUDED_SENDERS:
        if exc_sender in lower_sender:
            return True

    clean_text = text.strip()
    
    cleaned_no_tags = re.sub(r'\[.*?\]\(tg://user\?id=\d+\)', '', clean_text).strip()
    cleaned_no_tags = re.sub(r'@\w+', '', cleaned_no_tags).strip()
    if len(cleaned_no_tags) < 4:
        return True
    
    if len(clean_text) < 18:
        if not any(k in clean_text.lower() for k in ["bể", "vỡ", "dập", "trứng", "kg", "pt"]):
            return True
        if clean_text.isdigit():
            return True
            
    lower_text = clean_text.lower()

    for pattern in EXCLUDE_CHATTER_PATTERNS:
        if pattern in lower_text:
            return True
            
    return False

def detect_issue_type(text: str) -> str:
    if not text:
        return "Khác"
    lower = text.lower()
    
    # 1. Sự cố Tài xế / Vận hành / Giao trễ / Hụt xe / Sự cố xe
    driver_patterns = [
        r'\bhụt xe\b', r'\bsự cố\b', r'\bquay đầu\b', r'\bxe hỏng\b', r'\bhư xe\b', r'\bchết máy\b',
        r'\bbể bánh\b', r'\bthủng lốp\b', r'\btìm xe\b', r'\bđiều xe\b', r'\bbáo muộn\b', r'\bgiao muộn\b',
        r'\btheo lịch\b', r'\bchưa thấy giao\b', r'\bchưa giao\b', r'\bchưa tới\b', r'\btrễ\b', r'\bchậm\b',
        r'\bgiao trễ\b', r'\bgiao sai\b', r'\bgiao nhầm\b', r'\bgiao lộn\b', r'\bva quẹt\b',
        r'\blàm bể\b', r'\blàm vỡ\b', r'\blàm hỏng\b', r'\bhư cơ sở\b', r'\bkhiếu nại tài xế\b', r'\btài xế\b'
    ]
    for dp in driver_patterns:
        if re.search(dp, lower):
            return "Sự cố Tài xế"

    # 2. Thiếu & Thừa (Chênh lệch số lượng)
    # Lưu ý: Loại trừ 'hụt xe' ra khỏi 'hụt'
    cleaned_lower_for_thieu = re.sub(r'hụt\s+xe', '', lower)
    has_thieu = bool(re.search(r'\b(thiếu|giao thiếu|nhận thiếu|thiếu hàng|không về|nhập thiếu|hụt hàng)\b', cleaned_lower_for_thieu))
    has_thua = bool(re.search(r'\b(thừa|giao thừa|dư|thừa hàng|hàng dư|nhập dư|giao dư)\b', lower))

    # 3. XCL (Chất lượng: bể, vỡ, nứt, dập, hỏng thực tế)
    xcl_patterns = [
        r'\b(nứt|bể|vỡ|dập|hư hỏng|thối|chảy nước|chảy dịch|rách bao|hở bao|kém chất lượng)\b',
        r'\b(bị úng|rau úng|bị héo|rau héo)\b'
    ]
    has_xcl = False
    for xp in xcl_patterns:
        if re.search(xp, lower):
            has_xcl = True
            break

    if has_xcl and not (has_thieu or has_thua):
        return "XCL"
    if has_thieu and not has_thua:
        return "Thiếu"
    if has_thua and not has_thieu:
        return "Thừa"
    if has_thieu and has_thua:
        return "Thiếu"
    if has_xcl:
        return "XCL"
        
    return "Khác"

def classify_message(text: str, sender_name: str = "", chat_title: str = "") -> dict:
    if not text:
        return {"category": "Khác", "priority": "P3", "issue_type": "Khác"}

    if is_group_excluded(chat_title):
        return None
    if is_chatter_or_resolved(text, sender_name):
        return None

    issue_type = detect_issue_type(text)

    # Priority
    priority = "P3"
    lower_text = text.lower()
    for kw in PRIORITY_KEYWORDS.get("P1", []):
        if kw in lower_text:
            priority = "P1"
            break
    if priority == "P3":
        for kw in PRIORITY_KEYWORDS.get("P2", []):
            if kw in lower_text:
                priority = "P2"
                break
    if issue_type == "Sự cố Tài xế" and priority == "P3":
        priority = "P2"

    # Category Group
    category = "Khác"
    chat_lower = (chat_title or "").lower()
    if "đối soát" in chat_lower or "đối soát" in lower_text:
        category = "KRC - Đối soát"
    elif any(k in chat_lower for k in ["aba", "đông mát", "thịt", "cá", "meat", "fish", "mđ", "nlvj", "trứng", "bqi", "đông hưng", "dong hung", "bách hóa", "má đùi", "heo", "gà", "bò"]):
        category = "Đông mát thịt cá"
    elif any(k in chat_lower for k in ["dc", "kho tổng", "tdc", "ghknn", "hub"]):
        category = "DC"
    elif any(k in chat_lower for k in ["krc", "rau", "củ", "quả", "trái cây", "nông sản"]):
        category = "KRC"
    else:
        category = "KRC"

    return {
        'category': category,
        'priority': priority,
        'issue_type': issue_type
    }

