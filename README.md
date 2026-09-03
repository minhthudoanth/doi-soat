# 🥑 HỆ THỐNG ĐỐI SOÁT & THEO DÕI VẬN HÀNH KINGFOOD SCM

Hệ thống tự động hóa giám sát tin nhắn Telegram và Dashboard đối soát vận hành dành riêng cho bộ phận SCM Kingfoodmart.

---

## 🌐 1. ĐỊA CHỈ TRUY CẬP DASHBOARD

* **Đường link chính thức:** [http://doi-soat.local:5000](http://doi-soat.local:5000)
* **Đường link dự phòng:** [http://127.0.0.1:5000](http://127.0.0.1:5000) hoặc [http://localhost:5000](http://localhost:5000)
* **Đường link mạng nội bộ (mở bằng điện thoại/máy cùng Wi-Fi):** `http://[IP_MÁY_BẠN]:5000` (ví dụ: `http://192.168.1.219:5000`)

> 💡 **Cài đặt tên miền cố định:** Nhấp chuột phải vào file `CAU_HINH_LINK_CO_DINH.bat` ➔ Chọn **Run as administrator** (làm 1 lần duy nhất).

---

## 🚀 2. HƯỚNG DẪN KHỞI ĐỘNG HÀNG NGÀY

### ⭐ Cách 1: Nhanh nhất (Khuyên dùng hàng ngày - 1 Click)
* Ra ngoài màn hình **Desktop**, nhấp đúp vào icon shortcut:
  👉 **`DOI_SOAT_KRC`**
* **Cơ chế:** Tự động bật Bot Telegram và Web Dashboard **chạy ngầm hoàn toàn** (không làm phiền bằng cửa sổ đen CMD). Sau ~2 giây trình duyệt sẽ tự động mở web lên.
* Khi tắt trình duyệt, server ngầm vẫn chạy. Lúc nào cần xem lại chỉ cần bấm lại shortcut này.

### 🔄 Cách 2: Tự động 100% khi bật máy tính
* Nhấp đúp vào file `BAT_TU_DONG_KHOI_DONG_CUNG_WINDOWS.bat` (chạy 1 lần để cài đặt).
* Từ hôm sau, mỗi khi bật máy tính, Windows sẽ tự chạy ngầm hệ thống. Bạn chỉ cần mở trình duyệt và truy cập `http://doi-soat.local:5000`.

### 🖥️ Cách 3: Chạy có cửa sổ dòng lệnh theo dõi log
* Nhấp đúp vào `CHAY_DASHBOARD.bat`.
* **Lưu ý:** Chỉ bấm nút **Minimize (thu nhỏ `_`)**, tuyệt đối không bấm nút `X` tắt cửa sổ CMD để tránh ngắt server.

### 🛑 Tắt toàn bộ hệ thống:
* Nhấp đúp vào `DUNG_HE_THONG.bat` để dừng sạch toàn bộ tiến trình Python.

---

## ✨ 3. CÁC TÍNH NĂNG CỐT LÕI

### 1. Tab Cần Check (Bộ lọc tin nhắn thông minh)
* Lọc chuẩn xác các tin nhắn tag Thư Đoàn (`@minhthudoan`, mã NV `SC017084`, User ID `8552986824`, hoặc gọi đích danh *chị Thư, em Thư, Thư ơi, nhờ Thư*).
* Loại trừ hoàn toàn các từ gây nhiễu (*thường, thực nhận, thức ăn, thư viện...*).
* Quản lý trạng thái: Đánh dấu đã đọc / Đã xử lý / Dismiss.

### 2. Tab Đối Soát KRC (Realtime Audit)
* Tự động trích xuất thông tin: Mã PT ghi nhận, Mã PT gốc kho KRC, SKU, Tên hàng, Số lượng lệch.
* Phân định tự động: Hàng Pack đếm theo item, Hàng KG đếm theo trọng lượng thực tế.
* Tự động tính Deadline Siêu thị phản hồi: 17:00 (nếu báo sáng) hoặc 10:00 hôm sau (nếu báo chiều).
* Chuẩn hóa tỉ lệ % DONE: Chỉ tính khi đã thực sự trả tồn về ST/DC theo phiếu TO.

### 3. Đồng bộ Google Sheet & Tồn kho 24/7
* Tự động quét và đồng bộ Google Sheet Đối Soát liên tục mỗi 3 phút trên luồng độc lập.
* Đồng bộ danh sách 220+ siêu thị và tồn kho KFM API.

---

## 📦 4. ĐỒNG BỘ MÃ NGUỒN GIT

* **Đồng bộ lên GitHub:** Nhấp đúp vào file `DONG_BO_GITHUB.bat`.
  * Kho lưu trữ: [https://github.com/minhthudoanth/doi-soat](https://github.com/minhthudoanth/doi-soat)
* **Đồng bộ lên GitLab dự phòng:** Nhấp đúp vào file `DONG_BO_GITLAB.bat`.
