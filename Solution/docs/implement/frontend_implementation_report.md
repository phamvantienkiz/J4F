# BÁO CÁO TRIỂN KHAI PHÂN HỆ FRONTEND: BURGER AGENT

Báo cáo này tóm tắt chi tiết các thành phần, kiến trúc và kết quả triển khai thực tế của phân hệ **Frontend (React, TypeScript & Vite)** cho dự án **Burger Agent** (Trợ lý Danh mục sản phẩm POD và Tối ưu hóa Fulfillment).

---

## 1. Tổng Quan Kỹ Thuật (Technical Overview)

Toàn bộ mã nguồn giao diện được tổ chức gọn gàng trong thư mục [Product/frontend/](file:///E:/Hackathon2026/J4F/Product/frontend) đảm bảo tính độc lập và dễ tích hợp.

- **Tech Stack chính:** React 19, TypeScript 6, Vite 8, Axios (HTTP Client), Lucide React (Icons), Canvas Confetti (Hiệu ứng thành công).
- **Styling:** Vanilla CSS và CSS Modules để kiểm soát chi tiết giao diện Glassmorphism, không dùng Tailwind CSS để tối ưu hóa hiệu suất load trang.
- **Quy tắc thiết kế:** Tuân thủ hệ màu HSL tối giản (Sleek Dark Mode): nền Deep Midnight Navy (`#020617`), các thẻ Glassmorphic Navy (`#0b1129`), nhấn mạnh (Brand Accents) bằng Electric Blue (`#2563EB`) và Neon Violet (`#7C3AED`) để biểu thị AI.
- **Bố cục giao diện:** Cấu trúc 3 cột thích ứng (Responsive Layout): Left Sidebar (20%) - Center Panel (50%) - Right Panel (30%).

---

## 2. Chi Tiết Các Thành Phần Đã Triển Khai (Components Implemented)

### 2.1. Quản lý Môi trường & Dependency
- Cấu hình [package.json](file:///E:/Hackathon2026/J4F/Product/frontend/package.json) định nghĩa đầy đủ scripts `dev`, `build`, `preview` và các gói dependencies chính xác không xung đột.

### 2.2. Style Tokens & Cấu Trúc CSS
- [index.css](file:///E:/Hackathon2026/J4F/Product/frontend/src/index.css): Khai báo toàn bộ CSS Variables hệ màu, phông chữ `Outfit` (Heading) & `Inter` (Body Text), hiệu ứng shimmer chờ tin nhắn, glow border khi chọn input và pulse ring cho các biểu tượng AI hoạt động.
- [App.css](file:///E:/Hackathon2026/J4F/Product/frontend/src/App.css): Định nghĩa khung lưới hiển thị 3 cột và responsive cho các màn hình kích thước nhỏ (Tablet, Mobile).

### 2.3. Axios API Client & Authentication Context
- [api.ts](file:///E:/Hackathon2026/J4F/Product/frontend/src/services/api.ts): Cổng kết nối trung gian đóng gói toàn bộ endpoints của FastAPI Backend. Thiết lập Interceptors tự động đính kèm Token xác thực JWT dưới dạng `Authorization: Bearer <token>` vào request header.
- [AuthContext.tsx](file:///E:/Hackathon2026/J4F/Product/frontend/src/context/AuthContext.tsx): Quản lý vòng đời đăng nhập, đăng ký, đồng bộ dữ liệu Store Name, email của Seller và lưu trữ an toàn token trong `localStorage`.

### 2.4. Các Components Giao Diện Cốt Lõi
- [AuthModal.tsx](file:///E:/Hackathon2026/J4F/Product/frontend/src/components/AuthModal.tsx) & [AuthModal.css](file:///E:/Hackathon2026/J4F/Product/frontend/src/components/AuthModal.css): Form Đăng ký (yêu cầu thêm tên Store POD) và Đăng nhập. Tích hợp hiệu ứng làm mờ màn hình (blur backdrop overlay) tạo chiều sâu cao cấp.
- [Sidebar.tsx](file:///E:/Hackathon2026/J4F/Product/frontend/src/components/Sidebar.tsx) & [Sidebar.css](file:///E:/Hackathon2026/J4F/Product/frontend/src/components/Sidebar.css): Cột 1 (Left Sidebar) quản lý danh sách cuộc hội thoại cũ được nhóm thông minh theo thời gian (Hôm nay, Hôm qua, Tuần trước, Cũ hơn). Tích hợp hiển thị profile store, nút New Chat và nút mở Modal Cài đặt.
- [PreferencesModal.tsx](file:///E:/Hackathon2026/J4F/Product/frontend/src/components/PreferencesModal.tsx) & [PreferencesModal.css](file:///E:/Hackathon2026/J4F/Product/frontend/src/components/PreferencesModal.css): Giao diện cấu hình mặc định cho Seller (Target Margin %, Max Shipping Days, Tiêu chí ưu tiên Margin/Speed, Thị trường).
- [ChatArea.tsx](file:///E:/Hackathon2026/J4F/Product/frontend/src/components/ChatArea.tsx) & [ChatArea.css](file:///E:/Hackathon2026/J4F/Product/frontend/src/components/ChatArea.css): Cột 2 (Center Panel) quản lý khung chat cuộn tự động. Tích hợp parser Markdown (inline code, bold, lists, header) và hiển thị **Bảng so sánh tối ưu hóa xưởng in** có highlight Neon Violet phát sáng cho lựa chọn số 1 (Recommended).
- [RightPanel.tsx](file:///E:/Hackathon2026/J4F/Product/frontend/src/components/RightPanel.tsx) & [RightPanel.css](file:///E:/Hackathon2026/J4F/Product/frontend/src/components/RightPanel.css): Cột 3 (Right Panel) chứa:
  - *Product Inspector:* Bản mô phỏng Mockup vector chất lượng cao (T-Shirt, Hoodie, Ceramic Mug) thay đổi màu sắc và chi tiết trực quan thời gian thực.
  - *Order HUD:* Form điền thông tin người nhận, tính chi phí landed cost breakdown (Base, Print, Ship, Tax) và nút gửi đơn hàng. Kích hoạt hiệu ứng bắn pháo hoa khi nhận kết quả thành công từ API.

---

## 3. Báo Cáo Kiểm Thử & Biên Dịch (Build & Verification Report)

Hệ thống đã trải qua quá trình tối ưu hóa nghiêm ngặt và đạt tỷ lệ biên dịch thành công tuyệt đối.

- **Kiểm tra TypeScript:** Khắc phục triệt để các lỗi import type phục vụ quy tắc `verbatimModuleSyntax` trong compiler.
- **Biên dịch Production:** Chạy lệnh `npm run build` thành công, tạo ra các bundle nén tối ưu:
  - `dist/index.html` (0.45 kB)
  - `dist/assets/index-BWuh4exj.css` (26.46 kB)
  - `dist/assets/index-BzUe-4fY.js` (283.49 kB)

---

## 4. Hướng Dẫn Vận Hành Đồng Thời (Dual Server Execution Guide)

Để khởi chạy toàn diện sản phẩm Burger Agent trên máy giám khảo dưới 10 phút, thực hiện theo 2 bước song song:

### Bước 1: Khởi động FastAPI Backend (Port 8000)
```bash
cd Product
uv run python backend/app/db/init_db.py
uv run uvicorn backend.main:app --host 0.0.0.0 --port 8000 --reload
```

### Bước 2: Khởi động Vite Frontend (Port 5173)
```bash
cd Product/frontend
npm install
npm run dev
```

*Truy cập [http://localhost:5173](http://localhost:5173) bằng trình duyệt để trải nghiệm toàn bộ ứng dụng Burger Agent.*
