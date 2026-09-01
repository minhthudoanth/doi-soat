import os

# Telegram API Credentials
API_ID = 37416990
API_HASH = "65e816fcc7ad12b08a53fa9710245b58"
SESSION_NAME = "kingfood_scm_session"

# Database path
DB_PATH = os.path.join(os.path.dirname(__file__), "scm_monitor.db")

# DANH SÁCH CÁC NHÓM CẦN BỎ QUA HOÀN TOÀN
EXCLUDED_GROUPS = [
    "RAU - Vấn đề chất lượng (CATE - STORE)",
    "CATE - STORE - THỊT, CÁ, TRỨNG, VN READY MEAL",
    "RAU - Vấn đề chất lượng",
    "CATE - STORE",
    "Xuất Bill",
    "Xuất Bill (Đầu ST) cho VT",
    "Xuat Bill",
    "hình ảnh chênh lệch",
    "SCM - KRC (hình ảnh chênh lệch)",
    "SCM - ĐÔNG MÁT (hình ảnh chênh lệch)",
    "IC - KDB - KRC",
    "IC - KDB - ĐÔNG MÁT",
    "IC - KDB",
    "KDB",
    "Logistic _ Inventory",
    "Logistic - Inventory",
    "Logistic",
    "Logistic KFM",
    "Inventory",
    "Nội bộ",
    "Nội Bộ",
    "nội bộ",
    "noi bo",
    "LOG - Xử lý lệch nội bộ",
    "LOG -",
    "SCM- KRC Nội bộ",
    "SCM - KRC Nội bộ"
]



# 4 PHÂN LOẠI SỰ CỐ CHUẨN SCM
SCM_CATEGORIES_EXACT = {
    "XCL (Chất lượng)": [
        "xcl", "bể", "be", "vỡ", "vo", "dập", "dap", "nứt", "nut", "úng", "ung",
        "ướt", "uot", "xẹp", "xep", "gãy", "gay", "héo", "heo", "hư hỏng", "thối",
        "chảy nước", "chảy dịch", "rách bao", "hở bao", "kém chất lượng", "kdb", "sâu"
    ],
    "Thiếu": [
        "thiếu", "thieu", "báo thiếu", "giao thiếu", "nhận thiếu", "hụt", "thiếu hàng",
        "không có trong kiện", "chưa nhận được", "thiếu sl", "không về"
    ],
    "Thừa": [
        "thừa", "thua", "báo thừa", "giao thừa", "dư", "thừa hàng", "hàng dư", "dư sl",
        "thừa sl", "nhập dư"
    ]
}

# 3 Nhóm ngành chính
CATEGORY_RULES = {
    "KRC - Đối soát": [
        "đối soát", "doi soat", "chênh lệch", "lệch phiếu", "xác nhận số lượng"
    ],
    "KRC": [
        "krc", "rau", "củ", "quả", "trái cây", "nông sản"
    ],
    "Đông mát thịt cá": [
        "thịt", "cá", "hải sản", "heo", "bò", "gà", "đông mát", "kho mát", "tủ đông", "trứng"
    ],
    "DC": [
        "dc", "kho tổng", "phiếu chuyển", "điều chuyển", "nhập kho", "xuất kho", "tồn kho"
    ]
}

# Ma trận ưu tiên
PRIORITY_KEYWORDS = {
    "P1": ["gấp", "khẩn", "khẩn cấp", "ngay lập tức", "hỏng nặng", "khiếu nại"],
    "P2": ["cần duyệt", "chưa duyệt", "xử lý giúp", "check giúp", "chênh lệch", "thiếu", "thừa", "xcl"]
}
