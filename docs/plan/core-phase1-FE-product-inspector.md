# Kế hoạch triển khai: Product Inspector & Drag-Drop Mockup HUD (FE - Giai đoạn 1)

## 1. Liên kết Yêu cầu & Tài liệu tham chiếu
- **User Story liên quan:**
  - [US-002: Xem Mockup & Tùy Biến Sản Phẩm](file:///E:/MyProject/BurgerAgent/docs/product/burgeragent-core-prd.md#L112-L133)
- **Functional Requirements:**
  - [F-4: Product Inspector & Preview Mockup Lồng Ghép Thiết Kế](file:///E:/MyProject/BurgerAgent/docs/product/burgeragent-core-prd.md#L213-L222)
- **Technical Constraints & Architecture:**
  - [Ghép thiết kế động (Pillow Dynamic Mockup Composite)](file:///E:/MyProject/BurgerAgent/docs/product/burgeragent-core-ai-engine.md#L382-L389)
  - [Cột 3: Right Panel (Product Inspector & Order HUD)](file:///E:/MyProject/BurgerAgent/docs/product/burgeragent-frontend-design.md#L122-L130)
  - [Hiệu Ứng Chuyển Cảnh "Fly to Mockup" Redesign](file:///E:/MyProject/BurgerAgent/docs/product/burgeragent-frontend-design.md#L182-L189)
  - [Khu Vực Kéo Thả Upload Thiết Kế (Drag & Drop Design HUD)](file:///E:/MyProject/BurgerAgent/docs/product/burgeragent-frontend-design.md#L190-L198)
- **QA/QC Test Cases:**
  - [TC-007: Đồng bộ dữ liệu chọn xưởng sang Right Panel](file:///E:/MyProject/BurgerAgent/docs/product/burgeragent-core-qa-qc.md#L86)
  - [TC-008: Lồng ghép thiết kế & Preview Mockup](file:///E:/MyProject/BurgerAgent/docs/product/burgeragent-core-qa-qc.md#L87)

---

## 2. Đặc tả Kỹ thuật
- **Fly to Mockup Effect:** Hiệu ứng di chuyển bay mượt mà của ảnh thumbnail phôi sản phẩm từ vị trí hàng trong bảng so sánh (Cột 2) đáp xuống vị trí Mockup Display (Cột 3) với thời gian bay **350ms** (`cubic-bezier(0.16, 1, 0.3, 1)`).
- **Tránh giật Layout (CLS):** Khung chứa Mockup bắt buộc khai báo kích thước cố định hoặc sử dụng thuộc tính `aspect-ratio` để giao diện không bị giật nhảy khi ảnh load bất đồng bộ.
- **Drag & Drop Zone:** Khung kéo thả nét đứt `.drop-zone` hỗ trợ kéo thả trực tiếp tệp hình ảnh thiết kế (`.png`, `.jpg`, `.svg`). Đọc nội dung tệp bằng JavaScript `FileReader` để đổi sang chuỗi Base64 và vẽ đè lên mockup local.
- **Mockup Preview Layering:**
  - Lớp nền (Base Layer): Ảnh phôi phông nền sản phẩm.
  - Lớp thiết kế (Design Layer): Ảnh in nằm ở vị trí tuyệt đối (`position: absolute`) đè lên lớp nền.
  - Toggles: Nút nhấn chuyển đổi góc nhìn Mặt Trước (Front view) và Mặt Sau (Back view).

---

## 3. Kế hoạch Triển khai (Mã nguồn & Cấu trúc)
1. **Thiết lập Tab Navigation & Mockup Preview Container:**
   - Xây dựng phần Right Panel chia tab. Mặc định mở tab "Fulfillment Checkout".
   - Khai báo css cho Mockup Display: `width: 100%; aspect-ratio: 1 / 1; position: relative; overflow: hidden;`.
   - Viết các nút bấm Toggle xem mặt trước/sau dưới mockup.
2. **Triển khai Drag & Drop Design HUD:**
   - Tạo component `DesignDropZone`. Viết các hàm xử lý sự kiện `onDragOver`, `onDragLeave`, và `onDrop`.
   - Sử dụng `FileReader` đọc file ảnh của user, chuyển đổi thành mã Base64 và gán vào state của React component phôi áo.
   - Thêm tính năng cho phép thả trực tiếp ảnh thiết kế đè lên khu vực hình mockup lớn để kích hoạt tự động gán.
3. **Phát triển Color Swatches & Size Chips:**
   - Tạo component hiển thị các hạt tròn màu sắc (`ColorSwatches`) có viền nổi bật (focus border) khi click chọn.
   - Tạo component hiển thị các chip chọn kích cỡ (`SizeChips`) dạng nút vuông nhỏ.
   - Cập nhật state thuộc tính sản phẩm của seller khi đổi màu/size.
4. **Triển khai Hiệu ứng Fly to Mockup:**
   - Sử dụng thư viện animation (như Framer Motion) hoặc CSS transitions tùy biến:
     - Khi nhận sự kiện click "Chọn Xưởng", lấy tọa độ nguồn (bounding client rect) của nút hoặc thumbnail dòng so sánh.
     - Tạo một bản sao hình ảnh tạm thời (`absolute`) di chuyển từ tọa độ nguồn đến tọa độ đích (Mockup Display).
     - Kết thúc animation trong 350ms, xóa bản sao và hiển thị phôi chính tại Right Panel.

---

## 4. Kịch bản Kiểm thử & QA/QC (Không Mock Data)
- **TC-MOCKUP-001: Hiệu ứng chuyển cảnh Fly to Mockup**
  - **Mục tiêu:** Di chuyển mượt mà phôi áo giữa hai cột khi click chọn.
  - **Cách test:** Click "Chọn Xưởng" ở cột 2 -> Quan sát hình ảnh bay xuyên màn hình sang cột 3 trong khoảng 350ms, Right Panel tự động hiện ra mà không bị giật lag hay biến mất đột ngột.
- **TC-MOCKUP-002: Drag & Drop và hiển thị Base64**
  - **Mục tiêu:** Kéo thả tệp ảnh in lên áo hiển thị tức thì.
  - **Cách test:** Kéo thả một file ảnh `.png` từ thư mục máy tính thả vào khung Drop Zone của mặt trước -> Ảnh in phải tự động thu phóng và xuất hiện trên ngực phôi áo Mockup.
- **TC-MOCKUP-003: Toggle đổi góc nhìn trước/sau**
  - **Mục tiêu:** Đổi mặt xem trước và giữ thiết kế tương ứng.
  - **Cách test:** Đã tải lên ảnh thiết kế mặt trước và mặt sau. Click nút "Back view" -> Mockup phải đổi sang hiển thị mặt sau áo kèm ảnh in mặt sau. Click "Front view" -> Quay lại mặt trước kèm thiết kế mặt trước.
