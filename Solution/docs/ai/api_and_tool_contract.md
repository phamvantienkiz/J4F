# API & TOOL CONTRACT: BURGERPRINTS AGENT

Tài liệu này xác lập "hợp đồng" (contract) giao tiếp giữa các thành phần phần mềm của hệ thống **BurgerPrints Agent**. Tài liệu bao gồm đặc tả API v2.0 của hệ thống BurgerPrints (dùng để tích hợp ngoài) và đặc tả giao diện lập trình của bộ Tool Layer dành cho LangGraph Agent (dùng để phát triển trong).

Tài liệu này được thiết kế thống nhất và liên kết chặt chẽ với [Solution Overview](file:///E:/Hackathon2026/J4F/Solution/docs/ai/solution_overview.md), [System Architecture](file:///E:/Hackathon2026/J4F/Solution/docs/ai/system_architecture.md), và [Agent Design Specification](file:///E:/Hackathon2026/J4F/Solution/docs/ai/agent_design_specification.md).

---

## 1. BurgerPrints API v2.0 Contract (External Integration)

Hệ thống tích hợp trực tiếp với cổng API v2.0 của BurgerPrints. Toàn bộ các yêu cầu RESTful được gửi qua giao thức HTTPS.

*   **Base URL:** `https://api.burgerprints.com/v2` (Môi trường Sandbox/Production)
*   **Authentication:** Sử dụng khóa API Key cá nhân được cung cấp trong phần cài đặt của Store. Khóa này được truyền trực tiếp dưới dạng query parameter `apiKey` trong URL của mọi request.
    *   *Ví dụ:* `https://api.burgerprints.com/v2/orders?apiKey=bp_sec_key_abc123`

### 1.1. API Tạo Đơn Hàng (Create Order)
*   **Endpoint:** `POST /orders`
*   **Mô tả:** Đẩy thông tin đơn hàng nháp hoặc đơn hàng thật lên hệ thống BurgerPrints để tiến hành in ấn và vận chuyển.
*   **Headers:**
    *   `Content-Type: application/json`
*   **Request Body (JSON):**
    ```json
    {
      "order_reference_id": "ORDER_RE_9988",
      "shipping_address": {
        "full_name": "David Miller",
        "address_line1": "742 Evergreen Terrace",
        "address_line2": "Apt 4B",
        "city": "Springfield",
        "state": "IL",
        "zip_code": "62704",
        "country_code": "US",
        "phone": "+12175550143"
      },
      "items": [
        {
          "sku": "BP-UNISEX-TSHIRT-BLK-L",
          "quantity": 2,
          "design_front_url": "https://assets.my-store.com/designs/tshirt_front_vintage.png",
          "design_back_url": "https://assets.my-store.com/designs/tshirt_back_logo.png",
          "mockup_front_url": "https://assets.my-store.com/mockups/tshirt_black_front.jpg",
          "mockup_back_url": "https://assets.my-store.com/mockups/tshirt_black_back.jpg",
          "selected_factory_id": "factory_us_chicago_01"
        }
      ]
    }
    ```
*   **Response Body - HTTP 201 Created:**
    ```json
    {
      "success": true,
      "order_id": "bp_ord_88776655",
      "order_reference_id": "ORDER_RE_9988",
      "status": "pending",
      "financial_summary": {
        "currency": "USD",
        "subtotal": 11.00,
        "printing_fee": 4.00,
        "shipping_fee": 8.40,
        "tax": 0.95,
        "total_cogs": 24.35
      },
      "created_at": "2026-06-06T08:00:00Z"
    }
    ```

### 1.2. API Lấy Chi Tiết Đơn Hàng (Get Single Order)
*   **Endpoint:** `GET /orders/{order_id}`
*   **Mô tả:** Tra cứu thông tin chi tiết và tiến độ xử lý/vận đơn của một đơn hàng.
*   **Response Body - HTTP 200 OK:**
    ```json
    {
      "order_id": "bp_ord_88776655",
      "status": "in_production",
      "shipping_address": {
        "full_name": "David Miller",
        "city": "Springfield",
        "country_code": "US"
      },
      "fulfillment": {
        "factory_id": "factory_us_chicago_01",
        "factory_name": "Chicago Print Corp"
      },
      "tracking": {
        "carrier": "USPS",
        "tracking_number": "9400100000000000000000",
        "tracking_url": "https://tools.usps.com/go/TrackConfirmAction?tLabels=9400100000000000000000",
        "estimated_delivery": "2026-06-12T18:00:00Z"
      },
      "updated_at": "2026-06-06T10:15:30Z"
    }
    ```

### 1.3. API Hủy Đơn Hàng (Cancel Order)
*   **Endpoint:** `POST /orders/{order_id}/cancel`
*   **Mô tả:** Yêu cầu hủy đơn hàng. Việc hủy đơn chỉ thành công khi trạng thái đơn hàng chưa chuyển sang giai đoạn in ấn (`in_production`).
*   **Response Body - HTTP 200 OK:**
    ```json
    {
      "success": true,
      "order_id": "bp_ord_88776655",
      "status": "cancelled",
      "refund_amount": 24.35,
      "cancelled_at": "2026-06-06T10:20:00Z"
    }
    ```

### 1.4. API Tra Cứu Catalog & Báo Giá (Catalog API Contract)
Đây là các API mở rộng của BurgerPrints để hỗ trợ các ứng dụng trợ lý (Agent) tìm kiếm thông tin nhanh:

#### A. Tìm kiếm sản phẩm
*   **Endpoint:** `GET /catalog/products`
*   **Query Params:** `query` (từ khóa tìm kiếm), `category` (Apparel, Mug, Canvas...)
*   **Response Body - HTTP 200 OK:**
    ```json
    {
      "products": [
        {
          "product_id": "bp_prod_tshirt_01",
          "name": "Classic Unisex T-Shirt",
          "category": "Apparel",
          "sizes": ["S", "M", "L", "XL", "2XL"],
          "colors": ["Black", "White", "Navy", "Red"],
          "base_price": 5.50
        }
      ]
    }
    ```

#### B. Lấy báo giá xưởng in (Quotes)
*   **Endpoint:** `GET /catalog/products/{product_id}/quotes`
*   **Query Params:** `market` (quốc gia đích, ví dụ: `US`, `EU` để lọc xưởng gần nhất)
*   **Response Body - HTTP 200 OK:**
    ```json
    {
      "product_id": "bp_prod_tshirt_01",
      "factory_quotes": [
        {
          "factory_id": "factory_us_chicago_01",
          "factory_name": "Chicago Print Corp",
          "location": "IL, US",
          "base_cost": 5.50,
          "printing_cost": 2.00,
          "available_colors": ["Black", "White"],
          "production_time_days": 2
        },
        {
          "factory_id": "factory_vn_hanoi_02",
          "factory_name": "Hanoi Garment & Print",
          "location": "Hanoi, VN",
          "base_cost": 4.10,
          "printing_cost": 1.50,
          "available_colors": ["Black", "White", "Navy", "Red"],
          "production_time_days": 3
        }
      ]
    }
    ```

#### C. Ước tính chi phí và thời gian vận chuyển (Estimate Shipping)
*   **Endpoint:** `POST /shipping/estimate`
*   **Request Body (JSON):**
    ```json
    {
      "origin_factory_id": "factory_us_chicago_01",
      "destination_country": "US",
      "zip_code": "62704"
    }
    ```
*   **Response Body - HTTP 200 OK:**
    ```json
    {
      "shipping_options": [
        {
          "carrier": "USPS Standard",
          "shipping_cost": 4.20,
          "delivery_days_min": 3,
          "delivery_days_max": 5,
          "sla_reliability_score": 96.5
        },
        {
          "carrier": "DHL Express",
          "shipping_cost": 12.50,
          "delivery_days_min": 1,
          "delivery_days_max": 2,
          "sla_reliability_score": 99.1
        }
      ]
    }
    ```

---

## 2. Agent Tool Layer Interface Contract (LangGraph Tools)

Bộ Tool Layer đóng vai trò là "cánh tay nối dài" để LangGraph Agent thực thi các truy vấn và hành động. Toàn bộ các function Python dưới đây được bọc trong module `tools/burgerprints_tools.py` và khai báo cho Gemini LLM qua cơ chế Function Calling.

### 2.1. Tool: `search_catalog`
*   **Python Signature:**
    ```python
    def search_catalog(query: str, category: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Tìm kiếm các sản phẩm Print-on-Demand trong danh mục hệ thống BurgerPrints.
        
        Args:
            query (str): Từ khóa tìm kiếm sản phẩm (ví dụ: 't-shirt', 'mug', 'hoodie').
            category (str, optional): Phân loại sản phẩm ('Apparel', 'Drinkware', 'Home Decor').
            
        Returns:
            List[Dict]: Danh sách các sản phẩm khớp kèm mã product_id và danh sách thuộc tính.
        """
    ```
*   **Đầu ra mẫu (trả về cho Agent):**
    ```json
    [
      {
        "product_id": "bp_prod_tshirt_01",
        "name": "Classic Unisex T-Shirt",
        "colors": ["Black", "White", "Navy"],
        "sizes": ["S", "M", "L", "XL"]
      }
    ]
    ```

### 2.2. Tool: `get_factory_quotes`
*   **Python Signature:**
    ```python
    def get_factory_quotes(product_id: str, variant_id: str, market: str) -> List[Dict[str, Any]]:
        """
        Lấy báo giá thô từ các nhà in liên kết của BurgerPrints sản xuất biến thể sản phẩm này.
        
        Args:
            product_id (str): Mã sản phẩm gốc.
            variant_id (str): Mã biến thể cụ thể (Size L, Màu Black...).
            market (str): Quốc gia đích vận chuyển để ưu tiên lọc xưởng nội địa.
            
        Returns:
            List[Dict]: Danh sách các xưởng in nhận sản xuất kèm theo chi phí in và base cost.
        """
    ```
*   **Đầu ra mẫu (trả về cho Agent):**
    ```json
    [
      {
        "factory_id": "factory_us_chicago_01",
        "factory_name": "Chicago Print Corp",
        "location": "IL, US",
        "base_cost": 5.50,
        "printing_cost": 2.00,
        "production_time_days": 2
      }
    ]
    ```

### 2.3. Tool: `get_shipping_options`
*   **Python Signature:**
    ```python
    def get_shipping_options(origin_factory_id: str, destination_country: str, zip_code: str) -> List[Dict[str, Any]]:
        """
        Tra cứu các phương án vận chuyển khả dụng giữa nhà in và khách hàng.
        
        Args:
            origin_factory_id (str): ID của nhà in sản xuất sản phẩm.
            destination_country (str): Quốc gia đích (ví dụ: 'US', 'DE', 'VN').
            zip_code (str): Mã bưu chính của người nhận hàng.
            
        Returns:
            List[Dict]: Danh sách các gói cước vận chuyển, giá tiền và SLA ngày giao hàng.
        """
    ```
*   **Đầu ra mẫu (trả về cho Agent):**
    ```json
    [
      {
        "carrier": "USPS Standard",
        "shipping_cost": 4.20,
        "delivery_days_min": 3,
        "delivery_days_max": 5,
        "sla_reliability_score": 96.5
      }
    ]
    ```

### 2.4. Tool: `create_order`
*   **Python Signature:**
    ```python
    def create_order(sku: str, quantity: int, shipping_address: Dict[str, Any], selected_factory_id: str) -> Dict[str, Any]:
        """
        Gửi yêu cầu tạo đơn hàng POD chính thức lên hệ thống BurgerPrints.
        
        Args:
            sku (str): Mã SKU biến thể của sản phẩm cần đặt.
            quantity (int): Số lượng sản phẩm cần đặt.
            shipping_address (Dict): Địa chỉ nhận hàng đầy đủ của khách hàng.
            selected_factory_id (str): ID nhà in được chọn sản xuất.
            
        Returns:
            Dict: Thông tin phản hồi từ API bao gồm trạng thái đơn, mã đơn hàng bp_ord_xxx.
        """
    ```
*   **Đầu ra mẫu (trả về cho Agent):**
    ```json
    {
      "success": true,
      "order_id": "bp_ord_88776655",
      "status": "pending",
      "total_cogs": 24.35
    }
    ```

---

## 3. Quy Tắc Mapping Dữ Liệu Cho Lập Trình Viên (Developer Mapping Rules)

Để rút ngắn thời gian triển khai MVP từ 2 ngày xuống còn vài giờ, lập trình viên cần tuân thủ các quy tắc ánh xạ dữ liệu sau:

1.  **Mocking Fallback:** Trong file `.env`, cấu hình tham số `USE_MOCK_API=true` để toàn bộ các hàm trong `tools/burgerprints_tools.py` tự động đọc dữ liệu Mock JSON tĩnh cục bộ thay vì gửi request HTTP thật. Điều này giúp team né tránh các rủi ro API sập hoặc không có API Key hoạt động trong lúc demo Hackathon.
2.  **Mapping State sang API Payload:** Khi người dùng đồng ý chốt đơn, dữ liệu từ `AgentState` được ánh xạ sang API tạo đơn hàng như sau:
    *   `state['order_draft']['selected_option_id']` $\rightarrow$ ánh xạ vào `selected_factory_id` trong danh mục items của API.
    *   Các trường địa chỉ trong `state['order_draft']` $\rightarrow$ ánh xạ vào `shipping_address` của API.
3.  **Xử lý sai số tài chính (Floating Point):** Khi tính toán Landed Cost, Pricing Engine bắt buộc phải dùng hàm làm tròn `round(value, 2)` của Python trước khi ghi đè vào State và trả về API, ngăn ngừa việc hiển thị các số có nhiều chữ số thập phân dạng `24.349999999999` lên giao diện Streamlit UI gây mất thẩm mỹ.
