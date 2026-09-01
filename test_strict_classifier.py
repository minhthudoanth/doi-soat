import re

EXCLUDED_CHATTER_PATTERNS = [
    # Xác nhận nhận đúng / đủ -> BỎ QUA HOÀN TOÀN
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
    "nhận đủ ạ",
    "nhận đúng sl",
    "nhận đúng theo phiếu",
    "nhận đúng trên phiếu",
    "đúng theo phiếu",
    "đúng trên phiếu",
    
    # Nhắc nhở / giục phiếu / quy định
    "lên eform",
    "lên ticket",
    "hoàn thành phiếu",
    "phiếu hậu kiểm",
    "lưu ý quan trọng",
    "anh remind",
    "hi gsm/sm",
    "sau thời gian trên",
    "từ chối xử lý"
]

def is_chatter_message(text: str) -> bool:
    if not text:
        return True
    lower = text.lower()
    for pat in EXCLUDED_CHATTER_PATTERNS:
        if pat in lower:
            # Nếu chỉ là xác nhận nhận đúng/đủ và không có chữ thiếu/dư/bể
            if not any(k in lower for k in ["thiếu", "dư", "thừa", "bể", "dập", "nứt", "vỡ"]):
                return True
            if "nhận đúng ạ" in lower or "st thực nhận đúng" in lower or "nhận đúng sl" in lower:
                return True
    return False

def detect_issue_type_strict(text: str) -> str:
    if not text:
        return "Khác"
    lower = text.lower()
    
    # 1. Sự cố Tài xế / Vận hành / Giao trễ
    driver_patterns = [
        r'\btheo lịch\b', r'\bchưa thấy giao\b', r'\bchưa giao\b', r'\btrễ\b', r'\bchậm\b',
        r'\bgiao trễ\b', r'\bgiao sai\b', r'\bgiao nhầm\b', r'\bgiao lộn\b', r'\bva quẹt\b',
        r'\blàm bể\b', r'\blàm vỡ\b', r'\blàm hỏng\b', r'\bkhiếu nại tài xế\b'
    ]
    for dp in driver_patterns:
        if re.search(dp, lower):
            return "Sự cố Tài xế"
            
    # 2. Thiếu & Thừa (Chênh lệch số lượng)
    has_thieu = bool(re.search(r'\b(thiếu|giao thiếu|nhận thiếu|hụt|thiếu hàng|không về)\b', lower))
    has_thua = bool(re.search(r'\b(thừa|giao thừa|dư|thừa hàng|hàng dư|nhập dư)\b', lower))
    
    # 3. XCL (Chất lượng: bể, vỡ, nứt, dập, hỏng)
    # Loại trừ từ 'húng' và 'bổ sung'
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
        return "Thiếu" # hoặc Chênh lệch
    if has_xcl:
        return "XCL"
        
    return "Khác"
