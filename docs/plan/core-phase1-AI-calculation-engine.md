# Kế hoạch triển khai: Python Calculation Engine (AI - Giai đoạn 1)

## 1. Liên kết Yêu cầu & Tài liệu tham chiếu
- **User Story liên quan:**
  - [US-001: Tra Cứu & So Sánh Xưởng Qua Chatbot - So sánh xưởng](file:///E:/MyProject/BurgerAgent/docs/product/burgeragent-core-prd.md#L96-L100)
  - [US-002: Xem Mockup & Tùy Biến Sản Phẩm - Tính giá in mặt thứ hai](file:///E:/MyProject/BurgerAgent/docs/product/burgeragent-core-prd.md#L128-L132)
- **Functional Requirements:**
  - [F-2: Công Cụ Tính Toán Độc Lập (Python Calculation Engine)](file:///E:/MyProject/BurgerAgent/docs/product/burgeragent-core-prd.md#L196-L207)
- **Technical Constraints & Architecture:**
  - [LLM Ảo Giác Số Liệu Risk Assessment](file:///E:/MyProject/BurgerAgent/docs/product/burgeragent-core-prd.md#L321-L322)
  - [PythonCalculationEngine class](file:///E:/MyProject/BurgerAgent/docs/product/burgeragent-core-architecture.md#L84-L88)
  - [Đặc tả Công Thức Tính Toán Tài Chính (Python Engine)](file:///E:/MyProject/BurgerAgent/docs/product/burgeragent-core-ai-engine.md#L265-L322)
- **QA/QC Test Cases:**
  - [TC-004: Tính toán Landed Cost chính xác](file:///E:/MyProject/BurgerAgent/docs/product/burgeragent-core-qa-qc.md#L75)
  - [TC-004b: Tính toán Biên lợi nhuận (Margin %) theo thứ tự ưu tiên](file:///E:/MyProject/BurgerAgent/docs/product/burgeragent-core-qa-qc.md#L76)
  - [TC-005: Tính toán in 2 mặt (2nd Print Cost)](file:///E:/MyProject/BurgerAgent/docs/product/burgeragent-core-qa-qc.md#L77)
  - [TC-006: Đánh giá rủi ro SLA vận chuyển](file:///E:/MyProject/BurgerAgent/docs/product/burgeragent-core-qa-qc.md#L78)

---

## 2. Đặc tả Kỹ thuật
- **Công thức Landed Cost:**
  - `Landed Cost` = `Base Cost + Print Cost + Shipping Fee + Tax`.
  - Trong đó: `Tax = (Base Cost + Print Cost + Shipping Fee) * Mức thuế suất`.
  - Thuế suất mặc định: US = `8.25%`, EU = `19.00%`, VN = `10.00%`.
  - Làm tròn tiền tệ: Làm tròn đến 2 chữ số thập phân (`round(value, 2)`).
- **Quy tắc tính Giá bán lẻ đề xuất & Margin:**
  - `Margin` = `(Retail Price - Landed Cost) / Retail Price * 100`.
  - Xác định `Retail Price` theo thứ tự ưu tiên:
    1. Nhận dạng trực tiếp từ câu hỏi của seller (Ví dụ: "bán giá $25").
    2. Cấu hình `Target Margin` trong Preferences của Seller: `Retail Price = Landed Cost / (1 - Target Margin)`.
    3. Nếu Preferences trống, áp dụng Target Margin mặc định là `40%`.
- **Logic đánh giá rủi ro SLA:**
  - Đọc lịch sử vận đơn từ DB SQLite.
  - Tính trung bình độ lệch: `avg_delay = sum(max(0, actual_days - expected_days)) / total_shipments`.
  - Nếu `avg_delay > 2` ngày -> Gán nhãn rủi ro `"Cao"`, ngược lại là `"Thấp"`.

---

## 3. Kế hoạch Triển khai (Mã nguồn & Cấu trúc)
1. **Khởi tạo Engine Python:**
   - Tạo file [ai/app/tools/calculation.py](file:///E:/MyProject/BurgerAgent/docs/product/burgeragent-backend-ai-structure.md#L113) chứa lớp `PythonCalculationEngine`.
   - Triển khai phương thức tĩnh `calculate_landed_cost` thực hiện phép cộng và nhân thuế suất theo đúng công thức tài chính.
   - Triển khai phương thức tĩnh `calculate_margin` nhận retail_price và landed_cost, kiểm tra tránh lỗi chia cho 0.
   - Triển khai phương thức tĩnh `evaluate_sla_risk` xử lý mảng tuple `(actual_days, expected_days)`.
2. **Xây dựng LangChain Tools Wrapper:**
   - Tạo hàm `@tool` wrapper `calculate_landed_cost_tool` để bọc các hàm tính toán của Engine.
   - Định nghĩa kiểu dữ liệu đầu vào cho Tool bằng Pydantic (ví dụ: `base_cost: float`, `print_cost: float`, `shipping_fee: float`, `destination: str`, `retail_price: Optional[float]`).
   - Tích hợp logic tìm kiếm thứ tự ưu tiên của retail_price bên trong tool để quyết định margin.
3. **Liên kết với LangGraph:**
   - Đăng ký `calculate_landed_cost_tool` vào danh sách công cụ của LangGraph.
   - Viết system prompt cấm LLM tự tính toán số học, bắt buộc phải gọi tool này khi cần đưa ra con số Landed Cost hay Margin cho Seller.

---

## 4. Kịch bản Kiểm thử & QA/QC (Không Mock Data)
- **TC-CALC-001: Tính Landed Cost và Thuế suất chính xác**
  - **Mục tiêu:** Kiểm tra kết quả tính thuế và landed cost không sai số.
  - **Cách test:** Chạy unit test truyền dữ liệu: `base_cost=10.00`, `print_cost=2.50`, `shipping_fee=3.00`, `destination="US"` (thuế 8.25%).
    - Subtotal = 10 + 2.5 + 3 = 15.5.
    - Tax = 15.5 * 8.25% = 1.27875 -> 1.28.
    - Landed Cost = 15.5 + 1.28 = 16.78.
    - Kết quả trả về phải khớp chính xác 16.78.
- **TC-CALC-002: Lựa chọn thứ tự ưu tiên của Margin**
  - **Mục tiêu:** Kiểm tra Margin được tính theo đúng thứ tự ưu tiên giá bán lẻ.
  - **Cách test:** Chạy unit test truyền landed_cost = 20.00.
    1. Khi truyền retail_price = 30.00 -> Margin = (30-20)/30 = 33.33%.
    2. Khi không truyền retail_price, truyền Target Margin của Seller = 30% -> Retail Price đề xuất = 20 / 0.7 = 28.57. Margin = 30%.
    3. Khi không truyền retail_price và Preferences trống -> Tự áp dụng target margin mặc định 40% -> Retail Price đề xuất = 20 / 0.6 = 33.33. Margin = 40%.
- **TC-CALC-003: Phân loại rủi ro SLA**
  - **Mục tiêu:** Phân loại đúng mức độ rủi ro dựa trên độ lệch ngày giao hàng.
  - **Cách test:** Truyền lịch sử giao hàng thực tế/cam kết: `[(5, 3), (7, 5), (6, 4)]` (lệch trung bình = 2 ngày). Kết quả trả về phải là rủi ro `"Thấp"`. Thử với mảng `[(6, 3), (8, 5), (7, 4)]` (lệch trung bình = 3 ngày) -> Kết quả phải trả về rủi ro `"Cao"`.
