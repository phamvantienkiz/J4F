# Kế hoạch triển khai: Glassmorphic App Shell & 3-Column Layout Grid (FE - Giai đoạn 1)

## 1. Liên kết Yêu cầu & Tài liệu tham chiếu
- **User Story liên quan:**
  - [US-001: Tra Cứu & So Sánh Xưởng Qua Chatbot - Web Dashboard](file:///E:/MyProject/BurgerAgent/docs/product/burgeragent-core-prd.md#L39-L40)
- **Functional Requirements:**
  - [F-6: Giao diện Chatbot Telegram & Quy trình Đặt hàng - Đồng bộ Web sang Telegram](file:///E:/MyProject/BurgerAgent/docs/product/burgeragent-core-prd.md#L232-L235)
- **Technical Constraints & Architecture:**
  - [Kiến trúc đa kênh (Omni-channel)](file:///E:/MyProject/BurgerAgent/docs/product/burgeragent-core-architecture.md#L15-L16)
  - [Triết Lý Thiết Kế & Định Vị Thương Hiệu - Glassmorphism](file:///E:/MyProject/BurgerAgent/docs/product/burgeragent-frontend-design.md#L7-L14)
  - [Hệ Thống Design Tokens (Style Guide)](file:///E:/MyProject/BurgerAgent/docs/product/burgeragent-frontend-design.md#L17-L50)
  - [Kiến Trúc Bố Cục Giao Diện (Layout Grid Architecture)](file:///E:/MyProject/BurgerAgent/docs/product/burgeragent-frontend-design.md#L53-L99)
- **QA/QC Test Cases:**
  - [TC-018: Hiệu năng phản hồi cục bộ & Giao diện di động](file:///E:/MyProject/BurgerAgent/docs/product/burgeragent-core-qa-qc.md#L110-L112)
  - [Mức độ nghiêm trọng S3: Lỗi vỡ khung hiển thị](file:///E:/MyProject/BurgerAgent/docs/product/burgeragent-core-qa-qc.md#L130-L132)

---

## 2. Đặc tả Kỹ thuật
- **Ngôn ngữ phong cách:** CSS Vanilla kết hợp cấu trúc Design Tokens (không dùng TailwindCSS).
- **Glassmorphism Spec:**
  ```css
  background: hsla(224, 71%, 8%, 0.65);
  backdrop-filter: blur(12px) saturate(180%);
  border: 1px solid rgba(255, 255, 255, 0.08);
  ```
- **Hệ phông chữ:**
  - Tiêu đề & Nhãn: `Outfit`
  - Văn bản & Chat: `Inter`
  - Số liệu & Mã SKU: `JetBrains Mono`
- **Bố cục màn hình rộng (Desktop >= 1200px):**
  - Chiều cao cố định `100vh`, ẩn scrollbar toàn màn hình (`overflow: hidden`).
  - Chia 3 cột tỷ lệ **20% : 50% : 30%**. Mỗi cột tự cuộn dữ liệu độc lập.
- **Thích ứng màn hình di động (< 768px):**
  - Hiển thị 1 cột duy nhất (Center Chat).
  - Cột 1 (Sidebar) ẩn dưới Hamburger Menu, mở dạng Drawer trượt trái.
  - Cột 3 (Right Panel) chuyển thành **Bottom Sheet** trượt lên từ đáy màn hình chiếm 85% chiều cao.

---

## 3. Kế hoạch Triển khai (Mã nguồn & Cấu trúc)
1. **Thiết lập Design Tokens toàn cục:**
   - Tạo file `frontend/styles/index.css` chứa các biến CSS Custom Properties cho mã màu HSL (Primary, Secondary, Glow, backgrounds, texts), bán kính bo góc, và hiệu ứng bóng đổ kính mờ.
   - Nhúng Google Fonts (Outfit, Inter, JetBrains Mono) trong root layout.
2. **Xây dựng Cột 1: Left Sidebar:**
   - Thiết kế header chứa Logo, nút chuyển đổi Sáng/Tối.
   - Nút "+ New Chat" bo góc cam gradient phát sáng khi hover.
   - Danh sách phiên chat phân nhóm thời gian (Hôm nay, Hôm qua...), hỗ trợ nút click xóa nhanh phiên.
   - Footer chứa thông tin Profile user, nút mở Modal Preferences và Đăng xuất.
3. **Thiết lập Grid Shell 3 cột:**
   - Xây dựng Layout Grid bằng CSS Flexbox/Grid chia không gian 20%/50%/30% cố định chiều cao.
   - Cài đặt `overflow-y: auto` riêng cho từng khu vực để tin nhắn chat và checkout form cuộn mượt độc lập.
4. **Viết Media Queries Thích ứng:**
   - Cấu hình `@media (max-width: 1199px)` thu Sidebar vào Drawer trượt.
   - Cấu hình `@media (max-width: 767px)` thu gọn giao diện thành 1 cột. Viết CSS transition trượt mở Bottom Sheet từ dưới lên sử dụng cubic-bezier.

---

## 4. Kịch bản Kiểm thử & QA/QC (Không Mock Data)
- **TC-LAYOUT-001: Kiểm tra độ tương phản màu và WCAG 2.1 AA**
  - **Mục tiêu:** Đảm bảo chữ dễ đọc trên nền tối, độ tương phản tối thiểu 4.5:1.
  - **Cách test:** Dùng trình duyệt Chrome DevTools Lighthouse chạy phân tích Accessibility -> Điểm đánh giá độ tương phản màu của các khối text và menu phải đạt mức AA trở lên.
- **TC-LAYOUT-002: Thích ứng trên Thiết bị di động (Responsive Layout)**
  - **Mục tiêu:** Bố cục không bị vỡ trên điện thoại và sidebar Drawer/Bottom Sheet hoạt động chuẩn.
  - **Cách test:**
    1. Giả lập màn hình iPhone 12/13 trong DevTools (chiều rộng 390px). Giao diện phải chuyển về 1 cột khung chat.
    2. Click icon hamburger -> Drawer Sidebar trượt mượt mà từ bên trái ra.
    3. Click chọn một xưởng -> Bottom Sheet chứa Order HUD phải tự động trượt lên từ cạnh đáy, phủ lên khung chat, hiển thị đầy đủ thông tin thanh toán.
- **TC-LAYOUT-003: Cuộn độc lập (Scroll Isolation)**
  - **Mục tiêu:** Cuộn tin nhắn chat hoặc form order không làm dịch chuyển toàn trang.
  - **Cách test:** Cuộn chuột ở cột chat khi có nhiều tin nhắn -> Chỉ danh sách chat cuộn, Sidebar và Right Panel phải giữ nguyên vị trí, không xuất hiện thanh cuộn kép ở rìa màn hình.
