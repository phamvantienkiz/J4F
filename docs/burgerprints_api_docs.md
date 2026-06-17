# Tài liệu tích hợp API BurgerPrints cho ChatBot

Tài liệu này tổng hợp toàn bộ các API của BurgerPrints (bao gồm **BurgerPrints API v2** và **Public Catalog API v1**) đang được sử dụng trong codebase của hệ thống `BurgerPrintsAgent`. Tài liệu này cung cấp các endpoint, cấu trúc tham số, trường dữ liệu trả về, giải thích cách hoạt động và các lưu ý quan trọng về mặt logic & bảo mật phục vụ cho việc xây dựng ChatBot.

---

## 1. BurgerPrints API v2 (Quản lý Order, Balance & Product)

Nhóm API này yêu cầu xác thực thông qua Header sử dụng `api-key`.

*   **Base URL:** `https://api.burgerprints.com/v2`
*   **Headers bắt buộc:**
    ```http
    api-key: <YOUR_API_KEY>
    Accept: application/json
    User-Agent: BurgerPrintsAgent/0.1
    ```

### 1.1. Xem số dư tài khoản (Get Balance)
*   **Endpoint:** `GET /balance`
*   **Mục đích:** Kiểm tra kết nối API, lấy thông tin số dư tài khoản phục vụ seller thanh toán/fulfillment.
*   **Dữ liệu trả về (JSON):**
    ```json
    {
      "code": 200,
      "message": "success",
      "data": {
        "balance": 150.50,
        "currency": "USD"
      }
    }
    ```

### 1.2. Danh sách đơn hàng (List Orders)
*   **Endpoint:** `GET /order`
*   **Tham số truy vấn (Query Params):**
    *   `sandbox` (string, `"true"` hoặc `"false"`): Mặc định là `"true"` để truy cập môi trường thử nghiệm.
    *   `page_size` (number/string, giới hạn từ `1` đến `100`): Số lượng order trả về trên một trang.
*   **Dữ liệu trả về tiêu biểu:**
    ```json
    {
      "code": 200,
      "data": [
        {
          "id": "A30558-CT-5604773",
          "status": "pending",
          "amount": 25.50,
          "shipping_fee": 4.50,
          "created_date": "2026-06-01T12:00:00Z",
          "shipping": {
            "address": {
              "country": "US",
              "country_name": "United States"
            }
          },
          "items": [
            {
              "sku": "USG5000UL-Ash-XL",
              "catalog_sku": "USG5000UL-Ash-XL",
              "base_short_code": "USMG5000UL",
              "price": 6.75,
              "base_cost": 6.75,
              "shipping_fee": 1.00,
              "shipping_method": "standard",
              "size_name": "XL",
              "currency": "USD"
            }
          ]
        }
      ],
      "total": 120
    }
    ```

### 1.3. Chi tiết đơn hàng (Get Order Detail)
*   **Endpoint:** `GET /order/{order_id}`
*   **Lưu ý về cấu trúc trả về:** API trả về một đối tượng bọc có dạng `{code: 200, message: "...", data: {...}}`. Mã nguồn ChatBot bắt buộc phải đọc từ thuộc tính `data` để lấy thông tin đơn hàng thực tế.

### 1.4. Tạo đơn hàng (Create Order)
*   **Endpoint:** `POST /order`
*   **Mục đích:** Khởi tạo một đơn hàng mới lên hệ thống BurgerPrints. Hỗ trợ tạo đơn sandbox hoặc sản xuất, cũng như hỗ trợ thiết kế dạng Catalog SKU & Design URL hoặc sử dụng Shipping Label trực tiếp.
*   **Phân loại các trường Tự tạo/Quy chiếu và Tự động điền:**
    
    #### A. Các trường do Nhân viên/Seller Tự tạo hoặc Quy chiếu (Bắt buộc cung cấp):
    *   `reference_order_id` (string): **Mã tham chiếu đơn hàng**. Đây là mã định danh duy nhất do nhân viên/seller tự quy chiếu theo hệ thống quản lý nội bộ của mình (Ví dụ: `MYSTORE-1001`, `shopify_9981`) để đối soát với BurgerPrints.
    *   `design_url_front` (string) & `mockup_url_front` (string): **URL thiết kế và Mockup mặt trước**. *Lưu ý quan trọng:* Các trường này sẽ do **Frontend (FE) đảm nhiệm trước** bằng cách lấy trực tiếp URL ảnh từ trang web thiết kế/giao diện người dùng trên web client, ChatBot Backend chỉ nhận URL này trong Payload để truyền tiếp tới API BurgerPrints mà không cần tự tạo ra link.
    *   `shipping_name`, `shipping_address1`, `shipping_city`, `shipping_zip`, `shipping_country` (string): Thông tin địa chỉ giao hàng của khách mua.
    *   `shipping_state` (string): Bang/Tỉnh. Bắt buộc cung cấp nếu quốc gia giao hàng là Mỹ (`US`).

    #### B. Các trường Hệ thống Tự động điền hoặc Chọn mặc định (Có thể bỏ trống):
    *   `sandbox` (boolean): ChatBot/Client sẽ tự động điền hoặc ghi đè là `true` khi tạo đơn để bảo vệ môi trường sản xuất thật (gating protection).
    *   `quantity` (integer): Nếu không chỉ định, hệ thống mặc định điền là `1`.
    *   `shipping_method` (string): Nếu bỏ trống hoặc truyền sai, hệ thống tự động điền `"standard"` (hoặc phương thức rẻ nhất khả dụng).
    *   `production_service` & `additional_service` (string): Nếu không truyền, hệ thống tự động bỏ qua (không áp dụng dịch vụ ưu tiên hoặc ProActive Tracking).

*   **Cấu trúc Request Body chính thức:**
    *   `shipping_name` (string, bắt buộc): Tên người nhận hàng.
    *   `shipping_address1` (string, bắt buộc): Địa chỉ dòng 1 của khách hàng.
    *   `shipping_address2` (string, tùy chọn): Địa chỉ dòng 2 của khách hàng.
    *   `shipping_city` (string, bắt buộc): Thành phố.
    *   `shipping_state` (string, tùy chọn): Bang/Tỉnh. Bắt buộc đối với địa chỉ Mỹ (US).
    *   `shipping_zip` (string, bắt buộc): Mã zip/postal code của khách hàng.
    *   `shipping_country` (string, bắt buộc): Mã quốc gia (định dạng ISO 3166-1 alpha-2, ví dụ: `US`, `VN`).
    *   `shipping_email` (string, tùy chọn): Địa chỉ email khách hàng.
    *   `shipping_phone` (string, tùy chọn): Số điện thoại khách hàng.
    *   `reference_order_id` (string, bắt buộc): Mã order tham chiếu để đối soát đơn hàng nội bộ (Unique ID).
    *   `shipping_label` (string, tùy chọn): URL dẫn tới file PDF nhãn vận chuyển (Nếu đơn hàng có sẵn nhãn vận chuyển).
    *   `shipping_tracking_number` (string, tùy chọn): Mã tracking của nhãn vận chuyển đi kèm.
    *   `production_service` (string, tùy chọn): Dịch vụ sản xuất, ví dụ: `"Priority"`.
    *   `shipping_method` (string, tùy chọn): Phương thức vận chuyển (`economy`, `standard`, `express`, `priority express`). Nếu bỏ trống hoặc sai giá trị, hệ thống mặc định chọn `standard`.
    *   `additional_service` (string, tùy chọn): Dịch vụ đi kèm, ví dụ: `"ProActive Tracking"`.
    *   `callback_url` (string, tùy chọn): URL Webhook nhận thông báo cập nhật trạng thái đơn hàng (ví dụ: khi có mã tracking).
    *   `sandbox` (boolean, bắt buộc): Thiết lập `true` nếu muốn đặt đơn hàng ở chế độ Sandbox (thử nghiệm), thiết lập `false` nếu muốn đặt đơn hàng thật.
    *   `fulfillment_partner` (string, tùy chọn): Tên nền tảng (Platform name).
    *   `items` (array, bắt buộc): Danh sách sản phẩm trong đơn hàng.
        *   **Cách 1: Đặt hàng qua Catalog SKU & Design URL**
            *   `catalog_sku` (string, bắt buộc): Mã SKU của biến thể từ Catalog.
            *   `design_url_front` (string, bắt buộc/tùy chọn): URL thiết kế mặt trước.
            *   `mockup_url_front` (string, tùy chọn): URL ảnh mockup mặt trước.
            *   `design_url_back` (string, bắt buộc/tùy chọn): URL thiết kế mặt sau.
            *   `mockup_url_back` (string, tùy chọn): URL ảnh mockup mặt sau.
            *   *Lưu ý:* Bắt buộc phải có thiết kế (`design_url_*`) cho ít nhất một vùng in. Có thể có thêm các vùng in khác như `design_right_sleeve`, `design_left_sleeve`, `design_front_oversize`, `design_back_oversize`, `design_neck`, `design_pouch_pocket`, `design_hood`.
            *   `reference_item_id` (string, tùy chọn): ID sản phẩm tham chiếu nội bộ.
            *   `quantity` (integer, bắt buộc): Số lượng sản phẩm.
        *   **Cách 2: Đặt hàng qua Product ID & Variant ID**
            *   `product_id` (string, bắt buộc): ID của sản phẩm trong Campaign.
            *   `variant_id` (string, bắt buộc): ID của biến thể sản phẩm.
            *   `quantity` (integer, bắt buộc): Số lượng sản phẩm.

*   **Dữ liệu yêu cầu mẫu (cURL):**
    ```bash
    curl --location 'https://api.burgerprints.com/v2/order' \
    --header 'api-key: YOUR_API_KEY' \
    --header 'Content-Type: application/json' \
    --data '{
      "shipping_name": "james bond",
      "shipping_address1": "1598 Junior Avenue",
      "shipping_address2": "Homer",
      "shipping_city": "Atlanta",
      "shipping_state": "AZ",
      "shipping_zip": "30318",
      "shipping_country": "US",
      "shipping_email": "abc@gmail.com",
      "shipping_phone": "34",
      "reference_order_id": "2343435456vege",
      "shipping_label": "https://d1ud88wu9m1k4s.cloudfront.net/platform_labels/2024/03/09/A33602_v4SXpdI2cKmN129ezd5NYvJIu_1709998925551.pdf",
      "items": [
        {
          "catalog_sku": "USG5000-Red-S",
          "design_url_front": "https://d1ud88wu9m1k4s.cloudfront.net/isp/2021/03/04/A2075_store_b7vinpbi8brtf.jpg",
          "mockup_url_front": "https://d1ud88wu9m1k4s.cloudfront.net/isp/2021/03/04/A2075_store_b7vinpbi8brtf.jpg",
          "design_url_back": "https://d1ud88wu9m1k4s.cloudfront.net/isp/2021/03/04/A2075_store_b7vinpbi8brtf.jpg",
          "mockup_url_back": "https://d1ud88wu9m1k4s.cloudfront.net/isp/2021/03/04/A2075_store_b7vinpbi8brtf.jpg",
          "quantity": 3
        }
      ],
      "sandbox": true
    }'
    ```

*   **Dữ liệu trả về (JSON):**
    ```json
    {
      "is_success": true,
      "message": "Order created successfully",
      "order_id": "12345",
      "errors": []
    }
    ```
*   **Lưu ý quan trọng cho ChatBot:** 
    1. ChatBot phải luôn buộc trường `sandbox` bằng `true` khi gọi API (client code tự động ghi đè `"sandbox": True` để bảo vệ an toàn, tránh tạo đơn sản xuất thật ngoài ý muốn).
    2. Cần phân loại rõ 2 hình thức đặt hàng của seller: Đặt hàng sử dụng **Catalog SKU + Links thiết kế** (Phổ biến) hoặc Đặt hàng qua **Campaign/Product ID + Variant ID**. Nếu đơn hàng sử dụng Shipping Label tự cấp, bắt buộc truyền URL nhãn vào `shipping_label`.

### 1.5. Danh sách sản phẩm (List Products)
*   **Endpoint:** `GET /product`
*   **Tham số truy vấn (Query Params):**
    *   `page` (mặc định: `1`)
    *   `page_size` (giới hạn từ `1` đến `200`)
*   **Mục đích:** Lấy danh sách sản phẩm cơ bản (base products) và ánh xạ mã sản phẩm (`short_code`).

### 1.6. Chi tiết sản phẩm (Get Product Detail)
*   **Endpoint:** `GET /product/{short_code}`
*   **Mục đích:** Lấy thông tin chi tiết của một dòng sản phẩm theo mã ngắn, bao gồm các biến thể (variants), kích thước (size), màu sắc (color), giá vốn (base cost/price), chi phí in mặt thứ 2 (`2nd_price`), chi phí thêm khu vực in (`addition_price`), xưởng sản xuất (`partner_name`) và ID xưởng (`partner_id`).

### 1.7. Danh sách sản phẩm hết hàng (Out of Stock)
*   **Endpoint:** `GET /product/outofstock`
*   **Mục đích:** Liệt kê các SKU đang tạm thời hết hàng để ChatBot chủ động lọc bỏ hoặc cảnh báo người dùng trong quá trình xếp hạng/khuyến nghị SKU.

---

## 2. Public Catalog API v1 (Tra cứu Catalog & Vận chuyển toàn cầu)

Nhóm API này dùng để tra cứu thông tin SKU, so sánh giá vốn giữa các nhà cung cấp (suppliers), tính toán phí ship và thời gian giao hàng (delivery time/SLA). API này không bắt buộc Token bảo mật cá nhân của người dùng, sử dụng khóa chung hoặc truy cập công khai.

*   **Base URL:** `https://catalog-api.burgerprints.com/api/v1`
*   **Headers khuyến nghị:**
    ```http
    api-key: burgerprints
    Accept: application/json
    ```

### 2.1. Danh sách Catalog (Catalog List)
*   **Endpoint:** `GET /catalogsV2/list`
*   **Mục đích:** Lấy toàn bộ danh sách sản phẩm catalog phân nhóm theo: `baseNews` (Mới), `baseBestSellers` (Bán chạy) và `baseSuggest` (Gợi ý).
*   **Dữ liệu trả về:** Chứa các thuộc tính chính như `shortCode`, `name`, `displayName`, `aliasName` (dùng để tra cứu chi tiết), `dropshipPriceMin`, `dropshipPriceMax`, và danh sách các xưởng hỗ trợ (`locations`).

### 2.2. Chi tiết Catalog theo Alias (Product Detail by Alias)
*   **Endpoint:** `GET /catalogsV2/alias/{aliasName}`
*   **Mục đích:** Lấy thông tin giàu dữ liệu hơn API v2, bao gồm danh sách SKU đầy đủ (`baseSku[]`) đi kèm giá vốn (`baseCost`), xưởng sản xuất tương ứng (`location`), chi phí in mặt 2 (`secondSidePrice`), và phí ship cơ bản tới US hoặc Toàn cầu (WW).
*   **Trường dữ liệu quan trọng:**
    *   `baseSku[].sku`: Mã SKU đầy đủ của biến thể.
    *   `baseSku[].location`: ID của xưởng sản xuất (Fulfillment Location ID).
    *   `baseSku[].locationName`: Tên xưởng sản xuất.
    *   `baseSku[].shippingCostUs`: Phí ship item đầu tiên tới Mỹ (US).
    *   `baseSku[].shippingAddingUs`: Phí ship mỗi item tiếp theo tới Mỹ (US) trong cùng một đơn hàng.
    *   `baseSku[].shippingCostWW`: Phí ship item đầu tiên tới các quốc gia khác ngoài Mỹ (WW).
    *   `baseSku[].shippingAddingWW`: Phí ship mỗi item tiếp theo tới các quốc gia khác ngoài Mỹ (WW).

### 2.3. Danh sách quốc gia & Phí ship chi tiết (Shipping Destinations)
*   **Endpoint:** `GET /catalogsV2/locations?shortCode={SHORT_CODE}&partnerId={LOCATION_ID}`
*   **Mục đích:** Đây là API cực kỳ quan trọng để tra cứu thời gian giao hàng và biểu phí vận chuyển chi tiết cho một sản phẩm cụ thể tại một xưởng sản xuất đến tất cả các quốc gia trên thế giới.
*   **Dữ liệu trả về mẫu:**
    ```json
    {
      "code": 200,
      "message": "success",
      "data": [
        {
          "countryCode": "VN",
          "countryName": "Vietnam",
          "details": [
            {
              "method": "standard",
              "name": "Standard",
              "description": "15-20 business days",
              "carriers": "DHL",
              "firstItemPrice": "0.5",
              "additionalItemPrice": "0"
            }
          ]
        }
      ]
    }
    ```
*   **Ánh xạ biến trong ChatBot:**
    *   `countryCode`: Mã quốc gia (ví dụ: `US`, `VN`, `CA`).
    *   `details[].name`: Tên dịch vụ ship (ví dụ: `Standard`).
    *   `details[].description`: Thời gian giao hàng ước tính (ví dụ: `15-20 business days`).
    *   `details[].carriers`: Đơn vị vận chuyển (ví dụ: `DHL`, `USPS`).
    *   `details[].firstItemPrice`: Phí ship cho sản phẩm đầu tiên.
    *   `details[].additionalItemPrice`: Phí ship cho sản phẩm tiếp theo.

### 2.4. Thời gian xử lý của nhà cung cấp (Supplier SLA)
*   **Endpoint:** `GET /catalogsV2/location-sla?partnerId={LOCATION_ID}`
*   **Mục đích:** Lấy thời gian xử lý sản xuất (`processingTime`) và điểm SLA (`sla`) của xưởng. Giúp ChatBot so sánh và gợi ý xưởng có tốc độ sản xuất nhanh nhất khi có nhiều xưởng cùng cung cấp một SKU.

### 2.5. Danh sách tất cả các xưởng (Fulfillment Location List)
*   **Endpoint:** `GET /catalogsV2/locations/list`
*   **Mục đích:** Lấy thông tin danh sách đầy đủ tất cả các trung tâm hoàn thiện đơn hàng (Fulfillment Centers) của BurgerPrints trên toàn thế giới để lập chỉ mục hoặc hiển thị thông tin giới thiệu.

---

## 3. Các quy tắc quan trọng khi làm việc với ChatBot

Hệ thống ChatBot cần tuân thủ nghiêm ngặt các quy tắc an toàn dữ liệu, thiết lập môi trường và luồng xử lý sau:

### 3.1. Bảo vệ dữ liệu cá nhân (PII Protection)
*   Tuyệt đối **KHÔNG** hiển thị thông tin nhận dạng cá nhân (PII) của khách hàng như Tên, Địa chỉ chi tiết, Email hoặc Số điện thoại trong câu trả lời của ChatBot hoặc lưu trữ trong log hệ thống.
*   Thông tin nhạy cảm phải được che mặt trước khi hiển thị cho người dùng (ví dụ: `shipping_zip` chỉ hiển thị 2 ký tự đầu kèm ký tự che: `94***`, tên hiển thị `J*** D***`).

### 3.2. Rào chắn tạo đơn hàng (Order Creation Gating)
*   **Chế độ Sandbox:** Chỉ cho phép ChatBot gọi API tạo đơn hàng khi cấu hình môi trường `.env` có thiết lập:
    ```env
    BURGERPRINTS_ENABLE_SANDBOX_CREATE_ORDER=true
    ```
*   **Xác nhận 2 lớp (Double Confirmation):** Nếu người dùng yêu cầu tạo đơn hàng, ChatBot phải chuyển sang trạng thái thu thập thông tin bản thảo (Draft). ChatBot **KHÔNG ĐƯỢC** kích hoạt tạo đơn hàng khi nhận được câu trả lời ngắn hoặc mơ hồ từ người dùng (như *"ok"*, *"yes"*, *"đồng ý"*).
*   Đơn hàng chỉ được gửi lên API sau khi người dùng nhập chính xác một trong các chuỗi xác nhận bắt buộc sau:
    *   `"confirm create sandbox order"`
    *   `"xác nhận tạo sandbox order"`

### 3.3. Yêu cầu làm rõ Quốc gia đích (Country Clarification)
*   Khi người dùng thực hiện tra cứu, so sánh hoặc xếp hạng phí ship, thời gian giao hàng hoặc gợi ý xưởng/SKU:
    *   Nếu trong câu lệnh **thiếu thông tin quốc gia giao hàng**, ChatBot **KHÔNG ĐƯỢC tự động mặc định chọn US**.
    *   ChatBot phải phản hồi yêu cầu người dùng làm rõ: *"Bạn muốn ship/fulfill tới nước nào? Ví dụ: US, CA, UK, AU, VN."*

### 3.4. Logic tìm kiếm thay thế (Nearest Alternative Mode)
*   Khi người dùng áp dụng bộ lọc (ví dụ: *"giá vốn dưới $8"*, *"giao hàng dưới 5 ngày"*):
    *   Nếu không tìm thấy SKU nào đáp ứng hoàn toàn điều kiện, ChatBot **KHÔNG ĐƯỢC trả về danh sách rỗng**.
    *   Hệ thống phải chuyển sang chế độ **"lựa chọn thay thế gần nhất" (nearest alternative mode)**, đánh dấu thuộc tính `filter_match = "nearest_alternative"` trong kết quả trả về, giải thích rõ các giới hạn bị vượt và hiển thị các SKU gần đạt yêu cầu nhất để seller tham khảo.

### 3.5. Công thức tính toán chi phí (Cost Calculation Formulas)
*   **Phí ship đơn hàng:**
    $$\text{shipping\_fee} = \text{first\_item\_shipping} + (\text{quantity} - 1) \times \text{additional\_item\_shipping}$$
*   **Tổng chi phí fulfillment cơ bản:**
    $$\text{total\_cost} = (\text{base\_cost} \times \text{quantity}) + \text{shipping\_fee}$$
*   **Ước tính lợi nhuận (Profit Margin):**
    $$\text{profit\_margin} = (\text{selling\_price} \times \text{quantity}) - \text{total\_cost}$$
    *Lưu ý:* Nếu người dùng yêu cầu sắp xếp SKU theo lợi nhuận (`sort_by = "profit"`) nhưng chưa cung cấp giá bán lẻ (`selling_price`), ChatBot phải thông báo cho người dùng biết hệ thống sẽ tạm thời xếp hạng theo tổng chi phí fulfillment thấp nhất cho đến khi giá bán lẻ được cung cấp.
