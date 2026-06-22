# Kế hoạch triển khai: LangGraph Stateful Agent Loop (AI - Giai đoạn 1)

## 1. Liên kết Yêu cầu & Tài liệu tham chiếu
- **User Story liên quan:**
  - [US-001: Tra Cứu & So Sánh Xưởng Qua Chatbot - Ý định & Hỏi ngược](file:///E:/MyProject/BurgerAgent/docs/product/burgeragent-core-prd.md#L96-L104)
- **Functional Requirements:**
  - [F-1: Hệ thống AI Chatbot và Thiết kế LangGraph Stateful Agent Loop](file:///E:/MyProject/BurgerAgent/docs/product/burgeragent-core-prd.md#L182-L195)
- **Technical Constraints & Architecture:**
  - [Turn Control & Khôi phục trạng thái](file:///E:/MyProject/BurgerAgent/docs/product/burgeragent-core-prd.md#L184)
  - [Harness Component 1: While Loop & Component 6: Session Persist](file:///E:/MyProject/BurgerAgent/docs/product/burgeragent-core-ai-engine.md#L69-L75)
  - [Component 7: Prompt Assembly Pipeline & Component 9: Permission Layer](file:///E:/MyProject/BurgerAgent/docs/product/burgeragent-core-ai-engine.md#L134-L159)
  - [LangChainAgentLoop & LangGraph Stateful Agent Loop](file:///E:/MyProject/BurgerAgent/docs/product/burgeragent-core-architecture.md#L125-L128)
- **QA/QC Test Cases:**
  - [TC-001: Nhận diện ý định & Hiển thị Candidate Table](file:///E:/MyProject/BurgerAgent/docs/product/burgeragent-core-qa-qc.md#L72)
  - [TC-002: Xử lý thiếu thông tin đầu vào](file:///E:/MyProject/BurgerAgent/docs/product/burgeragent-core-qa-qc.md#L73)
  - [TC-019: Khôi phục trạng thái khi Server bị gián đoạn](file:///E:/MyProject/BurgerAgent/docs/product/burgeragent-core-qa-qc.md#L112)

---

## 2. Đặc tả Kỹ thuật
- **AI Framework:** LangGraph kết hợp LangChain.
- **Mô hình suy nghĩ:** Chain-of-Thought (CoT) cho phép LLM tự lập kế hoạch trước khi hành động.
- **Quản lý trạng thái (State):** Đồ thị LangGraph sử dụng `AgentState` TypedDict lưu trữ: `messages`, `current_product`, `current_factory`, `checkout_info`, `user_preferences`, `todos`.
- **Durable Execution:** Lưu trữ các điểm checkpoints thông qua SQLite Checkpointer.
- **Giới hạn số lượt suy nghĩ (Turn Limit):** Khai báo `max_turns = 10` để tránh LLM bị lặp vô hạn.

---

## 3. Kế hoạch Triển khai (Mã nguồn & Cấu trúc)
1. **Thiết lập Cấu hình State & Checkpointer:**
   - Tạo file [ai/app/agent/state.py](file:///E:/MyProject/BurgerAgent/docs/product/burgeragent-backend-ai-structure.md#L109) khai báo lớp `AgentState`.
   - Cấu hình SQLite Checkpointer để lưu trạng thái đồ thị bền vững.
2. **Xây dựng Đồ thị LangGraph (StateGraph):**
   - Triển khai trong [ai/app/agent/graph.py](file:///E:/MyProject/BurgerAgent/docs/product/burgeragent-backend-ai-structure.md#L108).
   - Định nghĩa Node `agent`: Gọi Gemini API sử dụng Prompt Assembly Pipeline, trả về tin nhắn AI.
   - Định nghĩa Node `action`: Thực thi các tool được LLM yêu cầu (Tool Binding).
   - Thiết lập Conditional Edge `should_continue`:
     - Nếu LLM gọi tool -> Định tuyến đến node `action`.
     - Nếu LLM không gọi tool hoặc số lượt suy nghĩ (`turn_count`) vượt quá 10 -> Định tuyến đến kết thúc (END).
3. **Triển khai Prompt Assembly Pipeline:**
   - Tạo file [ai/app/agent/prompts.py](file:///E:/MyProject/BurgerAgent/docs/product/burgeragent-backend-ai-structure.md#L110).
   - Viết hàm build system prompt động kết hợp các khối:
     - **Role Block:** Mô tả nhiệm vụ trợ lý BurgerPrints.
     - **Preferences Block:** Nạp các giá trị mặc định của seller lấy từ SQLite DB.
     - **Skills Block:** Hướng dẫn luồng so sánh xưởng hoặc checkout.
     - **Permission Block:** Khai báo quyền hiện tại (`Read-Only` hoặc `Interactive Approval`).
     - **Safety Block:** Nghiêm cấm tự tính toán số và làm lộ khóa API.
4. **Binding Công cụ Hệ thống (Tools):**
   - Đăng ký công cụ `search_catalog_db` (tìm kiếm FTS5), `get_catalog_detail` (lấy JSON cache), `calculate_landed_cost` (gọi Python calculation engine), `create_sandbox_order` và `get_order_status`.
   - Ràng buộc: LLM chỉ được phép lấy dữ liệu thô và gọi tool tính toán, cấm tự nhẩm.

---

## 4. Kịch bản Kiểm thử & QA/QC (Không Mock Data)
- **TC-GRAPH-001: Nhận diện ý định & Chuyển đổi Node**
  - **Mục tiêu:** Kiểm tra LangGraph chạy đúng node và gọi đúng tool khi hỏi so sánh.
  - **Cách test:** Gửi request chat `"Tìm Hoodie đi US rẻ nhất"`. Kiểm tra trường `thinking_log` trong response -> Phải thể hiện AI trích xuất thực thể, gọi tool `search_catalog_db`, sau đó gọi tool `calculate_landed_cost` và trả về kết quả bảng.
- **TC-GRAPH-002: Chặn lặp vô hạn (Turn Limit Handoff)**
  - **Mục tiêu:** Không bị treo máy khi LLM rơi vào vòng lặp gọi tool lỗi.
  - **Cách test:** Giả lập tool `calculate_landed_cost` luôn ném ra ngoại lệ và bắt AI phải thử lại. Chạy luồng -> Đảm bảo khi lượt gọi vượt quá 10, đồ thị phải tự động ngắt và kích hoạt tool `handoff_to_human`, trả về tin nhắn xin lỗi người bán.
- **TC-GRAPH-003: Phục hồi State sau sự cố (Resilience)**
  - **Mục tiêu:** Tiếp tục hội thoại từ điểm checkpoint trước khi crash.
  - **Cách test:**
    1. Seller chốt chọn xưởng A. Tiến trình lưu checkpoint thành công.
    2. Tắt nóng AI Service. Khởi động lại.
    3. Gửi tin nhắn: `"Chốt đơn hàng này đi"`. AI Service phải tự load lại state từ SQLite Checkpointer, nhận diện được xưởng A đã chọn trước đó và chuyển sang luồng thu thập địa chỉ.
