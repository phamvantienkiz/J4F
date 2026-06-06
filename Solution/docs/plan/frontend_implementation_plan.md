# FRONTEND IMPLEMENTATION PLAN: BURGER AGENT

Tài liệu này đặc tả chi tiết kế hoạch triển khai (Implementation Plan) cho phân hệ **Frontend** của hệ thống **Burger Agent** (Trợ lý Danh mục POD và Tối ưu hóa Fulfillment). Kế hoạch thiết kế nhằm tạo ra một giao diện hiện đại, tối ưu hóa trải nghiệm của Seller, tích hợp liền mạch với API FastAPI Backend và AI LangGraph đã hoàn thiện.

---

## 1. Mục Tiêu Thiết Kế & Nhận Diện (Burger Agent)

1. **Thay đổi Nhận diện:** Tên gọi chính thức của dự án và nhãn hiển thị trên giao diện là **Burger Agent** (thay thế cho PrintFlow AI).
2. **Phong cách UI/UX "Pro Max":** Sử dụng triệt để các phong cách thiết kế hiện đại:
   - **Glassmorphism:** Sử dụng `backdrop-filter: blur(12px) saturate(180%)` kết hợp với viền mỏng bán trong suốt để tạo chiều sâu trực quan.
   - **Hệ màu sắc tối ưu (Sleek Dark Mode):** Nền Deep Midnight Navy (`#020617`), các thẻ Glassmorphic Navy (`#0b1129`), nhấn mạnh (Brand Accents) bằng Electric Blue (`#2563EB`) và Neon Violet (`#7C3AED`) để biểu thị trí tuệ nhân tạo (AI).
   - **Phông chữ sắc nét:** `Outfit` (Heading & Labels) kết hợp `Inter` (Body Text) và `JetBrains Mono` (Bảng so sánh số liệu).
3. **Trải nghiệm Đa phương tiện:** Tích hợp ảnh mockup thực tế cho các phôi (T-Shirt, Hoodie, Mug), phản hồi tương tác mượt mà và bắn pháo hoa (`canvas-confetti`) khi chốt đơn thành công.
4. **Cài đặt & Vận hành nhanh:** Cấu hình npm script gọn gàng, hỗ trợ chạy đồng thời với Backend thông qua hướng dẫn đơn giản.

---

## 2. Công Nghệ & Thư Viện Sử Dụng

* **Framework:** **React + TypeScript + Vite** (Khởi tạo nhanh, build siêu tốc, tối ưu hóa bundle size).
* **Styling:** **Vanilla CSS / CSS Modules** (Kiểm soát hoàn hảo từng pixel, không sử dụng Tailwind CSS để giữ tính linh hoạt và dễ tối ưu).
* **Icons:** **Lucide React** (Bộ icon SVG nhất quán, hiện đại).
* **HTTP Client:** **Axios** (Hỗ trợ cấu hình interceptor để đính kèm JWT Token tự động).
* **Hiệu ứng:** **Canvas Confetti** (Bắn pháo hoa khi đặt đơn thành công).
* **Fonts:** Nhúng Google Fonts trực tiếp trong file HTML (`Outfit`, `Inter`, `JetBrains Mono`).

---

## 3. Kiến Trúc Trang & Bố Cục Giao Diện

Ứng dụng sẽ bao gồm các thành phần chính sau:

### 3.1. Cửa Sổ Authentication (Login / Register Modal)
* **UX Flow:** Nếu chưa có JWT Token trong `localStorage`, màn hình chính sẽ bị làm mờ (`backdrop-filter: blur(8px)`). Modal đăng nhập sẽ xuất hiện ở chính giữa.
* **Fields:** 
  - Đăng nhập: Email, Password (có nút hiện/ẩn password).
  - Đăng ký: Email, Password, Store Name (POD Store Name).
* **Tích hợp:** Gọi `/api/v1/auth/login` hoặc `/api/v1/auth/register`, lưu token vào `localStorage` và chuyển sang Dashboard.

### 3.2. Dashboard Chính (3 Cột: 20% - 50% - 30%)

#### Cột 1: Left Sidebar (Quản lý Phiên & Cài Đặt) - Chiếm 20% width
* **Nút New Chat:** Khởi tạo thread mới qua `POST /api/v1/chat/conversations`.
* **Lịch sử Chat:** Liệt kê các cuộc trò chuyện từ `/api/v1/chat/conversations`, click để đổi `thread_id` đang active và tải lịch sử tin nhắn.
* **Nút User Preferences:** Mở popup/modal cấu hình các thông số mặc định của Seller:
  - Target Margin (%)
  - Max Shipping Days (SLA)
  - Priority (Margin / Speed)
  - Preferred Market (US / EU / VN)
  - Cập nhật thời gian thực về Backend qua `PUT /api/v1/auth/preference`.
* **Profile Section (Bottom):** Hiển thị Store Name, Email và nút **Đăng xuất**.

#### Cột 2: Center Panel (Khung Chat Hội Thoại Core) - Chiếm 50% width
* **Chat Message List:** Hiển thị bong bóng chat của User (lề phải, navy sáng) và Agent (lề trái, navy tối/trong suốt).
* **Interactive Table:** Nếu tin nhắn của Agent chứa metadata `comparison_table`:
  - Render bảng so sánh dạng HTML/React có highlight rõ ràng.
  - Hàng thứ nhất (Top 1 - Recommended) sẽ có border màu tím sáng và tag nhấp nháy `"BEST CHOICE / RECOMMENDED"`.
  - Mỗi hàng có nút **"Chọn Xưởng"** để tự động kích hoạt Order HUD ở Right Panel.
* **Suggestion Chips (Gợi ý nhanh):** Các nút bấm sẵn ở đáy khung chat để Seller click nhanh (ví dụ: *"Hoodie ship US dưới 5 ngày"*, *"Tìm cốc sứ margin > 40%"*).
* **Input Area:** Ô nhập chat có viền phát sáng (Glow border), hỗ trợ gửi bằng phím `Enter` hoặc click nút gửi phi thuyền.

#### Cột 3: Right Panel (Thông Tin Chi Tiết & HUD Đơn Hàng) - Chiếm 30% width
* **Thành phần 1: Product Inspector (Thông tin sản phẩm)**
  - Hiển thị Mockup chất lượng cao tương ứng với loại sản phẩm đang chat (Áo phông, Áo hoodie, Cốc sứ).
  - Hiển thị thông số chi tiết: Tên sản phẩm, bảng màu khả dụng, size khả dụng và chất liệu.
* **Thành phần 2: Order HUD (Heads-Up Display Checkout)**
  - Hiển thị tóm tắt đơn hàng đang cấu hình: Tên người nhận, Địa chỉ, SKU, Số lượng.
  - Hiển thị phân tích chi phí Landed Cost: Base cost, Printing cost, Shipping cost, Tax.
  - Nút **"Confirm Fulfillment Order"** lớn, phát sáng xanh lá/blue. Khi click, gọi endpoint `POST /api/v1/order/confirm`.
  - Khi đặt thành công: Khóa nút bấm, chuyển trạng thái sang **Completed**, bắn pháo hoa confetti tràn màn hình và hiển thị Order ID / Tracking Number.

---

## 4. Lộ Trình Triển Khai Chi Tiết (Phase-by-Phase)

### Giai đoạn 1: Khởi Tạo Môi Trường & Cấu Hình CSS Tokens (Ngày 1)
* **Tác vụ 1:** Khởi tạo dự án Vite React TS tại thư mục `Product/frontend`.
* **Tác vụ 2:** Cài đặt các dependencies cần thiết (`axios`, `lucide-react`, `canvas-confetti`, `@types/canvas-confetti`).
* **Tác vụ 3:** Thiết lập file `src/index.css` định nghĩa các CSS Variables toàn cục (Theme colors HSL, Outfit & Inter fonts, Glassmorphic border, Glow shadow effects, keyframe animations).

### Giai đoạn 2: Cổng Đăng Nhập & API Client (Ngày 2 - Sáng)
* **Tác vụ 4:** Thiết lập `src/services/api.ts` chứa Axios client, cấu hình interceptors xử lý JWT token trong header, định nghĩa các API call cho Auth, Chat, Order.
* **Tác vụ 5:** Phát triển màn hình Login/Register UI với các trường kiểm soát dữ liệu, cơ chế blur nền phía sau và lưu JWT.

### Giai đoạn 3: Bố Cục Dashboard & Left Sidebar (Ngày 2 - Chiều)
* **Tác vụ 6:** Thiết kế layout 3 cột chính.
* **Tác vụ 7:** Hoàn thiện Left Sidebar: Danh sách chat lịch sử, tạo chat mới, nút hiển thị modal Cấu hình sở thích (Preferences) với API update đồng bộ về database backend.

### Giai đoạn 4: Chat Engine & Bảng So Sánh Động (Ngày 3 - Sáng)
* **Tác vụ 8:** Lập trình Khung chat ở giữa, xử lý gửi/nhận tin nhắn không đồng bộ, tạo hiệu ứng gõ chữ hoặc loading mượt mà.
* **Tác vụ 9:** Xây dựng component so sánh candidates động từ JSON metadata, highlight lựa chọn số 1 (gợi ý từ thuật toán AI).

### Giai đoạn 5: Product Inspector & Order HUD Checkout (Ngày 3 - Chiều)
* **Tác vụ 10:** Xây dựng panel bên phải. Đọc trạng thái chat để hiển thị Mockup sản phẩm sinh động và đồng bộ thông số.
* **Tác vụ 11:** Triển khai form điền thông tin ship và nút bấm đẩy đơn sang backend. Tích hợp hiệu ứng pháo hoa ăn mừng và hiển thị mã tracking thực tế của BurgerPrints.

---

## 5. Quy Trình Kiểm Thử & Xác Thực Frontend (QA Checklist)

Để đảm bảo chất lượng giao diện chuẩn Staff Engineer, các kiểm thử sau phải được thực hiện:

| Thành phần | Phương pháp kiểm thử | Kết quả mong đợi |
| :--- | :--- | :--- |
| **Authentication** | Nhập sai email/password; Tạo tài khoản mới | Hiển thị thông báo lỗi rõ ràng; Đăng nhập thành công lưu token và biến mất modal |
| **CORS Connection** | Gửi tin nhắn đầu tiên | API kết nối thành công tới cổng `http://localhost:8000`, không lỗi CORS |
| **State Sync** | Chuyển đổi giữa các cuộc hội thoại cũ | Lịch sử chat được tải lại chính xác đúng ngữ cảnh cũ |
| **Comparison Table** | Tìm kiếm sản phẩm | Bảng so sánh hiển thị trực quan, Option 1 nổi bật rõ nét với tag "RECOMMENDED" |
| **Order HUD & Confetti** | Click đặt đơn | Đẩy đơn thành công, nút bị khóa, pháo hoa bắn lên và hiển thị Order ID kèm trạng thái đơn hàng |
| **Responsive Design** | Thu hẹp cửa sổ trình duyệt | Cột sidebar và right panel tự thu nhỏ hoặc chuyển sang menu trượt mượt mà trên màn hình nhỏ |
