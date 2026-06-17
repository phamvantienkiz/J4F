# Tài liệu Thiết kế Hệ thống BurgerPrints Agent (Production-Ready)
**Ngày tạo:** 2026-06-15  
**Trạng thái:** Thiết kế chi tiết (Design Spec)  
**Tác giả:** Claude Agent

---

## 🎨 1. Sơ đồ Kiến trúc Hệ thống (Draw.io XML)

Bạn có thể sao chép toàn bộ khối mã XML bên dưới, truy cập trang [Draw.io](https://app.diagrams.net/), chọn **Arrange -> Insert -> Advanced -> XML** (hoặc kéo thả tệp này vào), paste đoạn mã này vào để hiển thị sơ đồ trực quan:

```xml
<mxGraphModel dx="1000" dy="800" grid="1" gridSize="10" guides="1" tooltips="1" connect="1" arrows="1" fold="1" page="1" pageScale="1" pageWidth="850" pageHeight="1100" math="0" shadow="0">
  <root>
    <mxCell id="0" />
    <mxCell id="1" parent="0" />
    <mxCell id="nextjs" value="Next.js Frontend&#xa;(Chat UI, Order Panel)" style="rounded=1;whiteSpace=wrap;html=1;fillColor=#dae8fc;strokeColor=#6c8ebf;fontStyle=1" vertex="1" parent="1">
      <mxGeometry x="40" y="240" width="160" height="80" as="geometry" />
    </mxCell>
    <mxCell id="fastapi" value="FastAPI Backend&#xa;(Router, Middleware, Schedulers)" style="rounded=1;whiteSpace=wrap;html=1;fillColor=#d5e8d4;strokeColor=#82b366;fontStyle=1" vertex="1" parent="1">
      <mxGeometry x="280" y="240" width="200" height="80" as="geometry" />
    </mxCell>
    <mxCell id="agent_mgr" value="State-Driven Agent Flow&#xa;(Pydantic &amp; State Manager)" style="rounded=1;whiteSpace=wrap;html=1;fillColor=#ffe6cc;strokeColor=#d79b00;fontStyle=1" vertex="1" parent="1">
      <mxGeometry x="560" y="240" width="200" height="80" as="geometry" />
    </mxCell>
    <mxCell id="supabase" value="Supabase PostgreSQL&#xa;(Session, Cache, Products)" style="shape=cylinder3;whiteSpace=wrap;html=1;boundedLbl=1;backgroundOutline=1;size=15;fillColor=#e1d5e7;strokeColor=#9673a6;fontStyle=1" vertex="1" parent="1">
      <mxGeometry x="290" y="440" width="180" height="80" as="geometry" />
    </mxCell>
    <mxCell id="bp_api" value="BurgerPrints API v2&#xa;(External API)" style="ellipse;shape=cloud;whiteSpace=wrap;html=1;fillColor=#f5f5f5;strokeColor=#666666;fontColor=#333333;fontStyle=1" vertex="1" parent="1">
      <mxGeometry x="570" y="440" width="180" height="80" as="geometry" />
    </mxCell>
    <mxCell id="tax_calc" value="ITaxCalculator&#xa;(Interface Thuế)" style="rounded=1;whiteSpace=wrap;html=1;fillColor=#f8cecc;strokeColor=#b85450;fontStyle=1" vertex="1" parent="1">
      <mxGeometry x="500" y="80" width="140" height="60" as="geometry" />
    </mxCell>
    <mxCell id="trend_service" value="ITrendService&#xa;(Interface Trend &amp; Season)" style="rounded=1;whiteSpace=wrap;html=1;fillColor=#fff2cc;strokeColor=#d6b656;fontStyle=1" vertex="1" parent="1">
      <mxGeometry x="680" y="80" width="140" height="60" as="geometry" />
    </mxCell>
    <mxCell id="e1" value="HTTP / JSON" style="edgeStyle=orthogonalEdgeStyle;rounded=0;orthogonalLoop=1;jettySize=auto;html=1;exitX=1;exitY=0.5;exitDx=0;exitDy=0;entryX=0;entryY=0.5;entryDx=0;entryDy=0;" edge="1" parent="1" source="nextjs" target="fastapi">
      <mxGeometry relative="1" as="geometry" />
    </mxCell>
    <mxCell id="e2" value="Calls Agent" style="edgeStyle=orthogonalEdgeStyle;rounded=0;orthogonalLoop=1;jettySize=auto;html=1;exitX=1;exitY=0.5;exitDx=0;exitDy=0;entryX=0;entryY=0.5;entryDx=0;entryDy=0;" edge="1" parent="1" source="fastapi" target="agent_mgr">
      <mxGeometry relative="1" as="geometry" />
    </mxCell>
    <mxCell id="e3" value="SQLAlchemy Sync/Async" style="edgeStyle=orthogonalEdgeStyle;rounded=0;orthogonalLoop=1;jettySize=auto;html=1;exitX=0.5;exitY=1;exitDx=0;exitDy=0;entryX=0.5;entryY=0;entryDx=0;entryDy=0;entryPerimeter=0;" edge="1" parent="1" source="fastapi" target="supabase">
      <mxGeometry relative="1" as="geometry" />
    </mxCell>
    <mxCell id="e4" value="Save Session State" style="edgeStyle=orthogonalEdgeStyle;rounded=0;orthogonalLoop=1;jettySize=auto;html=1;exitX=0.25;exitY=1;exitDx=0;exitDy=0;entryX=0.75;entryY=0;entryDx=0;entryDy=0;entryPerimeter=0;" edge="1" parent="1" source="agent_mgr" target="supabase">
      <mxGeometry relative="1" as="geometry">
        <Array as="points">
          <mxPoint x="610" y="380" />
          <mxPoint x="425" y="380" />
        </Array>
      </mxGeometry>
    </mxCell>
    <mxCell id="e5" value="Real-time check &amp;&#xa;Sandbox Fulfill" style="edgeStyle=orthogonalEdgeStyle;rounded=0;orthogonalLoop=1;jettySize=auto;html=1;exitX=0.5;exitY=1;exitDx=0;exitDy=0;entryX=0.5;entryY=0.125;entryDx=0;entryDy=0;entryPerimeter=0;" edge="1" parent="1" source="agent_mgr" target="bp_api">
      <mxGeometry relative="1" as="geometry" />
    </mxCell>
    <mxCell id="e6" value="Get Tax Rate" style="edgeStyle=orthogonalEdgeStyle;rounded=0;orthogonalLoop=1;jettySize=auto;html=1;exitX=0.25;exitY=0;exitDx=0;exitDy=0;entryX=0.5;entryY=1;entryDx=0;entryDy=0;" edge="1" parent="1" source="agent_mgr" target="tax_calc">
      <mxGeometry relative="1" as="geometry" />
    </mxCell>
    <mxCell id="e7" value="Get Trends" style="edgeStyle=orthogonalEdgeStyle;rounded=0;orthogonalLoop=1;jettySize=auto;html=1;exitX=0.75;exitY=0;exitDx=0;exitDy=0;entryX=0.5;entryY=1;entryDx=0;entryDy=0;" edge="1" parent="1" source="agent_mgr" target="trend_service">
      <mxGeometry relative="1" as="geometry" />
    </mxCell>
  </root>
</mxGraphModel>
```

---

## 📖 2. Giải thích Chi tiết Kiến trúc Hệ thống & Luồng Dữ liệu (Vietnamese)

Kiến trúc hệ thống mới được tinh gọn tối đa nhằm phục vụ môi trường thương mại thực tế (Production), loại bỏ hoàn toàn các lớp trung gian không cần thiết để tăng tốc độ phản hồi và độ chính xác của Agent.

### 2.1. Các Thành phần Chính (System Layers)
1. **Next.js Frontend (Màu Xanh Dương):**
   * **Nhiệm vụ:** Quản lý giao diện tương tác người dùng. Bao gồm Khung hội thoại Chatbot và Bảng soạn thảo đơn hàng thử nghiệm (Order Draft Panel) hiển thị đồng thời khi phát hiện ý định tạo đơn.
   * **Giao tiếp:** Gọi các API endpoints trực tiếp sang FastAPI thông qua giao thức REST (định dạng JSON và truyền token JWT để xác thực).
2. **FastAPI Backend (Màu Xanh Lá Cây):**
   * **Nhiệm vụ:** Đóng vai trò là cổng API chính (API Gateway). Quản lý xác thực người dùng, middleware, và các luồng tác vụ nền (Background Schedulers - APScheduler) để đồng bộ hóa danh mục sản phẩm từ BurgerPrints sau mỗi 6-12 tiếng.
   * **CSDL:** Kết nối và thao tác với cơ sở dữ liệu Supabase thông qua thư viện ORM **SQLAlchemy** (hoặc SQLModel).
3. **State-Driven Agent Flow (Màu Cam):**
   * **Nhiệm vụ:** Trái tim logic của Agent. Không để LLM tự do suy nghĩ mà quản lý luồng bằng một State Machine chặt chẽ.
   * **Trích xuất dữ liệu:** Sử dụng mô hình AI (như GPT-4o-mini hoặc Claude 3.5 Haiku) để trích xuất các thông số hội thoại của người dùng (loại sản phẩm, màu, kích thước, giá bán lẻ mong muốn, quốc gia giao hàng) thành một cấu trúc dữ liệu định kiểu nghiêm ngặt bằng **Pydantic Model**.
   * **State Validation (Slot Filling):** Nếu thiếu thông tin quan trọng (như thiếu giá bán để tính Margin), Agent Flow sẽ chặn luồng xử lý và yêu cầu Next.js hiển thị câu hỏi làm rõ. Khi đầy đủ thông tin, code Python thuần mới được thực thi nhằm đảm bảo tính toán toán học chính xác 100%.
4. **Supabase PostgreSQL Database (Màu Tím):**
   * **Nhiệm vụ:** Nơi lưu trữ duy nhất của hệ thống. Chứa cache danh sách sản phẩm và biến thể SKU BurgerPrints, danh sách quốc gia được hỗ trợ, lịch sử hội thoại của người dùng (Session History), và cấu hình hệ thống.
5. **BurgerPrints API v2 & Public Catalog API v1 (Hình Đám Mây):**
   * **Nhiệm vụ:** Nguồn dữ liệu gốc từ đối tác.
   * **Real-time Check:** Khi người dùng bắt đầu tiến trình tạo đơn hàng Sandbox, Agent sẽ thực hiện kiểm tra thời gian thực (Real-time stock check) tới BurgerPrints API để đảm bảo SKU đó đang còn hàng thực tế trước khi điền thông tin địa chỉ giao hàng.
6. **ITaxCalculator & ITrendService (Màu Đỏ & Vàng):**
   * **Nhiệm vụ:** Các Module mở rộng (Interfaces) được định nghĩa sẵn để ghép nối các nghiên cứu độc lập trong tương lai (Tính Thuế và Gợi ý Xu hướng thời gian thực) mà không làm ảnh hưởng hay phát sinh lỗi cho mã nguồn lõi.

---

## 🔑 3. Cấu hình Tích hợp API BurgerPrints & Xác thực

Để các đơn hàng được đẩy thành công lên hệ thống quản lý của BurgerPrints và hiển thị chính xác trên dashboard, hệ thống cần cấu hình key xác thực (Authentication).

### 3.1. API Key của Người Dùng
Trong quá trình chạy và phát triển sản phẩm, hệ thống sử dụng khoá API Key của người dùng để thực thi các yêu cầu:
*   **Giá trị API Key:** `147a7d53-f1ed-0203-e065-00b14e8ebbf6`
*   **Phương thức cấu hình:** Key này sẽ được ghi vào biến môi trường `.env` hoặc file cấu hình bí mật trên FastAPI Backend:
    ```env
    BURGERPRINTS_API_KEY=147a7d53-f1ed-0203-e065-00b14e8ebbf6
    BURGERPRINTS_API_BASE_URL=https://api.burgerprints.com/v2
    BURGERPRINTS_ENABLE_SANDBOX_CREATE_ORDER=true
    ```
*   **Header Xác thực:** Mỗi khi Agent gọi API tạo đơn hoặc kiểm tra thông tin số dư (Balance) của BurgerPrints, Backend sẽ chèn khóa này vào header của HTTP Request:
    ```http
    api-key: 147a7d53-f1ed-0203-e065-00b14e8ebbf6
    Accept: application/json
    ```

---

## 🌡️ 4. Thiết kế Bộ Gợi ý Sản phẩm theo Mùa vụ & Khu vực (Seasonal & Regional Engine)

Tính năng gợi ý sản phẩm theo **Tháng (Mùa vụ)** và **Quốc gia/Khu vực (Địa lý)** được tích hợp trực tiếp làm nhân tố cốt lõi trong phase phát triển này. Thay vì để LLM tự suy luận (không chính xác về mặt địa lý/thời tiết), hệ thống sử dụng **State-Driven Function Calling** kết hợp với logic lập trình Python xác định (Deterministic).

### 4.1. Định nghĩa Schema Trích xuất Đầu vào (Pydantic Model)
Khi người dùng hỏi về gợi ý sản phẩm hoặc xu hướng, LLM sẽ trích xuất thông tin đầu vào bằng cấu hình Pydantic nghiêm ngặt (`strict=True`):

```python
from pydantic import BaseModel, Field, field_validator
from typing import Optional

class SeasonalAnalysisInput(BaseModel):
    model_config = {"extra": "forbid"}  # strict=True (Ngăn chặn các tham số lạ)
    
    month: int = Field(
        ..., 
        ge=1, 
        le=12, 
        description="Tháng cần truy vấn thông tin gợi ý hoặc xu hướng (Giá trị từ 1 đến 12)"
    )
    country_code: str = Field(
        ..., 
        min_length=2, 
        max_length=2, 
        description="Mã quốc gia đích gồm 2 ký tự viết hoa (ISO 3166-1 alpha-2, ví dụ: US, CA, AU)"
    )
    niche_hint: Optional[str] = Field(
        None, 
        description="Gợi ý ngách/niche thiết kế nếu người dùng yêu cầu cụ thể (ví dụ: 'retro', 'dog')"
    )

    @field_validator("country_code")
    @classmethod
    def validate_country_upper(cls, v: str) -> str:
        return v.upper()
```

### 4.2. Logic Python Xử lý Xác định (Deterministic Engine Logic)
Khi nhận dữ liệu từ `SeasonalAnalysisInput`, Python Backend sẽ xử lý qua 3 lớp logic decoupled (phân tách rạch ròi):

#### Lớp A: Kiểm tra và Khớp nối Quốc gia được Hỗ trợ trong Database (Supported Country Gating)
Để đảm bảo tốc độ phản hồi cực nhanh (< 1.5s) và tránh gọi API ngoài liên tục gây nghẽn:
1.  **Cache Quốc gia (Database Cache):** Danh sách các quốc gia/vùng miền được BurgerPrints hỗ trợ vận chuyển sẽ được lưu trữ và cache trong cơ sở dữ liệu Supabase PostgreSQL. Dữ liệu này được tự động đồng bộ theo chu kỳ 6-12 tiếng từ endpoint `GET /catalogsV2/locations` của BurgerPrints API.
2.  **Kiểm tra nội bộ (Internal Check):** Hệ thống sẽ thực hiện truy vấn đối chiếu quốc gia người dùng yêu cầu trực tiếp với dữ liệu cache trong DB cục bộ.
3.  **Cơ chế fallback (Nearest Supported Country):** Nếu quốc gia yêu cầu không được hỗ trợ:
    *   Hệ thống chuyển sang chế độ **"Nearest Alternative Country Mode"** (Ví dụ: `NZ` thay thế cho một số đảo Nam Thái Bình Dương, hoặc `US`/`CA` làm trung tâm Bắc Mỹ).
    *   Trả về phản hồi giải thích rõ ràng lý do thay thế quốc gia đích để đảm bảo trải nghiệm người dùng.

#### Lớp B: Khớp nối Văn hóa & Lễ hội (Culture & Holiday Mapping)
Các sự kiện văn hóa, ngày lễ lớn cố định theo tháng và khu vực địa lý:
*   **Mỹ (US):** 
    - Tháng 7 -> Independence Day (Quốc khánh Mỹ - July 4th)
    - Tháng 11 -> Thanksgiving & Black Friday
    - Tháng 12 -> Christmas
*   **Toàn cầu / Các nước phương Tây:**
    - Tháng 2 -> Valentine's Day
    - Tháng 5 -> Mother's Day
    - Tháng 10 -> Halloween

#### Lớp C: Khớp nối Khí hậu & Vùng địa lý (Regional Climate Mapping)
Thời tiết quyết định loại trang phục. Logic này được ánh xạ theo Vĩ độ địa lý (Bán cầu Bắc vs Bán cầu Nam):
*   **Bán cầu Bắc (Northern Hemisphere):** Gồm `US`, `CA`, `GB` (UK), các nước EU.
    - Nếu tháng `6, 7, 8` -> Mùa Hè (Summer) -> Ưu tiên gợi ý: **T-shirts, Tank Tops, Canvas Bags**.
    - Nếu tháng `12, 1, 2` -> Mùa Đông (Winter) -> Ưu tiên gợi ý: **Hoodies, Sweatshirts, Long Sleeves**.
*   **Bán cầu Nam (Southern Hemisphere):** Gồm `AU` (Australia), `NZ` (New Zealand).
    - Nếu tháng `6, 7, 8` -> Mùa Đông (Winter) -> Ưu tiên gợi ý: **Hoodies, Sweatshirts**.
    - Nếu tháng `12, 1, 2` -> Mùa Hè (Summer) -> Ưu tiên gợi ý: **T-shirts, Tank Tops**.

---

## 🛠️ 5. Database Schema & Interface Gợi ý Mùa vụ (ITrendService)

### 5.1. Định nghĩa Interface Python
```python
from abc import ABC, abstractmethod
from typing import List, Dict, Any, Tuple
from enum import Enum

class ClimateType(str, Enum):
    SUMMER = "summer"
    WINTER = "winter"
    SPRING_AUTUMN = "spring_autumn"

class EventMetadata(BaseModel):
    name: str
    description: str
    target_niches: List[str]
    suggested_categories: List[str]

class SkuRecommendation(BaseModel):
    sku: str
    name: str
    base_cost: float
    shipping_cost: float
    shipping_sla: str
    workshop_location: str
    profit_margin_est: float = 0.0

class ITrendService(ABC):
    @abstractmethod
    def validate_and_fallback_country(self, country_code: str) -> Tuple[str, bool]:
        """
        Kiểm tra xem quốc gia có được hỗ trợ vận chuyển hay không (Truy vấn DB cache cục bộ).
        Trả về: (quốc gia thực tế sử dụng, True nếu là quốc gia gốc / False nếu là quốc gia fallback)
        """
        pass

    @abstractmethod
    def get_events_by_region(self, month: int, country_code: str) -> List[EventMetadata]:
        """Lấy danh sách các sự kiện/ngày lễ hội dựa trên tháng và quốc gia"""
        pass

    @abstractmethod
    def get_climate_season(self, month: int, country_code: str) -> ClimateType:
        """Xác định mùa khí hậu (Summer/Winter) của quốc gia đó tại tháng truy vấn"""
        pass

    @abstractmethod
    def recommend_catalog_skus(self, categories: List[str], country_code: str) -> List[SkuRecommendation]:
        """
        Khuyến nghị các SKU cụ thể từ cơ sở dữ liệu Supabase.
        Thực hiện một truy vấn JOIN logic giữa các Category được gợi ý và bảng 'Catalog Cache'
        để lấy ra SKU có Base Cost tốt nhất, vị trí xưởng sản xuất gần nhất, và SLA ship nhanh nhất.
        """
        pass
```

### 5.2. Luồng thực thi logic JOIN dữ liệu (Database JOIN Logic)
Để lấy ra các SKU cụ thể thay vì chỉ gợi ý chung chung như "Áo phông", hàm `recommend_catalog_skus` sẽ thực hiện truy vấn SQL (qua SQLAlchemy) tới database **Supabase PostgreSQL**:

```sql
SELECT 
    c.short_code, 
    c.display_name, 
    v.sku, 
    v.base_cost, 
    s.first_item_price AS shipping_cost,
    s.description AS shipping_sla,
    l.location_name AS workshop_location
FROM catalogs c
JOIN variants v ON c.short_code = v.catalog_short_code
JOIN fulfillment_locations l ON v.location_id = l.location_id
JOIN shipping_rates s ON (s.short_code = c.short_code AND s.location_id = l.location_id)
WHERE c.category IN (:categories)
  AND s.country_code = :country_code
ORDER BY v.base_cost ASC, s.first_item_price ASC
LIMIT 3;
```
*   **Kết quả:** Trả về chính xác mã SKU của BurgerPrints (Ví dụ: `USG5000-Wht-S`), mức giá vốn thực tế của xưởng phù hợp nhất, và thời gian giao hàng thực tế tới quốc gia đó để hiển thị trực tiếp cho Seller ra quyết định.

---

## 🔒 6. Luồng Nghiệp vụ Sandbox Order Gating & PII Masking

1. **Ý định tạo đơn:** Khi người dùng gửi yêu cầu hoặc click nút "Tạo Sandbox Order" trên UI, Next.js sẽ gửi yêu cầu sang FastAPI.
2. **Real-time Stock Check:** Backend gọi API BurgerPrints để kiểm tra thời gian thực trạng thái kho hàng của SKU mục tiêu. Chỉ kích hoạt gọi API trực tiếp khi người dùng bắt đầu quy trình tạo đơn. Nếu hết hàng, Agent báo lỗi ngay lập tức trên UI và đề xuất SKU thay thế.
3. **Draft Billing & PII Masking:** Next.js mở Order Panel, người dùng điền thông tin địa chỉ. Toàn bộ thông tin nhạy cảm của khách hàng (Tên, Địa chỉ cụ thể, SĐT, Zipcode) sẽ được **che giấu (masking)** trước khi lưu trữ vào nhật ký chat của AI Agent (Ví dụ: `J*** D***`, `123 M*** St`).
4. **Xác nhận 2 lớp:** Nút "Đặt hàng" trên UI sẽ bị vô hiệu hóa cho đến khi người dùng nhập chính xác chuỗi xác nhận bắt buộc vào ô chat:
   * `"confirm create sandbox order"` hoặc `"xác nhận tạo sandbox order"`.
   * **Tuyệt đối không chấp nhận các từ xác nhận ngắn** như "ok", "yes", "có", "xác nhận".
