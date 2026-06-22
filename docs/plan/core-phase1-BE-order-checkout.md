# Kế hoạch triển khai: Order & Sandbox Checkout Service (BE - Giai đoạn 1)

## 1. Liên kết Yêu cầu & Tài liệu tham chiếu
- **User Story liên quan:**
  - [US-003: Đặt Đơn Sandbox Qua Order HUD](file:///E:/MyProject/BurgerAgent/docs/product/burgeragent-core-prd.md#L135-L157)
  - [US-004: Theo Dõi Trạng Thái Lịch Sử Đơn Hàng](file:///E:/MyProject/BurgerAgent/docs/product/burgeragent-core-prd.md#L159-L176)
- **Functional Requirements:**
  - [F-5: Giao Dịch Đặt Đơn Sandbox - SKU, thông tin nhận hàng](file:///E:/MyProject/BurgerAgent/docs/product/burgeragent-core-prd.md#L223-L230)
- **Technical Constraints & Architecture:**
  - [Quy trình Đặt Hàng Đa Kênh Sequence Diagram](file:///E:/MyProject/BurgerAgent/docs/product/burgeragent-core-architecture.md#L329-L355)
  - [Chọn CP (Strong Consistency) cho Đơn Hàng](file:///E:/MyProject/BurgerAgent/docs/product/burgeragent-core-architecture.md#L432-L437)
  - [Tài liệu BurgerPrints API v2.0 - Orders API](file:///E:/MyProject/BurgerAgent/docs/business/burgerprints-api-v2.md#L37-L112)
  - [Nhóm Đơn Hàng & Webhook API](file:///E:/MyProject/BurgerAgent/docs/product/burgeragent-core-api.md#L71-L76)
  - [Đặc Tả Chi Tiết Orders API (/v1/orders)](file:///E:/MyProject/BurgerAgent/docs/product/burgeragent-core-api.md#L179-L253)
- **QA/QC Test Cases:**
  - [TC-010: Validation thông tin nhận hàng](file:///E:/MyProject/BurgerAgent/docs/product/burgeragent-core-qa-qc.md#L87-L89)
  - [TC-011: Đặt đơn hàng Sandbox thành công](file:///E:/MyProject/BurgerAgent/docs/product/burgeragent-core-qa-qc.md#L90)
  - [TC-012: Đặt đơn Sandbox không trừ ví](file:///E:/MyProject/BurgerAgent/docs/product/burgeragent-core-qa-qc.md#L91)

---

## 2. Đặc tả Kỹ thuật
- **Nguyên tắc giao dịch:** Nhất quán mạnh (Strong Consistency). Khi client nhấn đặt hàng, Backend bắt buộc phải đợi phản hồi thành công từ API đối tác BurgerPrints rồi mới lưu trạng thái và phản hồi cho client.
- **Ràng buộc Ví Sandbox:** API Sandbox BurgerPrints cho phép tạo đơn thành công vô điều kiện ngay cả khi số dư tài khoản của Seller bằng `$0.00`.
- **Thiết kế API Patterns:**
  - **Pattern 2 - Pagination:** Phân trang kết quả lịch sử bằng tham số `page` và `limit`.
  - **Pattern 3 - Filtering:** Hỗ trợ lọc danh sách đơn hàng theo `status`.
  - **Pattern 4 - Field Selection:** Hỗ trợ lọc các trường trả về thông qua tham số `fields`.
  - **Pattern 5 - Expansion:** Mở rộng thông tin bằng `?expand=tracking` để backend tự gọi API BurgerPrints lấy thông tin hành trình vận chuyển thời gian thực của hãng vận chuyển.

---

## 3. Kế hoạch Triển khai (Mã nguồn & Cấu trúc)
1. **Định nghĩa Schemas Dữ liệu & Validation:**
   - Tạo các Pydantic Models cho request body của đơn hàng (thông tin người nhận: `name`, `line1`, `city`, `state`, `postal_code`, `country`, và danh sách các sản phẩm: `sku`, `quantity`, `design_front_url`, `design_back_url`).
   - Viết các rule validate đầu vào: Họ tên, Address Line 1, City, và Zip Code không được để trống.
2. **Xây dựng Order Service & Kết nối BurgerPrints API:**
   - Triển khai trong [backend/app/services/order_service.py](file:///E:/MyProject/BurgerAgent/docs/product/burgeragent-backend-ai-structure.md#L81).
   - Thiết lập header có `api-key` lấy từ file `.env`.
   - Kết nối endpoint sandbox `POST https://api.burgerprints.com/v2/order` gửi payload đơn hàng.
   - Nhận về phản hồi chứa ID đơn hàng của BurgerPrints (`bp_order_id`) và mã vận đơn mặc định.
3. **Phát triển Order Endpoints (Tạo, Xem Lịch sử, Chi tiết):**
   - Tạo file [backend/app/api/v1/endpoints/orders.py](file:///E:/MyProject/BurgerAgent/docs/product/burgeragent-backend-ai-structure.md#L53).
   - Triển khai `POST /v1/orders`: Xác thực người dùng, gọi validate địa chỉ, gọi `OrderService` đặt đơn sandbox, nhận response và ghi nhận trạng thái vào SQLite qua `OrderRepository`, trả về thông tin thành công.
   - Triển khai `GET /v1/orders`: Truy vấn danh sách đơn hàng từ SQLite, áp dụng logic phân trang, lọc theo trạng thái và lọc thuộc tính trả về theo `fields`.
   - Triển khai `GET /v1/orders/{id}`: Lấy chi tiết đơn hàng từ SQLite. Nếu URL chứa `?expand=tracking`, gọi tiếp API `GET https://api.burgerprints.com/v2/order/{id}/tracking` lấy thông tin vận đơn trực tiếp (carrier, tracking_code, url, estimated_delivery, last_checkpoint) và lồng vào trường `tracking` của response.
4. **Xây dựng Webhook Endpoint nhận cập nhật từ BurgerPrints:**
   - Tạo file [backend/app/api/v1/endpoints/webhook.py](file:///E:/MyProject/BurgerAgent/docs/product/burgeragent-backend-ai-structure.md#L54).
   - Triển khai `POST /v1/orders/webhook` tiếp nhận callback thông báo trạng thái thay đổi (`shipped`, `processed`...) từ BurgerPrints.
   - Cập nhật trường `status` và `tracking_number` tương ứng trong bảng `orders` của SQLite.

---

## 4. Kịch bản Kiểm thử & QA/QC (Không Mock Data)
- **TC-ORDER-001: Validate thông tin địa chỉ giao nhận**
  - **Mục tiêu:** Trả về lỗi khi thiếu thông tin giao hàng bắt buộc.
  - **Cách test:** Gọi API `POST /v1/orders` với body thiếu trường `"postal_code"` hoặc để trống `"line1"`. API phải chặn lại và trả về lỗi `400 Bad Request` dạng Error Envelope với thông báo lỗi rõ ràng.
- **TC-ORDER-002: Đặt đơn Sandbox thành công trên Ví $0.00**
  - **Mục tiêu:** Kiểm tra khả năng tạo đơn sandbox không trừ ví.
  - **Cách test:** Đăng nhập tài khoản seller có số dư $0.00. Gọi API `POST /v1/orders` với thông tin địa chỉ hợp lệ và SKU phôi. Response phải trả về mã `200/201` thành công chứa ID đơn hàng và trạng thái đơn ban đầu là `"queued"`.
- **TC-ORDER-003: Lấy lịch sử và lọc dữ liệu (Filter, Pagination, Field Selection)**
  - **Mục tiêu:** Trả về danh sách đơn hàng phân trang và có chọn lọc trường.
  - **Cách test:** Gọi API `/v1/orders?page=1&limit=5&status=queued&fields=order_id,status` -> Response phải trả về danh sách tối đa 5 đơn hàng có trạng thái `"queued"` và mỗi đơn hàng chỉ chứa duy nhất hai thuộc tính `order_id` và `status`.
- **TC-ORDER-004: Mở rộng dữ liệu Tracking (Expansion)**
  - **Mục tiêu:** Kéo thông tin vận đơn thời gian thực từ API đối tác khi yêu cầu expand.
  - **Cách test:** Gọi API `/v1/orders/BP-ORDER-9912?expand=tracking` -> Response trả về phải chứa đầy đủ trường thông tin vận chuyển `tracking` (carrier, tracking_code...) được kéo về từ API BurgerPrints.
