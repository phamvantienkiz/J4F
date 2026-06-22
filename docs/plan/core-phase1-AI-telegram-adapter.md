# Kế hoạch triển khai: Telegram Bot UI/UX Adapter & Pillow Renderer (AI - Giai đoạn 1)

## 1. Liên kết Yêu cầu & Tài liệu tham chiếu
- **User Story liên quan:**
  - [US-001: Tra Cứu & So Sánh Xưởng Qua Chatbot - Telegram Chatbot Bot](file:///E:/MyProject/BurgerAgent/docs/product/burgeragent-core-prd.md#L40-L41)
  - [US-002: Xem Mockup & Tùy Biến Sản Phẩm - Lồng ghép thiết kế](file:///E:/MyProject/BurgerAgent/docs/product/burgeragent-core-prd.md#L124-L127)
- **Functional Requirements:**
  - [F-6: Giao diện Chatbot Telegram & Quy trình Đặt hàng Hội thoại](file:///E:/MyProject/BurgerAgent/docs/product/burgeragent-core-prd.md#L232-L241)
- **Technical Constraints & Architecture:**
  - [Quy Đổi Giao Diện Telegram (Telegram Bot UI/UX Adapter)](file:///E:/MyProject/BurgerAgent/docs/product/burgeragent-core-architecture.md#L358-L398)
  - [Telegram Bot UI/UX Adapter & Pillow component](file:///E:/MyProject/BurgerAgent/docs/product/burgeragent-core-architecture.md#L124-L126)
  - [Render hình ảnh Mockup xem trước API (/v1/mockups/preview)](file:///E:/MyProject/BurgerAgent/docs/product/burgeragent-core-api.md#L147-L175)
- **QA/QC Test Cases:**
  - [TC-013: Quy đổi Candidate Table sang Telegram](file:///E:/MyProject/BurgerAgent/docs/product/burgeragent-core-qa-qc.md#L99)
  - [TC-014: Dynamic Mockup Render trên Telegram](file:///E:/MyProject/BurgerAgent/docs/product/burgeragent-core-qa-qc.md#L100)
  - [TC-015: Đặt đơn qua hội thoại Telegram (Conversational Checkout)](file:///E:/MyProject/BurgerAgent/docs/product/burgeragent-core-qa-qc.md#L101)

---

## 2. Đặc tả Kỹ thuật
- **Định dạng hiển thị:** Quy đổi bảng Candidate Table 10 cột dạng HTML thành văn bản Markdown phân cấp, hiển thị rõ ràng trên màn hình điện thoại di động.
- **Pillow Mockup Composite:**
  - **Tọa độ in mặc định:**
    - **Áo thun/Hoodie:** Vùng in ngực trước có tâm tại `(width * 0.5, height * 0.35)`, kích thước chiều ngang thiết kế chiếm tối đa `30%` chiều ngang phôi áo.
    - **Cốc sứ (Mugs):** Vùng in nằm ở trung tâm `(width * 0.5, height * 0.5)`, tỷ lệ bao phủ thiết kế `45%`.
  - Phối hợp xử lý kênh Alpha (độ trong suốt) của file thiết kế PNG/JPG để dán đè chính xác lên phôi áo.
- **Conversational Checkout:** Xây dựng State Machine nhỏ lưu trữ các bước hội thoại hỏi đáp thông tin giao hàng: Họ tên -> Địa chỉ -> Zip Code -> Xác nhận.

---

## 3. Kế hoạch Triển khai (Mã nguồn & Cấu trúc)
1. **Phát triển Module Định dạng Tin nhắn:**
   - Tạo file [ai/app/telegram_adapter/bot_formatter.py](file:///E:/MyProject/BurgerAgent/docs/product/burgeragent-backend-ai-structure.md#L125).
   - Triển khai hàm `format_candidate_table_to_markdown(options: list) -> str`: Lấy danh sách xưởng so sánh, duyệt và build thành chuỗi text Markdown chứa thông tin chi tiết của từng Factory (Landed Cost, Margin, Vận chuyển, SLA Risk), gắn các biểu tượng cảm xúc (emoji) để tăng tính sinh động.
   - Trả về danh sách Inline Keyboards gắn kèm dưới tin nhắn (ví dụ: `[Chọn Factory A - Landed Cost $11.5]`).
2. **Xây dựng Pillow Mockup Composite:**
   - Tạo file [ai/app/telegram_adapter/mockup_renderer.py](file:///E:/MyProject/BurgerAgent/docs/product/burgeragent-backend-ai-structure.md#L126).
   - Triển khai hàm `composite_design_on_base(base_img_path: str, design_img_path: str, product_type: str) -> Image`:
     - Load ảnh phôi áo nền bằng Pillow.
     - Tải ảnh thiết kế từ URL hoặc đọc từ base64.
     - Tính toán tỷ lệ và resize ảnh thiết kế.
     - Sử dụng hàm `paste()` của Pillow với mặt nạ alpha (mask) để ghép ảnh thiết kế đè lên phôi theo đúng tọa độ in mặc định.
     - Lưu ảnh đầu ra ra thư mục static của server Backend.
3. **Phát triển API Rendering Endpoints:**
   - Tạo file [ai/app/api/v1/endpoints/rendering.py](file:///E:/MyProject/BurgerAgent/docs/product/burgeragent-backend-ai-structure.md#L100).
   - Endpoint `POST /v1/mockups/preview`: Tiếp nhận `product_id`, `color`, `design_front_url`, và `design_back_url` để gọi Pillow Renderer ghép ảnh và trả về link URL ảnh kết quả tĩnh.
4. **Triển khai Quy trình Đặt hàng Hội thoại (Conversational Checkout):**
   - Viết các câu lệnh điều khiển State trong LangGraph: Hỏi từng bước thông tin người nhận, chờ người bán chat, kiểm tra validate dữ liệu, lưu vào `AgentState.checkout_info`, sau khi hoàn tất hiển thị tóm tắt hóa đơn và nút inline xác nhận đặt đơn hàng.

---

## 4. Kịch bản Kiểm thử & QA/QC (Không Mock Data)
- **TC-TG-001: Quy đổi bảng so sánh sang Markdown**
  - **Mục tiêu:** Bảng Candidate Table được định dạng gọn gàng, trực quan.
  - **Cách test:** Truyền danh sách 3 xưởng so sánh vào hàm định dạng. Chuỗi Markdown trả ra phải chứa tên xưởng, landed cost, SLA và risk, không có mã HTML dư thừa.
- **TC-TG-002: Pillow Render ghép ảnh phôi và thiết kế**
  - **Mục tiêu:** Tạo ảnh xem trước thành công mà không bị mất độ trong suốt hoặc sai vị trí.
  - **Cách test:** Gọi API `POST /v1/mockups/preview` với phôi áo Navy và link ảnh in ngực trước. Kiểm tra ảnh lưu tại thư mục static -> Ảnh in phải nằm ở đúng vùng ngực áo phôi, được căn giữa, viền ảnh thiết kế hòa trộn tự nhiên với màu áo phôi Navy, không bị vỡ ảnh.
- **TC-TG-003: Conversational Checkout State Machine**
  - **Mục tiêu:** Hỏi đáp tuần tự và lưu đầy đủ thông tin giao hàng.
  - **Cách test:** Trải nghiệm chat trên Telegram qua các lượt:
    1. Nhấn nút "Đặt hàng". Bot phải hỏi: `"Xin vui lòng nhập Tên người nhận:"`.
    2. Nhập `"John Doe"`. Bot lưu tên và hỏi tiếp: `"Nhập Địa chỉ nhận hàng (Dòng 1):"`.
    3. Nhập `"123 Street"`. Bot lưu địa chỉ và hỏi tiếp: `"Nhập Zip Code:"`.
    4. Nhập `"10001"`. Bot lưu Zip Code và hiển thị tóm tắt hóa đơn kèm nút inline `"Xác Nhận Đơn Hàng"`.
