# Kế hoạch triển khai: Self-Healing Schema Mapper (AI - Giai đoạn 1)

## 1. Liên kết Yêu cầu & Tài liệu tham chiếu
- **User Story liên quan:**
  - [US-001: Tra Cứu & So Sánh Xưởng Qua Chatbot - Lỗi kết nối offline](file:///E:/MyProject/BurgerAgent/docs/product/burgeragent-core-prd.md#L105-L109)
- **Functional Requirements:**
  - [F-6: Tự Phục Hồi Schema (Self-healing) - Giai đoạn 1](file:///E:/MyProject/BurgerAgent/docs/product/burgeragent-core-prd.md#L303-L304)
- **Technical Constraints & Architecture:**
  - [Cơ chế Tự Phục Hồi Schema (Self-healing Schema Mapper)](file:///E:/MyProject/BurgerAgent/docs/product/burgeragent-core-prd.md#L282-L286)
  - [Harness Component 4: Sub-Agents (SelfHealingMapperSubAgent)](file:///E:/MyProject/BurgerAgent/docs/product/burgeragent-core-ai-engine.md#L106-L109)
  - [Module Tự Phục Hồi Schema (Self-Healing Loop)](file:///E:/MyProject/BurgerAgent/docs/product/burgeragent-core-ai-engine.md#L326-L356)
  - [Cơ chế Tự Phục Hồi Schema Sequence Diagram](file:///E:/MyProject/BurgerAgent/docs/product/burgeragent-core-architecture.md#L295-L325)
- **QA/QC Test Cases:**
  - [TC-017: Cơ chế tự phục hồi Schema (Self-healing)](file:///E:/MyProject/BurgerAgent/docs/product/burgeragent-core-qa-qc.md#L110)

---

## 2. Đặc tả Kỹ thuật
- **Nguyên lý hoạt động:**
  - Khi đồng bộ, nếu thư viện JSONPath trả về `None` cho các trường giá trị bắt buộc -> Phát sinh ngoại lệ `ParsingException`.
  - Hệ thống kích hoạt `SelfHealingMapperSubAgent` chạy ngầm.
  - Subagent gọi LLM phân tích cấu trúc JSON mới để tìm các trường có ý nghĩa tương đương và sinh tệp cấu hình `mapping_metadata.json` mới.
  - Ghi đè tệp tin và thực hiện parse lại Catalog thô.
  - Cảnh báo đến Kênh Telegram Admin của Quản trị viên.

---

## 3. Kế hoạch Triển khai (Mã nguồn & Cấu trúc)
1. **Thiết lập File Metadata Mapping mặc định:**
   - Tạo file [ai/app/schema_mapper/mapping_metadata.json](file:///E:/MyProject/BurgerAgent/docs/product/burgeragent-backend-ai-structure.md#L122) lưu cấu trúc JSONPath ánh xạ mặc định cho các trường: `base_sku`, `base_price`, `second_side_price`, `third_side_price`, `variants`, `factory_name`.
2. **Xây dựng Self-Healing Parser Module:**
   - Tạo file [ai/app/schema_mapper/mapper.py](file:///E:/MyProject/BurgerAgent/docs/product/burgeragent-backend-ai-structure.md#L121).
   - Triển khai hàm `parse_raw_catalog(data_raw: dict) -> dict` sử dụng thư viện JSONPath dựa trên file metadata mapping.
   - Nếu parse thất bại (ví dụ không tìm thấy `base_price`), ném lỗi `ParsingException`.
3. **Phát triển SelfHealingMapperSubAgent:**
   - Triển khai subagent độc lập sử dụng Gemini API.
   - Thiết lập System Prompt chỉ thị cho Subagent:
     - Nhận vào cấu hình mapping cũ và gói JSON response API BurgerPrints mới.
     - Phân tích cấu trúc ngữ nghĩa của các trường trong JSON mới.
     - Khai thác lại các đường dẫn JSONPath chính xác thay thế cho các trường bị thiếu.
     - Xuất ra duy nhất chuỗi JSON hợp lệ khớp với cấu trúc metadata.
4. **Viết cơ chế Ghi đè & Thử lại (Retry Loop):**
   - Viết hàm điều phối: Khi bắt được `ParsingException` trong Sync Service -> Gọi Subagent -> Ghi đè file `mapping_metadata.json` mới -> Gọi lại hàm parse -> Nếu thành công, tiếp tục tiến trình sync và gọi Telegram API thông báo admin.

---

## 4. Kịch bản Kiểm thử & QA/QC (Không Mock Data)
- **TC-HEAL-001: Phát hiện lỗi parse và kích hoạt tự phục hồi**
  - **Mục tiêu:** Kiểm tra hệ thống tự động sinh lại file mapping khi API đối tác đổi tên trường.
  - **Cách test:**
    1. Chuẩn bị file dữ liệu JSON mẫu có trường `"price"` đổi tên thành `"base_price_new"`.
    2. Chạy hàm parse với cấu hình cũ (đang trỏ tới `$.price`) -> Phải bắt được lỗi `ParsingException`.
    3. Trình điều phối kích hoạt Subagent -> Subagent gọi LLM -> LLM phải nhận diện được `"base_price_new"` đại diện cho giá base và cập nhật path thành `$.base_price_new` trong `mapping_metadata.json`.
    4. Kiểm tra file `mapping_metadata.json` trên ổ đĩa xem có tự động cập nhật hay không.
    5. Hàm parse chạy lại -> Phải parse thành công và lấy đúng giá trị giá phôi áo.
- **TC-HEAL-002: Cảnh báo Telegram Admin**
  - **Mục tiêu:** Đảm bảo bắn tin nhắn thông báo cho quản trị viên sau khi phục hồi thành công.
  - **Cách test:** Cấu hình Telegram bot token và Chat ID admin. Khi kết thúc quy trình tự phục hồi, kiểm tra group chat admin trên Telegram phải nhận được tin nhắn cảnh báo dạng: *"Hệ thống tự động cập nhật API Mapping thành công cho [Product ID]"*.
