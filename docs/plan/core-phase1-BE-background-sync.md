# Kế hoạch triển khai: Background Sync Service (BE - Giai đoạn 1)

## 1. Liên kết Yêu cầu & Tài liệu tham chiếu
- **User Story liên quan:**
  - [US-001: Tra Cứu & So Sánh Xưởng Qua Chatbot - Offline Mode](file:///E:/MyProject/BurgerAgent/docs/product/burgeragent-core-prd.md#L105-L109)
- **Functional Requirements:**
  - [F-1: Thiết kế LangGraph Stateful Agent Loop - Domain Retrieval](file:///E:/MyProject/BurgerAgent/docs/product/burgeragent-core-prd.md#L182-L195)
  - [F-2: Công Cụ Tính Toán Độc Lập - Query Shipping Rate API](file:///E:/MyProject/BurgerAgent/docs/product/burgeragent-core-prd.md#L202)
- **Technical Constraints & Architecture:**
  - [Cơ chế Sync dữ liệu & Hiệu năng](file:///E:/MyProject/BurgerAgent/docs/product/burgeragent-core-prd.md#L268-L270)
  - [Tự phục hồi (Self-healing)](file:///E:/MyProject/BurgerAgent/docs/product/burgeragent-core-prd.md#L282-L286)
  - [SyncBackgroundService component](file:///E:/MyProject/BurgerAgent/docs/product/burgeragent-core-architecture.md#L97-L102)
  - [Cơ chế Tự Phục Hồi Schema Sequence Diagram](file:///E:/MyProject/BurgerAgent/docs/product/burgeragent-core-architecture.md#L295-L325)
- **QA/QC Test Cases:**
  - [TC-016: Chạy tiến trình nền đồng bộ dữ liệu](file:///E:/MyProject/BurgerAgent/docs/product/burgeragent-core-qa-qc.md#L107-L109)
  - [TC-017: Cơ chế tự phục hồi Schema (Self-healing)](file:///E:/MyProject/BurgerAgent/docs/product/burgeragent-core-qa-qc.md#L110-L111)

---

## 2. Đặc tả Kỹ thuật
- **Chu kỳ thực thi:** Mặc định chạy ngầm định kỳ mỗi 5 giờ.
- **Tính bất đồng bộ (Async Job):** Việc đồng bộ lớn có thể được kích hoạt thủ công qua API. Trả về `jobId` ngay lập tức để tránh client bị timeout (Pattern 6 - Async Request-Response).
- **Cơ chế gọi API:**
  - Đọc API Key của BurgerPrints từ `.env` để làm thông tin xác thực.
  - Sử dụng thư viện `httpx` (Asynchronous HTTP Client) với cơ chế Retry Exponential Backoff (1s, 2s, 4s) khi gặp lỗi 429 hoặc 5xx.
  - Lưu trữ lịch sử chạy job (status, progress_percent, details) trong DB SQLite phục vụ polling kiểm tra trạng thái.

---

## 3. Kế hoạch Triển khai (Mã nguồn & Cấu trúc)
1. **Xây dựng HTTP Client giao tiếp BurgerPrints API:**
   - Triển khai trong [backend/app/services/sync_service.py](file:///E:/MyProject/BurgerAgent/docs/product/burgeragent-backend-ai-structure.md#L83).
   - Hàm `GET` lấy toàn bộ bases sản phẩm từ `/v2/product`.
   - Hàm `GET` chi tiết từng base sản phẩm bằng `short_code` để lấy variations, giá base, giá in 2nd_price từ `/v2/product/{id}`.
2. **Thiết lập Background Scheduler:**
   - Tích hợp `FastAPI BackgroundTasks` cho các request thủ công hoặc `APScheduler` để đăng ký job định kỳ mỗi 5 giờ.
   - Thiết lập job tự chạy khi hệ thống khởi động để đảm bảo cache không bị trống trong lần khởi chạy đầu tiên.
3. **Triển khai Quy trình Phân tách JSON & Đồng bộ Index FTS5:**
   - Lặp qua danh sách sản phẩm tải về từ API BurgerPrints.
   - Gọi `CatalogRepository` để lưu đè dữ liệu JSON thô vào cột `data_raw_json` của bảng `catalog_cache`.
   - Gọi logic đồng bộ bóc tách các trường văn bản mô tả sản phẩm sang bảng ảo `catalog_fts5`.
4. **Xử lý Exception & Cơ chế Tự Phục Hồi (Self-Healing Bridge):**
   - Đọc tệp cấu hình mapping hiện tại `mapping_metadata.json`.
   - Khi parse dữ liệu, nếu gặp lỗi `KeyError` hoặc giá trị trường bắt buộc (`price`, `short_code`) trả về `None`, ném ra ngoại lệ `ParsingException`.
   - Bắt ngoại lệ `ParsingException` và gửi HTTP request sang AI Service (Port 8001) endpoint `/v1/inference/self-healing` kèm JSON payload lỗi và mapping cũ để AI tự phục hồi file mapping.
   - Sau khi AI Service sửa xong file mapping, tiến trình sync tự nạp lại mapping mới và tiếp tục thực hiện parse dữ liệu, tránh bị block.
   - Bắn thông báo thông qua Telegram Webhook báo lỗi/hoàn thành sync về group quản trị.

---

## 4. Kịch bản Kiểm thử & QA/QC (Không Mock Data)
- **TC-SYNC-001: Kích hoạt Sync thủ công qua API và Polling**
  - **Mục tiêu:** Kiểm tra luồng Async Sync Job trả về jobId và cho phép kiểm tra tiến độ qua polling endpoint.
  - **Cách test:**
    1. Gửi request `POST /v1/orders/sync` -> Phải trả về `202 Accepted` kèm `jobId` và trạng thái `"pending"`.
    2. Gửi request liên tục `GET /v1/jobs/{jobId}` -> Phải trả về tiến độ `progress_percent` tăng dần và trạng thái `"processing"`.
    3. Đợi tiến trình kết thúc, kiểm tra kết quả `GET /v1/jobs/{jobId}` -> Phải trả về trạng thái `"completed"` kèm chi tiết số lượng item đã đồng bộ.
- **TC-SYNC-002: Tự động chạy nền định kỳ**
  - **Mục tiêu:** Kiểm tra background scheduler hoạt động đúng thời gian.
  - **Cách test:** Cấu hình tạm thời chu kỳ sync là 10 giây (để test). Bật logs hệ thống -> Kiểm tra log xem background task có tự động chạy lại mỗi 10 giây mà không cần kích hoạt từ API hay không.
- **TC-SYNC-003: Xử lý lỗi API BurgerPrints (Retry Backoff)**
  - **Mục tiêu:** Đảm bảo hệ thống tự động retry khi API đối tác bị quá tải.
  - **Cách test:** Cấu hình mock endpoint BurgerPrints API trả về mã lỗi `429 Too Many Requests` trong 2 lần gọi đầu, lần thứ 3 trả về `200 OK`. Chạy job sync -> Quan sát log hệ thống phải hiển thị việc thực hiện gọi lại (retry) lần lượt sau 1 giây và 2 giây, và hoàn thành thành công ở lần thứ 3.
