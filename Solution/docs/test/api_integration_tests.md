# API GATEWAY & INTEGRATION TEST SPECIFICATION

Tài liệu này đặc tả chi tiết các kịch bản kiểm thử tích hợp (Integration Test cases) cho cổng API Gateway (FastAPI Backend) và các dịch vụ ngoại vi (BurgerPrints API Sandbox). Đảm bảo giao thức truyền tải JSON và cơ chế bảo mật hoạt động đúng theo hợp đồng dữ liệu.

Tài liệu này được thiết kế thống nhất và liên kết chặt chẽ với [System Architecture](file:///E:/Hackathon2026/J4F/Solution/docs/architecture/architecture.md), [API & Tool Contract](file:///E:/Hackathon2026/J4F/Solution/docs/ai/api_and_tool_contract.md), và [Project Structure & Layout](file:///E:/Hackathon2026/J4F/Solution/docs/ai/project_structure_and_layout.md).

---

## 1. Kiểm Thử API FastAPI Backend (RESTful Endpoints)

Các API endpoints trong thư mục `@Product/backend/app/api/v1/` cần được xác thực bằng thư viện `httpx` hoặc `requests` thông qua `TestClient` của FastAPI.

### 1.1. Module Xác thực (Authentication Endpoints)

#### Test Case AUTH-001: Đăng ký tài khoản Seller mới (Register)
*   **Endpoint:** `POST /api/v1/auth/register`
*   **Request Payload:**
    ```json
    {
      "email": "seller_test@example.com",
      "password": "SecurePassword123",
      "store_name": "Test Store"
    }
    ```
*   **Expected Response (HTTP 201 Created):**
    ```json
    {
      "success": true,
      "message": "User registered successfully",
      "user_id": "usr_uuid_v4_string"
    }
    ```
*   **Xác thực cơ sở dữ liệu:** Truy vấn bảng `users` trong SQLite, email `"seller_test@example.com"` phải tồn tại và mật khẩu được hash bằng bcrypt (không được lưu clear text).

#### Test Case AUTH-002: Đăng nhập nhận Token (Login)
*   **Endpoint:** `POST /api/v1/auth/login`
*   **Request Payload:**
    ```json
    {
      "email": "seller_test@example.com",
      "password": "SecurePassword123"
    }
    ```
*   **Expected Response (HTTP 200 OK):**
    ```json
    {
      "access_token": "jwt_token_string_here",
      "token_type": "bearer",
      "user": {
        "email": "seller_test@example.com",
        "store_name": "Test Store"
      }
    }
    ```
*   **Xác thực bảo mật:** Giải mã JWT Token bằng khóa bí mật, payload phải chứa `sub` là `user_id`.

---

### 1.2. Module Hội thoại (Chat Endpoints)

#### Test Case CHAT-001: Gửi tin nhắn mới (Send Message)
*   **Endpoint:** `POST /api/v1/chat/message`
*   **Headers:** `Authorization: Bearer jwt_token_string`
*   **Request Payload:**
    ```json
    {
      "thread_id": "optional_conv_uuid_v4",  -- Nếu trống, FastAPI tự sinh thread mới
      "message": "Tìm áo thun Unisex gửi đi Mỹ giá vốn dưới $10"
    }
    ```
*   **Expected Response (HTTP 200 OK):**
    ```json
    {
      "thread_id": "conv_uuid_v4",
      "response_text": "Em đã tìm thấy 3 phương án tối ưu...",
      "metadata": {
        "slots": {
          "product_type": "Unisex T-Shirt",
          "market": "US",
          "max_cogs": 10.0
        },
        "has_comparison_table": true,
        "options": [
          {
            "option_id": "opt_swift_us_01",
            "factory_name": "SwiftPrint Atlanta",
            "landed_cost": 8.50,
            "delivery_days_max": 5
          }
        ]
      }
    }
    ```
*   **Xác thực lưu trữ:** Bảng `conversations` phải có bản ghi cho `thread_id`. Bảng `messages` phải chứa 2 bản ghi mới (tin nhắn của user và câu trả lời của agent).

#### Test Case CHAT-002: Truy xuất lịch sử hội thoại (Chat History)
*   **Endpoint:** `GET /api/v1/chat/history/{conversation_id}`
*   **Headers:** `Authorization: Bearer jwt_token`
*   **Expected Response (HTTP 200 OK):**
    ```json
    {
      "conversation_id": "conv_uuid_v4",
      "title": "Tìm áo thun Unisex gửi đi Mỹ...",
      "messages": [
        {
          "sender": "user",
          "content": "Tìm áo thun Unisex gửi đi Mỹ...",
          "created_at": "2026-06-06T10:45:00Z"
        },
        {
          "sender": "assistant",
          "content": "Em đã tìm thấy 3 phương án...",
          "metadata": "json_string_or_object_matching_comparison_data",
          "created_at": "2026-06-06T10:45:05Z"
        }
      ]
    }
    ```

---

### 1.3. Module Đơn hàng (Order Endpoints)

#### Test Case ORD-001: Đẩy đơn hàng thật lên BurgerPrints (Execute Order)
*   **Endpoint:** `POST /api/v1/order/confirm`
*   **Headers:** `Authorization: Bearer jwt_token`
*   **Request Payload:**
    ```json
    {
      "thread_id": "conv_uuid_v4",
      "selected_option_id": "opt_swift_us_01",
      "shipping_address": {
        "full_name": "David Miller",
        "address_line1": "742 Evergreen Terrace",
        "city": "Springfield",
        "state": "IL",
        "zip_code": "62704",
        "country_code": "US",
        "phone": "+12175550143"
      }
    }
    ```
*   **Expected Response (HTTP 201 Created):**
    ```json
    {
      "success": true,
      "order_id": "bp_ord_88776655",
      "status": "pending",
      "tracking_number": "USPS-9400100000000000000000",
      "total_cogs": 12.20
    }
    ```
*   **Xác thực lưu trữ:** Bản ghi mới được tạo trong bảng `order_history` liên kết với `conversation_id`, trạng thái là `"pending"`.

---

## 2. Kiểm Thử Tích Hợp BurgerPrints API v2.0 (External API Integration)

Mã nguồn tại `@Product/ai/tools.py` chịu trách nhiệm gọi BurgerPrints API. Việc kiểm thử tích hợp này được chia thành hai cấu hình môi trường.

### 2.1. Cấu hình kiểm thử giả lập (`USE_MOCK_API=true`)
*   **Mục tiêu:** Cho phép chạy test suite độc lập, ổn định và nhanh chóng trong CI/CD hoặc môi trường không có kết nối internet.
*   **Cơ chế:**
    *   Hàm `search_catalog` không gửi HTTP Request, mà đọc file dữ liệu mẫu: `@Product/ai/data/mock_catalog.json`.
    *   Hàm `get_factory_quotes` đọc file: `@Product/ai/data/mock_quotes.json`.
    *   Hàm `get_shipping_options` trả về danh sách gói cước tĩnh được tính sẵn.
    *   Hàm `create_order` luôn trả về `"success": true` và một ID đơn hàng giả lập ngẫu nhiên dạng `bp_ord_mock_xxxx`.
*   **Test Case MOCK-001:** Xác minh rằng khi bật mock api, tốc độ phản hồi của các hàm wrapper phải < 50ms và trả về cấu hình dữ liệu đúng cấu trúc Pydantic Schema.

### 2.2. Cấu hình tích hợp thực tế (`USE_MOCK_API=false`)
*   **Mục tiêu:** Đảm bảo hệ thống tích hợp thông suốt với cổng Sandbox thực tế của BurgerPrints trước khi bàn giao sản phẩm.
*   **Cơ chế:**
    *   Sử dụng thư viện `httpx.Client` gửi HTTPS Request lên `https://api.burgerprints.com/v2/`.
    *   Tự động chèn query parameter `apiKey` lấy từ biến môi trường `BURGERPRINTS_API_KEY`.
*   **Test Case REAL-001: Tra cứu catalog thực tế**
    *   **Action:** Gọi hàm `search_catalog(query="T-shirt")`.
    *   **Expected Result:** HTTP Status Code = 200. Danh sách trả về chứa các đối tượng có `product_id` hợp lệ.
*   **Test Case REAL-002: Báo lỗi khi sai API Key**
    *   **Action:** Đặt cấu hình `BURGERPRINTS_API_KEY=invalid_key` và thực hiện cuộc gọi.
    *   **Expected Result:** Hệ thống bắt lỗi HTTP 401 Unauthorized từ BurgerPrints API, ném ngoại lệ `BurgerPrintsAuthError`, và Agent phản hồi lịch sự trên giao diện chat: `"API Key của BurgerPrints không hợp lệ. Bạn vui lòng cấu hình lại trong cài đặt."`
*   **Test Case REAL-003: Xử lý sự cố sập API (API Fallback)**
    *   **Action:** Mô phỏng sự cố bằng cách cấu hình Base URL trỏ đến IP không tồn tại (Timeout).
    *   **Expected Result:** Hệ thống bắt được lỗi `ConnectTimeout` trong tối đa 5 giây. Tự động kích hoạt cơ chế fallback đọc từ dữ liệu Mock cục bộ và ghi log cảnh báo: `"BurgerPrints API Timeout, falling back to mock memory"`.
