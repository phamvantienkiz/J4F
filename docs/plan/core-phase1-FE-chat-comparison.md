# Kế hoạch triển khai: Center Chat Area & Candidate Table (FE - Giai đoạn 1)

## 1. Liên kết Yêu cầu & Tài liệu tham chiếu
- **User Story liên quan:**
  - [US-001: Tra Cứu & So Sánh Xưởng Qua Chatbot - Candidate Table](file:///E:/MyProject/BurgerAgent/docs/product/burgeragent-core-prd.md#L96-L109)
- **Functional Requirements:**
  - [F-1: Thiết kế LangGraph Stateful Agent Loop - Hỏi ngược và AI CoT](file:///E:/MyProject/BurgerAgent/docs/product/burgeragent-core-prd.md#L182-L195)
  - [F-3: Bảng So Sánh Candidate Table Trong Chat](file:///E:/MyProject/BurgerAgent/docs/product/burgeragent-core-prd.md#L208-L212)
- **Technical Constraints & Architecture:**
  - [Quy đổi Bảng So Sánh (Candidate Table)](file:///E:/MyProject/BurgerAgent/docs/product/burgeragent-core-architecture.md#L362-L384)
  - [Cột 2: Center Panel (Khung Chat & So Sánh)](file:///E:/MyProject/BurgerAgent/docs/product/burgeragent-frontend-design.md#L113-L120)
  - [Bảng So Sánh Candidate Table Tương Thích & Mở Rộng Redesign](file:///E:/MyProject/BurgerAgent/docs/product/burgeragent-frontend-design.md#L167-L180)
- **QA/QC Test Cases:**
  - [TC-001: Nhận diện ý định & Hiển thị Candidate Table](file:///E:/MyProject/BurgerAgent/docs/product/burgeragent-core-qa-qc.md#L72)
  - [TC-002: Xử lý thiếu thông tin đầu vào - Chatbot phản hồi hỏi lại](file:///E:/MyProject/BurgerAgent/docs/product/burgeragent-core-qa-qc.md#L73)

---

## 2. Đặc tả Kỹ thuật
- **Welcome Screen:** Hiển thị màn hình giới thiệu khi phiên chat trống, chứa logo lớn và các Suggestion Chips ở cạnh đáy (nhấp để gửi nhanh câu hỏi gợi ý).
- **Phân biệt Bong bóng Chat (Message Bubbles):**
  - **User Message:** Canh phải, nền Navy nhạt (`hsl(224, 71%, 12%)`), bo tròn 3 góc (trừ góc dưới bên phải).
  - **AI Message:** Canh trái, nền kính siêu mờ trong suốt, có avatar robot nhỏ ở đầu dòng, bo tròn 3 góc (trừ góc dưới bên trái). Có tích hợp hiển thị/ẩn khối suy nghĩ (Thinking Log) của Agent.
- **Candidate Table Layout:**
  - Mặc định trên màn hình Desktop: Hiển thị bảng thu gọn gồm 6 cột thông số chính để không gây chật hẹp, kèm nút phóng to **"Xem Chi Tiết Bảng"**.
  - **Modal Fullscreen:** Khi click phóng to, hiển thị bảng modal rộng rãi đầy đủ 10 cột dữ liệu.
  - **Mobile Card View Carousel:** Trên mobile, tự động chuyển bảng sang dạng các thẻ card nằm ngang cho phép vuốt trượt ngang, hiển thị thông số xếp dọc.
  - **Highlight Đề xuất:** Dòng xưởng in đầu tiên được bo viền cam đậm (`--primary`) hoặc tím phát sáng, có nhãn nổi bật `RECOMMENDED` và nút CTA lớn.

---

## 3. Kế hoạch Triển khai (Mã nguồn & Cấu trúc)
1. **Xây dựng Chat Feed Component:**
   - Tạo React component `ChatFeed` nhận mảng tin nhắn của session.
   - Viết logic tự động cuộn xuống dưới cùng (`scroll-to-bottom`) khi có tin nhắn mới.
2. **Triển khai Message Bubble và Suggestion Chips:**
   - Xây dựng component `MessageBubble` định dạng Markdown cho nội dung văn bản.
   - Thêm nút toggle ẩn/hiển thị khối `thinking_log` của AI.
   - Thiết kế các Suggestion Chips ở Welcome Screen gửi prompt tương ứng khi click.
3. **Phát triển Responsive Candidate Table:**
   - Tạo component `CandidateTable` nhận dữ liệu JSON `comparison_data` từ API `/v1/chat`.
   - Cột hiển thị: *Xưởng in, Base Cost, Print Cost, Shipping, Tax, Landed Cost (in đậm), Margin % (xanh lá), SLA, Rủi ro SLA, Hành động*.
   - Áp dụng class CSS nổi bật cho phần tử đầu tiên (Recommended).
   - Gắn sự kiện `onSelectFactory` vào nút "Chọn Xưởng".
4. **Phát triển Modal Fullscreen & Carousel Mobile:**
   - Thiết lập Modal hiển thị bảng 10 cột khi nhấp nút Zoom.
   - Viết CSS Media Queries: Khi chiều rộng màn hình `< 768px`, ẩn bảng thông thường, hiển thị layout `flex` trượt ngang (`overflow-x: scroll; display: flex; scroll-snap-type: x mandatory`). Mỗi card xưởng in có layout xếp dọc rõ ràng.

---

## 4. Kịch bản Kiểm thử & QA/QC (Không Mock Data)
- **TC-CHATUI-001: Hiển thị đúng bong bóng chat và Thinking Log**
  - **Mục tiêu:** Trình bày tin nhắn đẹp mắt, hỗ trợ ẩn hiện log suy nghĩ của AI.
  - **Cách test:** Seller chat một câu bất kỳ -> Phản hồi của AI hiển thị canh trái. Nhấp nút Toggle "Xem tiến trình suy nghĩ" -> Khối log suy nghĩ phải hiển thị màu xám mờ với phông chữ `JetBrains Mono`.
- **TC-CHATUI-002: Vuốt ngang thẻ so sánh xưởng trên Mobile**
  - **Mục tiêu:** Bảng chuyển đổi thành card carousel trên màn hình nhỏ và vuốt ngang mượt mà.
  - **Cách test:** Bật chế độ Responsive di động của trình duyệt. Bảng so sánh phải biến mất và thay thế bằng các thẻ xưởng độc lập xếp liền nhau. Thử vuốt chuột/chạm ngang -> Các thẻ phải trượt theo cơ chế snap mượt mà.
- **TC-CHATUI-003: Phóng to bảng so sánh (Fullscreen Zoom)**
  - **Mục tiêu:** Cho phép xem đầy đủ 10 cột dữ liệu trên desktop.
  - **Cách test:** Trên màn hình desktop, click nút "Xem Chi Tiết Bảng" ở góc bảng -> Một modal phủ tràn màn hình phải xuất hiện hiển thị đầy đủ 10 cột giá và SLA rộng rãi, dễ đọc.
- **TC-CHATUI-004: Click chọn xưởng**
  - **Mục tiêu:** Nút chọn xưởng kích hoạt đúng callback sự kiện.
  - **Cách test:** Click nút "Chọn Xưởng" ở dòng số 1 -> Đảm bảo luồng frontend bắt được sự kiện và truyền dữ liệu xưởng đã chọn sang Right Panel để kích hoạt cấu hình mockup.
