# Kế hoạch triển khai: Memory & Context Management (AI - Giai đoạn 1)

## 1. Liên kết Yêu cầu & Tài liệu tham chiếu
- **User Story liên quan:**
  - [US-001: Tra Cứu & So Sánh Xưởng Qua Chatbot - Hội thoại nhiều lượt](file:///E:/MyProject/BurgerAgent/docs/product/burgeragent-core-prd.md#L91-L92)
- **Functional Requirements:**
  - [F-1: Thiết kế LangGraph Stateful Agent Loop - Memory](file:///E:/MyProject/BurgerAgent/docs/product/burgeragent-core-prd.md#L182-L195)
  - [Kiến Trúc Bộ Nhớ & Quản Lý Phiên (Memory & Session Architecture)](file:///E:/MyProject/BurgerAgent/docs/product/burgeragent-core-prd.md#L248-L261)
- **Technical Constraints & Architecture:**
  - [Memory & Session Manager component](file:///E:/MyProject/BurgerAgent/docs/product/burgeragent-core-architecture.md#L90-L95)
  - [Harness Component 2: Context Management](file:///E:/MyProject/BurgerAgent/docs/product/burgeragent-core-ai-engine.md#L76-L89)
- **QA/QC Test Cases:**
  - [TC-003: Duy trì ngữ cảnh & Tóm tắt hội thoại (Memory)](file:///E:/MyProject/BurgerAgent/docs/product/burgeragent-core-qa-qc.md#L74)

---

## 2. Đặc tả Kỹ thuật
- **Kiến trúc bộ nhớ phân lớp (3-Tier Context):**
  - **Bộ nhớ ngắn hạn (Short-term Memory):** Lưu lịch sử tin nhắn trong SQLite theo `Session ID`. Áp dụng phương pháp **Sliding Window Buffer** chỉ gửi 8-10 lượt hội thoại gần nhất (`messages[-8:]`) kèm theo system prompt cho LLM.
  - **Cơ chế Tóm tắt (Summarizer Worker):** Khi số lượng token hội thoại vượt quá **3,000 tokens**, kích hoạt background task gọi LLM tóm tắt ngữ cảnh.
  - **Quy tắc trích xuất tóm tắt (Keep vs Drop):**
    - **Giữ lại:** Tên sản phẩm đã chốt, xưởng in đã chọn, thị trường mục tiêu, màu sắc, kích thước, link thiết kế đã chốt.
    - **Loại bỏ:** Các bảng so sánh nháp, các con số tính toán tạm thời, dữ liệu JSON thô nhận từ API.
  - **Bộ nhớ dài hạn (Long-term Memory):** Lưu cấu hình ưu tiên (Preferences) của Seller, tự động nạp ở turn đầu tiên làm ngữ cảnh nền.

---

## 3. Kế hoạch Triển khai (Mã nguồn & Cấu trúc)
1. **Thiết lập Module Sliding Window:**
   - Tạo file [ai/app/memory/sliding_window.py](file:///E:/MyProject/BurgerAgent/docs/product/burgeragent-backend-ai-structure.md#L117) định nghĩa lớp `MemorySessionManager`.
   - Triển khai hàm `get_short_term_context(session_id: str)`: Đọc lịch sử tin nhắn từ DB SQLite, cắt lát lấy 8 lượt tin nhắn gần nhất.
   - Triển khai hàm `add_message(session_id: str, sender: str, content: str)`: Lưu trực tiếp tin nhắn mới của User hoặc AI vào bảng `chat_history`.
2. **Triển khai Summarizer Worker:**
   - Tạo file [ai/app/memory/summarizer.py](file:///E:/MyProject/BurgerAgent/docs/product/burgeragent-backend-ai-structure.md#L118).
   - Viết hàm `trigger_summarizer(session_id: str)`: Kiểm tra độ dài token của chat history. Nếu > 3000 tokens, chạy ngầm một LLM task gọi prompt tóm tắt.
   - Viết system prompt cho Summarizer: *"Hãy tóm tắt ngắn gọn cuộc hội thoại, chỉ giữ lại các thông tin sản phẩm và xưởng in đã chốt cuối cùng, bỏ qua các phương án so sánh nháp và bảng dữ liệu số thô..."*.
   - Cập nhật chuỗi tóm tắt này vào bảng `sessions` (trường `session_summary`).
3. **Tích hợp Prompt Assembly Pipeline:**
   - Khi build prompt cho turn tiếp theo, nạp `session_summary` vào vị trí `[Context Block]` của system prompt để làm nền ngữ cảnh dài hạn cho Agent.

---

## 4. Kịch bản Kiểm thử & QA/QC (Không Mock Data)
- **TC-MEM-001: Sliding Window Context**
  - **Mục tiêu:** Kiểm tra AI hiểu được câu hỏi tiếp nối ngữ cảnh trong phạm vi 8 tin nhắn.
  - **Cách test:**
    1. Nhập: `"Tôi muốn tìm áo Comfort Colors 1717."` -> AI trả lời bảng các xưởng.
    2. Nhập tiếp: `"Chọn xưởng Factory A ở Việt Nam nhé."` -> AI phải hiểu `"nhé"` là đang chọn xưởng cho Comfort Colors 1717 ở câu trên.
    3. Nhập tiếp: `"Đổi size áo này sang L."` -> AI phải đổi size của Comfort Colors 1717 sang L.
- **TC-MEM-002: Kích hoạt Summarizer khi vượt giới hạn**
  - **Mục tiêu:** Tự động tóm tắt và thu gọn lịch sử khi tokens vượt quá 3000.
  - **Cách test:** Giả lập chat liên tục hoặc dán đoạn text lớn (> 3000 tokens) vào khung chat. Kiểm tra DB SQLite tại bảng `sessions` -> Cột `session_summary` phải được cập nhật chứa chuỗi tóm tắt ngắn gọn. Đồng thời lịch sử truyền lên LLM chỉ chứa Summary + 8 tin nhắn gần nhất, giúp tiết kiệm token và tăng tốc độ xử lý.
