# ĐẶC TẢ GIAO DIỆN LẬP TRÌNH ỨNG DỤNG (REST API SPECIFICATION)
## DỰ ÁN: BURGERAGENT CORE (HỆ THỐNG CỐT LÕI)

> [!IMPORTANT]
> **Tên tài liệu:** Tài liệu Đặc tả REST API BurgerAgent Core
> **Phiên bản:** v1.0.0
> **Ngày cập nhật:** 2026-06-16
> **Trạng thái:** DỰ THẢO (Sẵn sàng phát triển)
> 
> Tài liệu này được thiết kế tuân thủ 7 thiết kế mẫu REST API chuẩn (**API Design Patterns**): Versioning, Pagination, Filtering, Field Selection, Expansion, Async Request-Response, và Consistent Response.

---

## 1. Nguyên Tắc Thiết Kế Chung (API Design Guide)

### 1.1. Phiên bản hóa (Pattern 1 - Versioning)
Mọi endpoint trong hệ thống đều bắt buộc sử dụng tiền tố phiên bản `/v1/` trong URL path để đảm bảo tính ổn định và không làm sập các ứng dụng client cũ khi hệ thống nâng cấp.

### 1.2. Cấu trúc Phản hồi Nhất quán (Pattern 7 - Consistent Response)
Hệ thống sử dụng một cấu trúc bao đóng (Response Envelope) thống nhất cho tất cả các phản hồi (Thành công, Lỗi Client 4xx, Lỗi Server 5xx):

#### Định dạng Phản hồi Thành công (Success Envelope):
```json
{
  "success": true,
  "statusCode": 200,
  "message": "Mô tả kết quả thành công",
  "data": { ... },
  "meta": {
    "timestamp": "2026-06-16T15:00:00.000Z",
    "requestId": "req-9e2e-4b72-a1c2-df80bfe"
  }
}
```

#### Định dạng Phản hồi Lỗi (Error Envelope):
```json
{
  "success": false,
  "statusCode": 400,
  "message": "Mô tả lỗi tổng quát cho người dùng",
  "error": {
    "code": "ERROR_CODE_STRING",
    "details": [
      {
        "field": "tên_trường_bị_lỗi",
        "message": "Chi tiết lỗi dữ liệu"
      }
    ]
  },
  "meta": {
    "timestamp": "2026-06-16T15:01:00.000Z",
    "requestId": "req-9e2e-4b72-a1c2-df80bfe"
  }
}
```

---

## 2. API Surface Summary (Danh Sách Endpoints)

| Nhóm | Phương thức | Path | Mô tả | Ghi chú |
| :--- | :--- | :--- | :--- | :--- |
| **Xác thực** | POST | `/v1/auth/register` | Đăng ký tài khoản Seller mới | Validate mật khẩu và định dạng email. |
| **Xác thực** | POST | `/v1/auth/login` | Đăng nhập tài khoản | Trả về JWT Token. |
| **Cấu hình** | GET | `/v1/preferences` | Lấy cấu hình mặc định của Seller | Lấy thông tin Preferences từ DB. |
| **Cấu hình** | PUT | `/v1/preferences` | Cập nhật cấu hình mặc định | Có hiệu lực tức thì cho Agent xếp hạng. |
| **Hội thoại** | POST | `/v1/chat` | Gửi câu hỏi đến Trợ lý AI (Web) | Nhận câu trả lời và bảng so sánh. |
| **Hội thoại** | POST | `/v1/telegram/webhook` | Tiếp nhận tin nhắn từ Telegram | Webhook tích hợp với Telegram API. |
| **Mockups** | POST | `/v1/mockups/preview` | Render mockup lồng thiết kế | Xử lý ghép ảnh tĩnh trên backend. |
| **Đơn hàng** | POST | `/v1/orders` | Tạo đơn hàng fulfillment sandbox | Gọi trực tiếp API BurgerPrints. |
| **Đơn hàng** | GET | `/v1/orders` | Lấy danh sách đơn hàng đã đặt | Hỗ trợ phân trang, lọc trạng thái. |
| **Đơn hàng** | GET | `/v1/orders/{id}` | Lấy chi tiết đơn hàng | Hỗ trợ `?expand=tracking` trực tiếp. |
| **Đơn hàng** | POST | `/v1/orders/sync` | Kích hoạt tác vụ sync catalog thủ công | **Async Job** trả về `jobId`. |
| **Đơn hàng** | GET | `/v1/jobs/{id}` | Lấy trạng thái của Async Job | Polling kiểm tra tiến trình sync. |
| **Webhook** | POST | `/v1/orders/webhook` | Nhận trạng thái từ BurgerPrints | Webhook nhận cập nhật tự động. |

---

## 3. Đặc Tả Chi Tiết Các Endpoint Cốt Lõi (Endpoint Detail Specifications)

### 3.1. Nhóm Hội Thoại (Chat Bot API)

#### **POST** Gửi câu hỏi đến Trợ lý AI
- **Path:** `/v1/chat`
- **Mô tả:** Tiếp nhận prompt của seller từ Web client, nạp vào LangChain Agent Loop và phản hồi văn bản kèm dữ liệu bảng so sánh.
- **Request Headers:**
  - `Authorization`: `Bearer [JWT_TOKEN]`
- **Request Body:**
  ```json
  {
    "session_id": "session-123456",
    "message": "So sánh Hoodie các xưởng ship đi EU rẻ nhất"
  }
  ```
- **Response (`200 OK`):**
  ```json
  {
    "success": true,
    "statusCode": 200,
    "message": "Trợ lý phản hồi thành công",
    "data": {
      "response_text": "Dưới đây là bảng so sánh giá Hoodie từ các xưởng tối ưu nhất cho thị trường EU. Xưởng Factory A (VN) hiện là xưởng rẻ nhất về Landed Cost...",
      "thinking_log": "Intent extracted: Hoodie, Market: EU, Priority: Price. Querying database...",
      "comparison_data": {
        "target_product": "Hoodie",
        "target_market": "EU",
        "options": [
          {
            "recommended": true,
            "factory_name": "Factory A (VN)",
            "base_cost": 8.00,
            "print_cost": 3.50,
            "shipping_fee": 4.50,
            "tax": 3.04,
            "landed_cost": 19.04,
            "margin_percent": 45.6,
            "sla_days": "5-8 ngày",
            "sla_risk": "Low"
          },
          {
            "recommended": false,
            "factory_name": "Factory B (EU)",
            "base_cost": 10.50,
            "print_cost": 4.00,
            "shipping_fee": 3.00,
            "tax": 3.33,
            "landed_cost": 20.83,
            "margin_percent": 40.5,
            "sla_days": "3-5 ngày",
            "sla_risk": "Low"
          }
        ]
      }
    },
    "meta": {
      "timestamp": "2026-06-16T15:05:00.000Z",
      "requestId": "req-chat-789"
    }
  }
  ```

---

### 3.2. Nhóm Mockup Preview (Mockups API)

#### **POST** Render hình ảnh Mockup xem trước
- **Path:** `/v1/mockups/preview`
- **Mô tả:** Đè ảnh in ấn (Front/Back) lên phôi phông nền, xuất ảnh JPG/PNG. Dùng cho cả Web và Telegram.
- **Request Body:**
  ```json
  {
    "product_id": "USMCC1717",
    "color": "Black",
    "design_front_url": "https://example.com/designs/front.png",
    "design_back_url": "https://example.com/designs/back.png"
  }
  ```
- **Response (`200 OK`):**
  ```json
  {
    "success": true,
    "statusCode": 200,
    "message": "Tạo hình ảnh xem trước thành công",
    "data": {
      "mockup_front_url": "https://server.burgeragent.com/static/previews/USMCC1717-Black-front-composed.png",
      "mockup_back_url": "https://server.burgeragent.com/static/previews/USMCC1717-Black-back-composed.png",
      "print_cost_updated": 7.00
    },
    "meta": {
      "timestamp": "2026-06-16T15:06:00.000Z",
      "requestId": "req-mockup-111"
    }
  }
  ```

---

### 3.3. Nhóm Đơn Hàng (Orders API)

#### **GET** Lấy danh sách lịch sử đơn hàng
- **Path:** `/v1/orders`
- **Mô tả:** Lấy danh sách lịch sử đơn hàng của Seller (Pattern 2 - Pagination, Pattern 3 - Filtering, Pattern 4 - Field Selection).
- **Query Parameters:**
  - `page` (integer, optional): Trang hiện tại. Mặc định 1.
  - `limit` (integer, optional): Số đơn hiển thị một trang. Mặc định 20, max 100.
  - `status` (string, optional): Lọc theo trạng thái (`queued`, `place`, `shipped`, `failed`).
  - `fields` (string, optional): Lọc các trường trả về (VD: `order_id,sku,total_landed_cost,status`).
- **Request Example:** `/v1/orders?page=1&limit=2&status=shipped&fields=order_id,status,tracking_number`
- **Response (`200 OK`):**
  ```json
  {
    "success": true,
    "statusCode": 200,
    "message": "Truy xuất danh sách đơn hàng thành công",
    "data": [
      {
        "order_id": "BP-ORDER-9912",
        "status": "shipped",
        "tracking_number": "TRK-USPS-12345"
      },
      {
        "order_id": "BP-ORDER-9913",
        "status": "shipped",
        "tracking_number": "TRK-DHL-67890"
      }
    ],
    "meta": {
      "page": 1,
      "limit": 2,
      "total": 45,
      "totalPages": 23,
      "hasNext": true,
      "hasPrevious": false,
      "timestamp": "2026-06-16T15:10:00.000Z",
      "requestId": "req-list-orders-45"
    }
  }
  ```

#### **GET** Chi tiết đơn hàng & Mở rộng thông tin Tracking
- **Path:** `/v1/orders/{id}`
- **Mô tả:** Lấy chi tiết đơn hàng, cho phép mở rộng thông tin tracking trực tiếp từ BurgerPrints API (Pattern 5 - Expansion).
- **Query Parameters:**
  - `expand` (string, optional): Khai báo `tracking` để tự động kéo thông tin vận chuyển real-time của hãng ship.
- **Request Example:** `/v1/orders/BP-ORDER-9912?expand=tracking`
- **Response (`200 OK`):**
  ```json
  {
    "success": true,
    "statusCode": 200,
    "message": "Lấy chi tiết đơn hàng thành công",
    "data": {
      "order_id": "BP-ORDER-9912",
      "sku": "USMCC1717-Black-L",
      "quantity": 2,
      "total_landed_cost": 32.50,
      "status": "shipped",
      "created_at": "2026-06-16T08:00:00Z",
      "tracking": {
        "carrier": "USPS",
        "tracking_code": "9405500000000000000000",
        "tracking_url": "https://tools.usps.com/go/TrackConfirmAction?tLabels=9405500000000000000000",
        "estimated_delivery": "2026-06-20T18:00:00Z",
        "last_checkpoint": "Arrived at USPS Facility, JAMAICA, NY 11430"
      }
    },
    "meta": {
      "timestamp": "2026-06-16T15:12:00.000Z",
      "requestId": "req-detail-12"
    }
  }
  ```

---

### 3.4. Nhóm Tác Vụ Bất Đồng Bộ (Async Sync Jobs API)

#### **POST** Kích hoạt đồng bộ hóa dữ liệu thủ công
- **Path:** `/v1/orders/sync`
- **Mô tả:** Cho phép client hoặc quản trị viên kích hoạt đồng bộ hóa catalog và shipping rules thủ công. Do tác vụ này tốn thời gian gọi nhiều API và ghi DB, hệ thống áp dụng cơ chế bất đồng bộ (Pattern 6 - Async Request-Response).
- **Response (`202 Accepted`):**
  ```json
  {
    "success": true,
    "statusCode": 202,
    "message": "Tác vụ đồng bộ đã được tiếp nhận và xử lý ngầm",
    "data": {
      "jobId": "job-sync-5509",
      "status": "pending",
      "statusUrl": "/v1/jobs/job-sync-5509"
    },
    "meta": {
      "timestamp": "2026-06-16T15:15:00.000Z",
      "requestId": "req-sync-99"
    }
  }
  ```

#### **GET** Lấy trạng thái của Job bất đồng bộ
- **Path:** `/v1/jobs/{id}`
- **Mô tả:** Polling để kiểm tra trạng thái và tiến độ xử lý của Job ngầm.
- **Path Params:** `{id}`: Mã ID của job.
- **Response (`200 OK` - Khi đang chạy):**
  ```json
  {
    "success": true,
    "statusCode": 200,
    "message": "Tác vụ đang xử lý",
    "data": {
      "jobId": "job-sync-5509",
      "status": "processing",
      "progress_percent": 65
    },
    "meta": {
      "timestamp": "2026-06-16T15:16:00.000Z",
      "requestId": "req-job-check-1"
    }
  }
  ```
- **Response (`200 OK` - Khi hoàn thành):**
  ```json
  {
    "success": true,
    "statusCode": 200,
    "message": "Tác vụ đã hoàn thành xuất sắc",
    "data": {
      "jobId": "job-sync-5509",
      "status": "completed",
      "completed_at": "2026-06-16T15:16:30Z",
      "details": {
        "catalog_items_synced": 142,
        "shipping_rules_updated": 850
      }
    },
    "meta": {
      "timestamp": "2026-06-16T15:16:35.000Z",
      "requestId": "req-job-check-2"
    }
  }
  ```

---

_Đặc tả API này đã được tối ưu hóa toàn diện theo các nguyên tắc thiết kế API hiện đại, sẵn sàng giao tiếp an toàn và mượt mà giữa Frontend Dashboard, Telegram Bot và FastAPI Backend._
