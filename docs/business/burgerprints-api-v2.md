# BurgerPrints API v2.0 - Core Documentation

## 1. Authentication

- **Protocol:** HTTPS
- **Headers:**
  - `api-key`: `[YOUR_API_KEY]`
  - `Content-Type`: `application/json`

---

## 2. Product API (Sản phẩm & Xưởng in)

### **GET** Get all bases

- **Endpoint:** `https://api.burgerprints.com/v2/product`
- **Description:** Lấy danh sách các sản phẩm/phôi (base).
- **Request Params:**
  - `page` (string, optional): Số trang hiển thị. Mặc định 1.
  - `page_size` (string, optional): Số lượng item trên một trang.

### **GET** Get a base

- **Endpoint:** `https://api.burgerprints.com/v2/product/{id}`
- **Description:** Lấy chi tiết thông tin của một sản phẩm, bao gồm các biến thể (variations), size, màu sắc, giá base, và tên xưởng in (partner_name).
- **Path Params:**
  - `{id}` (string, required): Mã `short_code` của sản phẩm (VD: USG5000).

### **GET** Out of stock

- **Endpoint:** `https://api.burgerprints.com/v2/product/outofstock`
- **Description:** Lấy danh sách các sản phẩm đang hết hàng (out-of-stock).
- **Request Params:** Không có.

---

## 3. Orders API (Đơn hàng)

### **GET** Get all orders

- **Endpoint:** `https://api.burgerprints.com/v2/order`
- **Description:** Lấy thông tin tất cả đơn hàng.
- **Request Params:**
  - `sandbox` (boolean, required): Set là true để lấy đơn nháp/test.
  - `reference` (string, optional): Lọc theo mã reference.
  - `store_id` (string, optional): Lọc theo store_id.
  - `state` (string, optional): Lọc theo trạng thái.
  - `start_date` (timestamp, optional): Ngày bắt đầu.
  - `end_date` (timestamp, optional): Ngày kết thúc.
  - `page` (string, optional): Số trang hiển thị. Mặc định 1.
  - `page_size` (string, optional): Số item tối đa một trang. Mặc định 50, tối đa 500.

### **GET** Get a single order

- **Endpoint:** `https://api.burgerprints.com/v2/order/{id}`
- **Description:** Lấy chi tiết thông tin của một đơn hàng.

* Retrieves information about a specific order.
* We also note the order status and fulfillment status as shown in the table below.
  | Order Status | Fulfillment Status | Description |
  | ------------ | ------------------ | ------------------------------------------------------------------------------------ |
  | draft | Unfulfilled | User needs to provide additional information before payment. |
  | queued | Unfulfilled | Seller can choose to pay for all orders at once or pay for each order individually. |
  | place | Unfulfilled | Orders that have been successfully paid. |
  | processed | Scheduled | Orders that are currently being produced. |
  | shipped | Fulfilled | Orders that have been shipped. |
  | refunded | Unfulfilled | Production is stopped; contact support for assistance. There may be a fee or no fee. |

- **Path Params:**
  - `{id}` (string, required): Mã ID của đơn hàng.

### **GET** Get tracking order

- **Endpoint:** `https://api.burgerprints.com/v2/order/{id}/tracking`
- **Description:** Lấy mã vận đơn (tracking number) và thông tin vận chuyển của một đơn hàng.
- **Path Params:**
  - `{id}` (string, required): Mã ID của đơn hàng.

### **POST** Create order

- **Endpoint:** `https://api.burgerprints.com/v2/order`
- **Description:** Tạo một đơn hàng fulfillment mới.
- **Request Body Parameters:**
  - `store_id` (string): ID của cửa hàng.
  - `shipping_method` (string): Phương thức vận chuyển (VD: standard).
  - `callback_url` (string, optional): URL để nhận webhook.
  - `shipping` (object): Chứa thông tin người nhận gồm `name`, `email`, `phone`, và `address` (`line1`, `city`, `state`, `postal_code`, `country`).
  - `items` (array): Chứa danh sách sản phẩm gồm `catalog_sku`, `quantity`, `design_front_url`, `design_back_url`...

### **POST** Charge order

- **Endpoint:** `https://api.burgerprints.com/v2/order/charge`
- **Description:** Thanh toán cho các đơn hàng đã tạo.
- **Request Body Parameters:**
  - `order_ids` (array of strings, required): Danh sách các ID đơn hàng cần thanh toán.
- **Response Details:**
  - Trả về `state` (purchased / fail / pending), `message`, và `details`.

### **DELETE** Delete order

- **Endpoint:** `https://api.burgerprints.com/v2/order/{id}`
- **Description:** Xóa một đơn hàng. (Lưu ý: Chỉ gọi được khi đơn hàng đang ở trạng thái chưa thanh toán - unpaid).
- **Path Params:**
  - `{id}` (string, required): ID của đơn hàng cần xóa.

### **PUT** Cancel order

- **Endpoint:** `https://api.burgerprints.com/v2/order/{id}/cancel`
- **Description:** Hủy một đơn hàng.
- **Path Params:**
  - `{id}` (string, required): ID của đơn hàng cần hủy.

---

## 4. Balance API (Số dư tài khoản)

### **GET** Get balance

- **Endpoint:** `https://api.burgerprints.com/v2/balance`
- **Description:** Kiểm tra số dư tài khoản, chi phí đã thanh toán và chi phí pending.
- **Request Params:** Không có.

---

## 5. Webhook API (Thông báo)

### **POST** Add webhook

- **Endpoint:** `https://api.burgerprints.com/notification/api/v1/public/fulfillment/notify/webhook`
- **Description:** Đăng ký nhận thông báo trạng thái đơn hàng.
- **Request Body Parameters:**
  - `end_point_url` (string, required): URL của server bạn để nhận thông báo.
  - `is_active` (boolean, required): Trạng thái kích hoạt (true/false).

### **POST** Webhook Callback

- **Description:** Payload hệ thống BurgerPrints tự động bắn về `callback_url` khi đơn hàng có cập nhật.
- **Body Parameters (Nhận được):**
  - Danh sách các đơn hàng chứa `order_id`, `reference_order_id`, `carrier` (hãng vận chuyển), `code` (mã tracking), và `url` (link tra cứu vận đơn).
