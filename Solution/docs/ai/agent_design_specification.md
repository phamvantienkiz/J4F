# AGENT DESIGN SPECIFICATION: BURGERPRINTS AGENT

Tài liệu này cung cấp các đặc tả kỹ thuật chi tiết phục vụ việc lập trình hệ thống **BurgerPrints Agent** trên nền tảng **LangGraph**. Đặc tả bao gồm cấu trúc trạng thái (Agent State), luồng chuyển đổi trạng thái (Workflow Transitions), giao thức dữ liệu (Data Contracts), và logic xử lý của từng nút (Nodes) trong đồ thị.

Tài liệu này được thiết kế thống nhất và liên kết chặt chẽ với [Solution Overview](file:///E:/Hackathon2026/J4F/Solution/docs/ai/solution_overview.md) và [System Architecture](file:///E:/Hackathon2026/J4F/Solution/docs/ai/system_architecture.md).

---

## 1. Thiết Kế Trạng Thái Agent (Agent State Design)

Trạng thái (State) của Agent là một cấu trúc dữ liệu tập trung, lưu trữ toàn bộ thông tin ngữ cảnh xuyên suốt cuộc hội thoại. Trong LangGraph, State được truyền qua lại giữa các Node và được cập nhật thông qua cơ chế ghi đè (override) hoặc tích lũy (reducer).

### 1.1. Cấu trúc Python Spec (`state.py`)

```python
from typing import TypedDict, List, Dict, Any, Optional
from pydantic import BaseModel, Field

class UserPreference(BaseModel):
    preferred_market: str = Field(default="US", description="Thị trường ưu tiên của seller (US, EU, VN...)")
    target_margin: float = Field(default=40.0, description="Mức lợi nhuận gộp mục tiêu tính theo %")
    max_shipping_days: int = Field(default=7, description="Thời gian giao hàng tối đa mong muốn (ngày)")
    fulfillment_priority: str = Field(default="margin", description="Ưu tiên tối ưu: 'margin' hoặc 'speed'")

class Requirements(BaseModel):
    product_type: Optional[str] = Field(None, description="Loại sản phẩm (ví dụ: Unisex T-Shirt, Ceramic Mug...)")
    color: Optional[str] = Field(None, description="Màu sắc sản phẩm")
    size: Optional[str] = Field(None, description="Kích thước sản phẩm")
    market: Optional[str] = Field(None, description="Thị trường đích vận chuyển")
    max_cogs: Optional[float] = Field(None, description="Giá vốn tối đa mong muốn (đã gồm in + ship)")
    print_method: Optional[str] = Field(None, description="Phương thức in ấn (DTG, Embroidery...)")

class CandidateOption(BaseModel):
    option_id: str
    factory_name: str
    factory_location: str
    base_cost: float
    printing_cost: float
    shipping_cost: float
    tax_cost: float
    landed_cost: float
    margin_percentage: float
    delivery_days_min: int
    delivery_days_max: int
    sla_risk_score: float  # Điểm rủi ro chậm trễ (0-100, càng thấp càng tốt)

class OrderDraft(BaseModel):
    sku: str
    quantity: int
    shipping_name: str
    shipping_address_line1: str
    shipping_city: str
    shipping_state: str
    shipping_zip: str
    shipping_country: str
    selected_option_id: str

# Định nghĩa Agent State chính chuyển qua các Nodes của LangGraph
class AgentState(TypedDict):
    thread_id: str                                      # Khóa duy nhất của phiên chat
    user_preferences: UserPreference                    # Bộ nhớ ưu tiên lâu dài của Seller
    conversation_history: List[Dict[str, Any]]         # Lịch sử chat (LangChain Messages format)
    requirements: Requirements                          # Các tham số trích xuất được từ yêu cầu hiện tại
    candidates: List[Dict[str, Any]]                    # Danh sách thô các sản phẩm/nhà in từ API
    calculated_options: List[CandidateOption]           # Danh sách các phương án đã được Pricing Engine tính toán
    ranking_results: List[CandidateOption]              # Top các phương án đã được xếp hạng
    last_missing_fields: List[str]                      # Danh sách các trường thông tin quan trọng còn thiếu
    order_draft: Optional[OrderDraft]                   # Đơn hàng nháp đang chuẩn bị xác nhận
    order_status: Optional[Dict[str, Any]]              # Trạng thái đơn hàng sau khi tạo (mã đơn, tracking...)
```

---

## 2. Quy Trình Chuyển Đổi Trạng Thái (Agent Workflow & State Transition)

Workflow của Agent được xây dựng dưới dạng một máy trạng thái (State Machine) điều phối bởi LangGraph. Dưới đây là bảng đặc tả chuyển đổi trạng thái:

### 2.1. Bảng chuyển đổi trạng thái (State Transition Table)

| Trạng thái hiện tại | Điều kiện chuyển tiếp (Conditional Routing) | Trạng thái tiếp theo (Next Node) | Giải thích hành động |
| :--- | :--- | :--- | :--- |
| **Bắt đầu (Input)** | Nhận tin nhắn mới từ Seller | `extract_intent_node` | Bắt đầu phân tích cú pháp tin nhắn. |
| **`extract_intent_node`** | `requirements` còn thiếu trường cốt lõi (ví dụ: thiếu `product_type` hoặc `market`) | `clarify_node` | Chuyển sang đặt câu hỏi làm rõ tham số lọc. |
| **`extract_intent_node`** | Đầy đủ thông tin cốt lõi | `retrieve_catalog_node` | Đủ điều kiện truy vấn danh mục xưởng. |
| **`clarify_node`** | Trả câu hỏi làm rõ về UI và đợi phản hồi | **Đợi Input của User** | Tạm dừng luồng, giữ checkpoint trạng thái. |
| **`retrieve_catalog_node`**| API phản hồi dữ liệu thô thành công | `calculate_pricing_node` | Chuyển sang tính toán chi phí chi tiết. |
| **`calculate_pricing_node`**| Phép tính số liệu Python hoàn tất | `rank_and_recommend_node` | Chuyển dữ liệu sạch sang xếp hạng. |
| **`rank_and_recommend_node`**| Hiển thị bảng so sánh xong và đợi phản hồi | **Đợi Input của User** | Seller xem xét bảng, có thể đổi thông số hoặc chốt đơn. |
| **Đợi Input của User** | User ra lệnh: *"Chốt option X"* hoặc nhấn nút đặt hàng | `execute_order_node` | Chuyển sang bước tạo đơn hàng thực tế (Human-in-the-loop). |
| **`execute_order_node`** | API tạo đơn thành công | **Kết thúc (Done)** | Trả về thông tin đơn hàng và mã vận đơn. |

---

## 3. Đặc Tả Chi Tiết Từng Node (Agent Nodes Specification)

Dưới đây là đặc tả chi tiết đầu vào, đầu ra, và logic xử lý của từng Node trong LangGraph.

### 3.1. Intent & Slot Extraction Node (`extract_intent_node`)
*   **Mục tiêu:** Nhận diện ý định của người dùng và bóc tách các tham số lọc sản phẩm (slots).
*   **Đầu vào:** `conversation_history` (Tin nhắn mới nhất từ người dùng).
*   **Đầu ra:** Cập nhật trường `requirements` trong State.
*   **Logic xử lý:**
    *   Gọi Gemini API bằng kỹ thuật **Structured Outputs** (ép đầu ra theo định dạng JSON Schema của class `Requirements` ở trên).
    *   System Prompt quy định: *Chỉ trích xuất các thông tin có trong tin nhắn hoặc kế thừa từ `user_preferences`. Không được tự bịa ra thông số.*
    *   *Ví dụ Prompt:*
        ```
        Bạn là trợ lý NLU. Hãy phân tích tin nhắn mới nhất của người dùng và trích xuất các thuộc tính: product_type, color, size, market, max_cogs, print_method.
        Nếu người dùng không nhắc đến thị trường (market), hãy kiểm tra phần cài đặt ưu tiên của user: {state['user_preferences']}.
        ```

### 3.2. Clarification Node (`clarify_node`)
*   **Mục tiêu:** Sinh câu hỏi định hướng ngắn gọn để lấy các thông số lọc còn thiếu.
*   **Đầu vào:** `requirements` hiện tại, `last_missing_fields` (danh sách các trường trống).
*   **Đầu ra:** Cập nhật tin nhắn hỏi của Agent vào `conversation_history`.
*   **Logic xử lý:**
    *   Xác định các thông số bắt buộc phải có để call API (bắt buộc gồm: `product_type` và `market`).
    *   Nếu thiếu, Agent gọi Gemini API sinh câu hỏi tập trung.
    *   *Ví dụ logic:*
        ```python
        missing = []
        if not state['requirements'].product_type:
            missing.append("loại sản phẩm (ví dụ: áo T-shirt, cốc sứ)")
        if not state['requirements'].market:
            missing.append("thị trường giao hàng (ví dụ: US, EU)")
        
        state['last_missing_fields'] = missing
        # Gọi LLM sinh câu hỏi dạng: "Bạn muốn tìm loại sản phẩm nào và giao tới quốc gia nào?"
        ```

### 3.3. Catalog Retrieval Node (`retrieve_catalog_node`)
*   **Mục tiêu:** Gọi BurgerPrints API tìm kiếm sản phẩm và xưởng in.
*   **Đầu vào:** `requirements` (thông số lọc đã hoàn thiện).
*   **Đầu ra:** Cập nhật danh sách báo giá thô vào `candidates` trong State.
*   **Logic xử lý:**
    *   Node này là **Deterministic (không dùng LLM)**.
    *   Thực hiện tuần tự:
        1.  Gọi `search_catalog` tìm kiếm `product_type` để lấy về `product_id`.
        2.  Gọi `get_product_detail` với `product_id` để lấy về danh sách biến thể `variant_id` (size, color tương ứng).
        3.  Gọi `get_factory_quotes` lấy danh sách báo giá gốc (base cost) và phí in từ các xưởng có sẵn biến thể đó.
        4.  Lưu mảng kết quả thô vào `candidates`.

### 3.4. Calculation Node (`calculate_pricing_node`)
*   **Mục tiêu:** Tính toán landed cost và margin thực tế của từng xưởng in bằng code Python.
*   **Đầu vào:** `candidates` (báo giá thô), `requirements`, `user_preferences`.
*   **Đầu ra:** Cập nhật danh sách đối tượng `calculated_options` vào State.
*   **Logic xử lý:**
    *   **Cấm tuyệt đối LLM tính toán phần này.**
    *   Với mỗi xưởng in trong `candidates`, thực hiện:
        *   Gọi API vận chuyển `get_shipping_options` dựa trên địa chỉ xưởng (origin) và thị trường đích (destination) để lấy giá ship (`shipping_cost`) và thời gian giao hàng SLA (`delivery_days`).
        *   Tính tổng:
            $$LandedCost = BaseCost + PrintingCost + ShippingCost + Tax$$
        *   Tính Margin (giả định dựa trên giá bán ước tính của seller hoặc mặc định gấp đôi base cost nếu seller chưa cấu hình giá bán):
            $$MarginPercentage = \left(\frac{SellingPrice - LandedCost}{SellingPrice}\right) \times 100$$
        *   Đánh giá rủi ro SLA (`sla_risk_score`) dựa trên tỷ lệ giao hàng đúng hạn lịch sử của xưởng.
    *   Đóng gói thành các đối tượng `CandidateOption` và lưu vào State.

### 3.5. Recommendation Node (`rank_and_recommend_node`)
*   **Mục tiêu:** Xếp hạng các phương án tối ưu và sinh văn bản trình bày chi tiết cho Seller.
*   **Đầu vào:** `calculated_options`, `user_preferences`.
*   **Đầu ra:** Cập nhật `ranking_results` và sinh tin nhắn phản hồi chứa bảng Markdown.
*   **Logic xử lý:**
    *   Bước 1: Chạy thuật toán xếp hạng cứng (Scoring) trên danh sách `calculated_options`:
        *   Nếu seller ưu tiên lợi nhuận (`fulfillment_priority == 'margin'`):
            $$Score = MarginPercentage \times 0.6 + (10 - LandedCost) \times 0.2 + (15 - DeliveryDays_{Max}) \times 0.2$$
        *   Nếu seller ưu tiên tốc độ giao hàng (`fulfillment_priority == 'speed'`):
            $$Score = (15 - DeliveryDays_{Max}) \times 0.6 + MarginPercentage \times 0.2 + (100 - SlaRiskScore) \times 0.2$$
    *   Bước 2: Chọn ra Top 3 phương án có điểm cao nhất lưu vào `ranking_results`.
    *   Bước 3: Gửi Top 3 phương án này sang Gemini API để sinh text giải trình lý do xếp hạng. Định dạng đầu ra bắt buộc tuân thủ cấu trúc 4 khối (Kết luận, Bảng so sánh, Giải trình trade-off, Gợi ý bước tiếp theo) theo đặc tả của [Solution Overview](file:///E:/Hackathon2026/J4F/Solution/docs/ai/solution_overview.md#7-định-dạng-đầu-ra-ra-quyết-định-decision-ready-outputs).

### 3.6. Order Creation Node (`execute_order_node`)
*   **Mục tiêu:** Tạo đơn hàng thực tế trên BurgerPrints sau khi được xác nhận.
*   **Đầu vào:** `order_draft` (chứa SKU, số lượng, địa chỉ khách hàng và xưởng được chọn).
*   **Đầu ra:** Cập nhật kết quả API trả về vào `order_status`.
*   **Logic xử lý:**
    *   Node này yêu cầu **Human-in-the-loop**. Khi nhận được tín hiệu "Chốt đơn" từ UI/Chat:
        1.  Gọi `validate_order_draft` để kiểm tra độ tin cậy của thông tin giao hàng (định dạng ZIP code, trường trống).
        2.  Gọi Action Tool `create_order` truyền payload lên BurgerPrints.
        3.  Nhận mã giao dịch và mã tracking từ API.
        4.  Lưu trạng thái vào `order_status`.
        5.  Lưu checkpoint trạng thái hoàn thành vào SQLite DB.

---

## 4. Đặc Tả Dữ Liệu Trao Đổi (Data Contracts)

Để đảm bảo các API kết nối giữa các node và dịch vụ ngoài không bị lỗi kiểu dữ liệu (Type error), dưới đây là đặc tả JSON Payload trao đổi cốt lõi:

### 4.1. Payload gửi từ Gemini NLU (Intent & Slot Output)
```json
{
  "intent": "product_search",
  "slots": {
    "product_type": "Unisex T-Shirt",
    "color": "black",
    "size": "L",
    "market": "US",
    "max_cogs": 15.50,
    "print_method": "DTG"
  }
}
```

### 4.2. Payload kết quả từ Pricing Engine gửi sang Ranking Node
```json
[
  {
    "option_id": "opt_swift_us_01",
    "factory_name": "SwiftPrint Atlanta",
    "factory_location": "Georgia, US",
    "base_cost": 5.50,
    "printing_cost": 2.00,
    "shipping_cost": 4.20,
    "tax_cost": 0.50,
    "landed_cost": 12.20,
    "margin_percentage": 39.0,
    "delivery_days_min": 3,
    "delivery_days_max": 5,
    "sla_risk_score": 8.5
  }
]
```

### 4.3. Payload gửi lên BurgerPrints API để Tạo Đơn Hàng (`create_order`)
```json
{
  "provider_key": "opt_swift_us_01",
  "order_items": [
    {
      "sku": "BP-TSHIRT-BLK-L",
      "quantity": 1,
      "base_price": 5.50,
      "print_price": 2.00
    }
  ],
  "shipping_address": {
    "full_name": "John Doe",
    "address_line1": "123 Main St",
    "city": "San Jose",
    "state": "CA",
    "zip_code": "95112",
    "country": "US"
  }
}
```

---

## 5. Xử Lý Rủi Ro & Cơ Chế Dự Phòng (Error Handling & Fallbacks)

1.  **API BurgerPrints bị lỗi kết nối hoặc Timeout:**
    *   *Giải pháp:* Hệ thống tự động chuyển sang chế độ Mock Data (dữ liệu giả lập đã được cache sẵn trong SQLite từ các phiên làm việc trước) để đảm bảo không bị ngắt quãng luồng demo. Agent sẽ thông báo cho Seller: *"Hiện kết nối trực tiếp đến BurgerPrints đang gián đoạn, em đang hiển thị dữ liệu ước tính được tối ưu hóa từ bộ nhớ đệm."*
2.  **LLM trả về kết quả JSON bị lỗi cấu trúc (JSON Parse Error):**
    *   *Giải pháp:* Tích hợp bộ giải mã phòng ngừa (Fallback Parser). Nếu parsing JSON thất bại, Agent kích hoạt một node sửa lỗi tự động (Retry Node) gửi lại prompt kèm thông tin lỗi cho Gemini để sinh lại, hoặc chuyển về cấu hình mặc định (default values) của `Requirements` để đảm bảo hệ thống không bị crash.
3.  **Người dùng thay đổi chủ đề đột ngột (Context Switch):**
    *   *Giải pháp:* Trong node `extract_intent_node`, nếu phát hiện ý định của người dùng thay đổi 180 độ (ví dụ: đang tạo dở đơn hàng áo thun lại nói *"Tìm cốc sứ"*), Agent sẽ lưu tạm đơn hàng nháp cũ vào DB và gửi câu hỏi xác nhận: *"Em thấy bạn muốn tìm sản phẩm mới (Cốc sứ). Bạn có muốn hủy bỏ đơn hàng áo thun đang tạo dở không?"*
