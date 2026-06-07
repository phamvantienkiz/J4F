# 🍔 BurgerPrints Agent - Trợ lý Đối chiếu & Tạo Đơn Fulfillment (Text-to-API)

> Hệ thống conversational AI multi-agent giúp người bán (seller) POD chuyển đổi các yêu cầu bằng ngôn ngữ tự nhiên (tiếng Việt/tiếng Anh) thành các lệnh gọi API BurgerPrints v2.0, tự động xếp hạng SKU/supplier, tính toán biên lợi nhuận và hỗ trợ tạo đơn hàng sandbox an toàn.

**Trạng thái dự án:** ✅ MVP Hoàn thiện | **Công nghệ:** Python 3.11+, FastAPI, LangGraph, React + Vite + TS

---

## 📋 Mục lục
- [1. Giới thiệu tổng quan](#1-giới thiệu-tổng-quan)
- [2. Các tính năng chính](#2-các-tính-năng-chính)
- [3. Hướng dẫn cài đặt nhanh (Quick Start)](#3-hướng-dẫn-cài-đặt-nhanh-quick-start)
- [4. Kiến trúc hệ thống & Luồng xử lý](#4-kiến-trúc-hệ-thống--luồng-xử-lý)
- [5. Hướng dẫn chạy thử nghiệm (Smoke Tests)](#5-hướng-dẫn-chạy-thử-nghiệm-smoke-tests)
- [6. Quy tắc an toàn & Bảo mật](#6-quy-tắc-an-toàn--bảo-mật)
- [7. Cấu trúc thư mục dự án](#7-cấu-trúc-thư-mục-dự-án)
- [8. Đóng góp & Phát triển tính năng mới](#8-đóng-góp--phát-triển-tính-năng-mới)

---

## 🎯 1. Giới thiệu tổng quan

**BurgerPrints Agent** giải quyết bài toán cốt lõi của seller Print-On-Demand (POD):
- Tìm kiếm nhanh SKU phù hợp nhất theo ngân sách (base cost), thời gian giao hàng (delivery time) và quốc gia giao hàng (destination market).
- Tính toán chính xác lợi nhuận gộp (gross margin) theo từng platform (Etsy, Shopify, Amazon, TikTok, Generic) sau khi trừ chi phí sản xuất, vận chuyển và phí sàn.
- Tạo nhanh đơn hàng thử nghiệm (sandbox draft) trực tiếp qua cổng chat mà không cần thao tác thủ công trên dashboard của BurgerPrints.

**Ví dụ thực tế:**
> *Seller:* "Tôi muốn bán 2 áo T-shirt cho thị trường Mỹ, giá vốn dưới $8, ship dưới 5 ngày, chọn xưởng nào, SKU nào?"
> *Agent:* Gọi Catalog API lấy danh sách variants, áp bộ lọc, tính toán vận chuyển cho 2 sản phẩm, xếp hạng theo SLA và trả về bảng so sánh chi tiết giữa các xưởng, kèm gợi ý tạo sandbox order.

---

## ✨ 2. Các tính năng chính

1. **Stateful Conversation (LangGraph):** Quản lý hội thoại đa lượt cô lập theo `session_id`, lưu trữ vết tìm kiếm (last recommendation) để hỗ trợ các câu hỏi bổ sung ngắn (ví dụ: "ship sang CA thì sao?", "bán giá 25 đô").
2. **Dynamic Search & Ranking:** Hỗ trợ lọc theo `color`, `size`, `product_type` ở cấp SKU/variant. Nếu không tìm thấy kết quả khớp hoàn hảo, hệ thống tự động đề xuất các phương án thay thế gần nhất (Nearest Alternatives) kèm chỉ số chênh lệch (`filter_excess`).
3. **Sandbox Order Draft Gating:** Quy trình tạo đơn hàng thử nghiệm qua chat an toàn tuyệt đối. Yêu cầu nhập đầy đủ thông tin giao hàng, hiển thị tóm tắt đơn hàng đã ẩn thông tin cá nhân (PII masking) và chỉ tạo đơn khi nhận được cụm từ xác nhận chính xác.
4. **Market & Seasonal Suggestion:** Đưa ra các câu hỏi gợi ý và xu hướng sản phẩm (niche/design/events) dựa trên quốc gia và tháng lựa chọn (ví dụ: chuẩn bị cho July 4th tại Mỹ).
5. **Dual Intent Detection:** Kết hợp giữa bộ phân tích regex nhanh (rule-based parser) và mô hình ngôn ngữ lớn (LLM classifier) để phân loại ý định chính xác khi câu lệnh mơ hồ.

---

## ⚡ 3. Hướng dẫn cài đặt nhanh (Quick Start)

### Yêu cầu hệ thống
- **Python:** 3.11+
- **Node.js:** 18+ (để chạy frontend)
- **BurgerPrints API Key** (lấy từ cài đặt cửa hàng fulfillment của bạn)

### 3.1. Thiết lập Backend
1. **Clone repository:**
   ```bash
   git clone <repository_url>
   cd BurgerPrintsAgent
   ```
2. **Tạo và kích hoạt môi trường ảo:**
   ```bash
   python -m venv venv
   # Trên Windows (PowerShell):
   .\venv\Scripts\Activate.ps1
   # Trên macOS/Linux:
   source venv/bin/activate
   ```
3. **Cài đặt thư viện:**
   ```bash
   pip install -r requirements.txt
   ```
4. **Cấu hình biến môi trường (`.env`):**
   Tạo file `.env` ở thư mục gốc (xem mẫu ở `.env.example`):
   ```env
   BURGERPRINTS_API_KEY=your_burgerprints_api_key_here
   BURGERPRINTS_API_BASE_URL=https://api.burgerprints.com/v2
   BURGERPRINTS_ENABLE_SANDBOX_CREATE_ORDER=false # Đổi thành true để cho phép tạo đơn sandbox thật
   
   # Cấu hình LLM (Nếu muốn dùng LLM fallback router)
   LLM_INTENT_ENABLED=false
   LLM_API_KEY=your_llm_api_key
   ```
5. **Chạy Backend Server:**
   ```bash
   python -m uvicorn app:app --reload --host 127.0.0.1 --port 8000
   ```
   *Tài liệu Swagger UI sẽ khả dụng tại: `http://localhost:8000/docs`*

### 3.2. Thiết lập Frontend
1. **Di chuyển vào thư mục frontend:**
   ```bash
   cd frontend
   ```
2. **Cài đặt thư viện:**
   ```bash
   npm install
   ```
3. **Khởi chạy Frontend Dev Server:**
   ```bash
   npm run dev
   ```
   *Ứng dụng Web Chat UI sẽ hoạt động tại: `http://localhost:5173`*

### 3.3. Chạy toàn bộ Unit Tests
Dự án có bộ kiểm thử tự động toàn diện (132 test cases) kiểm tra toàn bộ logic parse, normalize, margin, ranking và graph state.
Để chạy tests từ thư mục gốc dự án:
```bash
python -m unittest test_core.py test_agent.py -v
```

---

## 🏗️ 4. Kiến trúc hệ thống & Luồng xử lý

Dự án tuân thủ mô hình kiến trúc phân lớp (6 lớp) để dễ bảo trì và mở rộng:

```
[Lớp API (FastAPI)]  --> Nhận request tại POST /agent/chat
       ↓
[Lớp Service (AgentService, AgentGraph)] --> LangGraph quản lý session state qua session_id
       ↓
[Lớp Orchestration (OrchestratorAgent, IntentAgent, SemanticRouter)] --> Phân loại & định tuyến luồng đi
       ↓
[Lớp Agent (CatalogAgent, OrderAgent, MarketAdviceAgent, AnswerAgent)] --> Thực thi nhiệm vụ chuyên biệt
       ↓
[Lớp Tools & Core (BurgerPrintsTools, Engine, TextParser, Normalizer)] --> Xử lý dữ liệu thô, parse tham số
       ↓
[Lớp Dịch vụ ngoài (BurgerPrintsClient, CatalogApiClient, Ranking, Margin)] --> Giao tiếp API & tính toán
```

### Chi tiết phản hồi API (`/agent/chat`)
Để đảm bảo frontend hoạt động nhất quán, cấu trúc dữ liệu trả về luôn tuân thủ format:
```json
{
  "answer": "Nội dung markdown phản hồi cho seller...",
  "intent": "search_order_items",
  "tool_calls": [{"name": "search_catalog_tool", "params": {...}}],
  "api": {
    "method": "GET",
    "path": "/catalogsV2/list",
    "url": "https://api.burgerprints.com/catalogsV2/list?...",
    "params": {...}
  },
  "params": {
    "country": "US",
    "product_type": "T-shirt",
    "selling_price": 25.0
  },
  "data": {
    "items": [...]
  },
  "notes": [],
  "session_id": "session-uuid-string"
}
```

---

## 🧪 5. Hướng dẫn chạy thử nghiệm (Smoke Tests)

Bạn có thể kiểm tra nhanh hệ thống bằng cách gửi các câu lệnh sau qua cổng chat:

1. **Kiểm tra thông tin tài khoản:**
   - Câu lệnh: `xem balance` hoặc `lấy 3 order mới nhất`
2. **Tìm kiếm sản phẩm & Xếp hạng:**
   - Câu lệnh: `Tôi muốn bán T-shirt ship US dưới $8`
   - *Hệ thống sẽ yêu cầu cung cấp giá bán nếu muốn tính Margin. Bạn có thể chat tiếp: `bán giá 25 đô`*
3. **So sánh xưởng sản xuất:**
   - Câu lệnh: `so sánh giá Hoodie giữa các xưởng đang có, xưởng nào ship US rẻ nhất?`
4. **Đề xuất sản phẩm theo mùa:**
   - Câu lệnh: `Có gợi ý sản phẩm nào cho mùa hè ở Mỹ không?`
5. **Quy trình tạo đơn thử nghiệm (Sandbox Order Draft):**
   - Bước 1: Tìm kiếm một SKU trước.
   - Bước 2: Chat `tạo sandbox order`.
   - Bước 3: Điền các thông tin theo yêu cầu của bot dưới dạng key-value (ví dụ: `shipping_name: John Doe`, `shipping_address1: 123 Main St`, v.v.).
   - Bước 4: Thử chat `ok` hoặc `yes`. *Bot sẽ từ chối tạo đơn và yêu cầu xác nhận chính xác.*
   - Bước 5: Chat `confirm create sandbox order` hoặc `xác nhận tạo sandbox order` để kết thúc quy trình.

---

## 🛡️ 6. Quy tắc an toàn & Bảo mật

- **Không gửi PII thô:** Toàn bộ thông tin cá nhân của người mua (họ tên, địa chỉ, số điện thoại) đều được ẩn/mã hóa (`masked`) trước khi lưu vào metadata đơn hàng hoặc hiển thị trên luồng chat.
- **Bảo vệ tạo đơn thật:** Hành động `POST /v2/order` bị chặn mặc định ở chế độ production để tránh tạo đơn ảo tốn chi phí. Việc tạo đơn chỉ được kích hoạt khi biến môi trường `BURGERPRINTS_ENABLE_SANDBOX_CREATE_ORDER=true` được cấu hình.
- **Bảo vệ Secret Keys:** Tuyệt đối không commit file `.env` chứa API Key lên các kho lưu trữ công khai.

---

## 📁 7. Cấu trúc thư mục dự án

Dưới đây là cấu trúc các tệp nguồn chính được đẩy lên kho lưu trữ Git:

```
BurgerPrintsAgent/
├── README.md                 # Tài liệu hướng dẫn sử dụng này
├── requirements.txt          # Thư viện Python phụ thuộc
│
├── src/                      # Mã nguồn Python Backend
│   ├── main.py               # FastAPI application entrypoint
│   ├── api/                  # Lớp Routing & API Schemas
│   ├── core/                 # Bộ máy xử lý trung tâm (Engine, Parser, Normalizer)
│   ├── services/             # API Clients (BurgerPrints & Catalog) & Logic Rank/Margin
│   └── agent/                # Cấu trúc Multi-Agent & LangGraph orchestration
│       ├── agents/           # Định nghĩa các Agent chuyên biệt
│       └── tools/            # Công cụ đăng ký để Agent gọi
│
└── frontend/                 # Mã nguồn Frontend (loại trừ node_modules/ và dist/)
    ├── src/
    │   ├── App.tsx           # Thành phần chính chứa Chat UI & Order Draft Panel
    │   ├── api/agent.ts      # HTTP Client kết nối tới backend
    │   └── styles/styles.css # Thiết kế giao diện (UI Tokens)
    ├── vite.config.ts        # Cấu hình Vite
    └── package.json          # Script chạy & các dependencies frontend
```

---

## 🔨 8. Đóng góp & Phát triển tính năng mới

Khi phát triển tính năng mới, vui lòng tuân thủ quy trình kiểm thử nghiêm ngặt:
1. Đọc kỹ file `docs/development_plan.md` để nắm rõ ràng các ràng buộc.
2. Viết unit tests bổ sung vào `test_core.py` hoặc `test_agent.py` trước khi sửa mã nguồn (TDD).
3. Đảm bảo chạy lệnh kiểm thử thành công:
   ```bash
   python -m unittest discover -s . -p "test*.py"
   ```
4. Không thay đổi cấu trúc dữ liệu trả về (`response shape`) của API chat để tránh làm hỏng hiển thị của frontend.
5. Luôn mask PII và kiểm soát gating an toàn đối với các API làm thay đổi trạng thái hệ thống.
