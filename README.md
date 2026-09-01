# Hướng Dẫn Vận Hành Kingfood SCM Auto-Check Userbot

## 1. Tính Năng Chính
- **Tàng hình 100%:** Chạy bằng tài khoản của bạn, không cần add bot lạ vào nhóm.
- **Tự động Phân loại:**
  - Kho & Phiếu Chuyển
  - Hàng Tươi Sống (Fresh: Thịt, Cá, Rau Củ)
  - Hàng Khô & FMCG
  - Đơn Hàng & Giao Vận (Delivery, Shipper)
  - Thu Ngân & Vận Hành Siêu Thị
- **Chấm điểm Ưu tiên:**
  - 🔴 **P1 (Khẩn cấp):** Bắn tin nhắn cảnh báo tức thì vào mục **"Tin nhắn đã lưu" (Saved Messages)** của bạn trên Telegram.
  - 🟡 **P2 (Cần xử lý):** Lưu vào danh sách chờ duyệt / xử lý.
  - 🟢 **P3 (Thông tin):** Ghi nhật ký đầy đủ.
- **Lưu trữ CSDL:** SQLite cục bộ (`scm_monitor.db`).

---

## 2. Cách Khởi Động Lần Đầu

1. Mở thư mục `kingfood_scm_bot`.
2. Bấm đúp chuột vào file **`start_bot.bat`**.
3. **Chỉ trong lần đầu tiên**, cửa sổ đen sẽ hỏi:
   - `Please enter your phone (or bot_token):` -> Nhập số điện thoại Telegram của bạn (ví dụ: `+84901234567`).
   - `Please enter the code you received:` -> Nhập mã 5 chữ số mà Telegram gửi vào ứng dụng Telegram của bạn.
   - *(Nếu tài khoản có bật mật khẩu 2 lớp: Nhập thêm password 2FA).*
4. Sau khi đăng nhập thành công, bot sẽ tạo file `kingfood_scm_session.session`.
5. Từ các lần sau, bạn chỉ cần bấm `start_bot.bat` là bot tự động chạy ngầm ngay lập tức mà không cần đăng nhập lại.

---

## 3. Các Lệnh Tra Cứu Nhanh (Gửi trong mục "Saved Messages" của bạn)

Bạn mở Telegram, vào mục **Tin nhắn đã lưu (Saved Messages)** và gõ:
- `.summary` : Xem báo cáo tổng hợp nhanh tình hình hôm nay.
- `.urgent` hoặc `.p1` : Xem danh sách các case khẩn cấp tồn đọng.
- `.stats` : Xem thống kê số lượng tin theo từng ngành hàng.
- `.ping` : Kiểm tra xem bot có đang chạy ngầm hay không.
