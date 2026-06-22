# Kế hoạch triển khai: API Gateway, Authentication & Chat Relay (BE - Giai đoạn 1)

## 1. Liên kết Yêu cầu & Tài liệu tham chiếu
- **User Story liên quan:**
  - [US-001: Tra Cứu & So Sánh Xưởng Qua Chatbot - Đăng nhập & Preferences](file:///E:/MyProject/BurgerAgent/docs/product/burgeragent-core-prd.md#L96-L100)
- **Functional Requirements:**
  - [F-1: Thiết kế LangGraph Stateful Agent Loop - Memory SQLite Session](file:///E:/MyProject/BurgerAgent/docs/product/burgeragent-core-prd.md#L182-L184)
  - [Bộ nhớ dài hạn (Long-term Profile Memory)](file:///E:/MyProject/BurgerAgent/docs/product/burgeragent-core-prd.md#L258-L261)
- **Technical Constraints & Architecture:**
  - [Bảo mật & Mã hóa tài khoản](file:///E:/MyProject/BurgerAgent/docs/product/burgeragent-core-prd.md#L274-L275)
  - [API Controller & Relay chat](file:///E:/MyProject/BurgerAgent/docs/product/burgeragent-core-architecture.md#L120-L122)
  - [Nguyên Tắc Thiết Kế API & Consistent Response](file:///E:/MyProject/BurgerAgent/docs/product/burgeragent-core-api.md#L14-L56)
  - [Nhóm Xác Thực & Cấu Hình & Hội Thoại API](file:///E:/MyProject/BurgerAgent/docs/product/burgeragent-core-api.md#L64-L68)
  - [Đặc Tả Chi Tiết Chat Bot API (/v1/chat)](file:///E:/MyProject/BurgerAgent/docs/product/burgeragent-core-api.md#L82-L141)
- **QA/QC Test Cases:**
  - [TC-004b: Tính toán Biên lợi nhuận (Margin %) theo thứ tự ưu tiên - Preferences](file:///E:/MyProject/BurgerAgent/docs/product/burgeragent-core-qa-qc.md#L76)

---

## 2. Đặc tả Kỹ thuật
- **Bảo mật:**
  - Sử dụng thư viện `bcrypt` để băm mật khẩu (`password_hash`) trước khi lưu DB.
  - Sử dụng JWT (JSON Web Tokens) với thuật toán `HS256` để xác thực người dùng. Token chứa các claims: `sub` (User ID), `exp` (Thời gian hết hạn).
- **Thiết kế API:**
  - Toàn bộ API bắt buộc tuân thủ Envelope Schema nhất quán cho cả trường hợp Thành công và Lỗi.
  - Endpoint `POST /v1/chat` yêu cầu Authorization Header: `Bearer [JWT_TOKEN]`.
- **Giao tiếp liên dịch vụ (Service-to-Service):**
  - Backend (Port 8000) đóng vai trò Gateway nhận chat request từ Web Client.
  - Backend sử dụng `ai_client.py` để gửi HTTP POST request sang AI Service (Port 8001) tại path `/v1/inference`.
  - Phản hồi từ AI Service được giải nén và đóng gói vào Response Envelope chuẩn để trả về Web Client.

---

## 3. Kế hoạch Triển khai (Mã nguồn & Cấu trúc)
1. **Xây dựng module Bảo mật & Đăng nhập:**
   - Triển khai các hàm helper `get_password_hash`, `verify_password`, `create_access_token` trong [backend/app/core/security.py](file:///E:/MyProject/BurgerAgent/docs/product/burgeragent-backend-ai-structure.md#L60).
   - Định nghĩa Schema dữ liệu đăng ký/đăng nhập (Pydantic models) trong lớp DTO.
2. **Triển khai dependency xác thực:**
   - Viết hàm `get_current_user` trong [backend/app/api/dependencies.py](file:///E:/MyProject/BurgerAgent/docs/product/burgeragent-backend-ai-structure.md#L56) kiểm tra header `Authorization`. Giải mã JWT, tìm kiếm `User` trong DB, nếu không hợp lệ trả về lỗi `401 Unauthorized` theo mẫu Error Envelope.
3. **Phát triển Auth Endpoints:**
   - Tạo file [backend/app/api/v1/endpoints/auth.py](file:///E:/MyProject/BurgerAgent/docs/product/burgeragent-backend-ai-structure.md#L51).
   - Triển khai `POST /v1/auth/register`: Validate email không trùng lặp, lưu `User` mới, đồng thời tự động tạo một bản ghi `UserPreferences` trống mặc định.
   - Triển khai `POST /v1/auth/login`: Xác thực mật khẩu, trả về JWT Access Token.
4. **Phát triển Preferences Endpoints:**
   - Triển khai `GET /v1/preferences` và `PUT /v1/preferences` trong router cấu hình. Cho phép cập nhật preferred_market, target_margin, max_sla_days, priority_criteria.
5. **Xây dựng Chat Relay Controller:**
   - Tạo file [backend/app/api/v1/endpoints/chat_relay.py](file:///E:/MyProject/BurgerAgent/docs/product/burgeragent-backend-ai-structure.md#L52).
   - Endpoint `POST /v1/chat` nhận `session_id` và `message`.
   - Gọi `UserRepository` lấy preferences của User hiện tại.
   - Sử dụng `AIClient` (trong [backend/app/services/ai_client.py](file:///E:/MyProject/BurgerAgent/docs/product/burgeragent-backend-ai-structure.md#L82)) để POST dữ liệu (`message`, `session_id`, `preferences`) sang AI Service ở cổng 8001.
   - Ghi nhận lịch sử hội thoại của User vào bảng `chat_history`.

---

## 4. Kịch bản Kiểm thử & QA/QC (Không Mock Data)
- **TC-AUTH-001: Đăng ký tài khoản và mã hóa mật khẩu**
  - **Mục tiêu:** Đảm bảo đăng ký thành công và mật khẩu không bị lưu dưới dạng plain text.
  - **Cách test:** Gọi API `POST /v1/auth/register` với email `"test@burgeragent.com"` và password `"Secret123"`. Kiểm tra DB SQLite -> Phải xuất hiện user mới và trường `password_hash` phải là chuỗi bcrypt đã băm (bắt đầu bằng `$2b$`).
- **TC-AUTH-002: Đăng nhập nhận JWT Token**
  - **Mục tiêu:** Lấy JWT Token hợp lệ khi gửi đúng credentials.
  - **Cách test:** Gọi API `POST /v1/auth/login` với thông tin vừa đăng ký. Phản hồi phải trả về `200 OK` chứa token. Thử đăng nhập lại với sai password -> Phải trả về lỗi `400 Bad Request` dạng Error Envelope.
- **TC-AUTH-003: Cập nhật Preferences thành công**
  - **Mục tiêu:** Lưu thay đổi preferences của user.
  - **Cách test:** Gọi `PUT /v1/preferences` với body: `{"preferred_market": "EU", "target_margin": 0.35}` kèm Header `Authorization: Bearer [token]`. Sau đó gọi `GET /v1/preferences` -> Dữ liệu trả về phải trùng khớp với cấu hình vừa đổi.
- **TC-CHAT-001: Relay chat sang AI Service**
  - **Mục tiêu:** Kiểm tra backend truyền tin nhắn thành công sang AI Engine và trả về đúng envelope.
  - **Cách test:** Khởi chạy đồng thời cả Backend (Port 8000) và AI Service (Port 8001). Gửi request `POST /v1/chat` -> Phải nhận về response chứa trường `response_text` và `comparison_data` được đóng gói đúng chuẩn Success Envelope.
