# BACKEND AND AI IMPLEMENTATION PLAN: BURGERPRINTS AGENT

Tài liệu này đặc tả chi tiết kế hoạch triển khai (Implementation Plan) cho phân hệ **Backend (FastAPI)** và **AI (LangGraph Agent & Pricing Engine)** của hệ thống **BurgerPrints Agent** (Trợ lý Danh mục POD). Kế hoạch này được thiết kế để hoàn thành trong 3 ngày của Hackathon, tuân thủ các tài liệu kiến trúc, đặc tả NLU/đồ thị, đặc tả cơ sở dữ liệu và kế hoạch kiểm thử hiện có.

---

## 1. Mục Tiêu Triển Khai (Implementation Objectives)

1. **Quản lý Môi trường Hiện đại (uv & pyproject.toml):** Sử dụng `uv` làm trình quản lý gói để đảm bảo tốc độ cài đặt tối đa và dễ dàng setup trong vòng dưới 10 phút trên máy giám khảo.
2. **Cấu trúc Clean Architecture:** Tổ chức code trong thư mục `@Product/` tách biệt rõ ràng giữa `backend` và `ai` theo đặc tả layout.
3. **Độc lập và Tin cậy tuyệt đối:** 
   - **Pricing Engine:** Thực hiện tính toán tài chính hoàn toàn bằng Python, loại bỏ rủi ro ảo giác LLM.
   - **Mock API Fallback:** Tích hợp sẵn cơ chế Mock dữ liệu khi `USE_MOCK_API=true` để phục vụ demo mượt mà nếu API ngoài gặp sự cố, nhưng luôn ưu tiên gọi BurgerPrints API thật khi chạy thực tế.
4. **Kiểm thử liên tục (Verification Loop):** Mỗi bước triển khai đều đi kèm chỉ dẫn kiểm thử và các kịch bản test tương ứng.

---

## 2. Bản đồ Thư mục & Phân chia Trách nhiệm

Toàn bộ mã nguồn sẽ nằm trong thư mục `@Product/` được tổ chức như sau:

```
@Product/
├── pyproject.toml            # Quản lý dependency toàn cục cho dự án (FastAPI & AI)
├── docker-compose.yml        # Docker Compose khởi chạy Backend
├── Dockerfile.backend        # Dockerfile đóng gói FastAPI & LangGraph
├── .env.example              # Mẫu cấu hình môi trường (.env thực tế không commit)
│
├── backend/                  # Phân hệ API Gateway & Web Services
│   ├── main.py               # Điểm chạy Uvicorn chính của FastAPI
│   └── app/
│       ├── api/              # Cổng kết nối REST Endpoints
│       │   ├── deps.py       # Dependency Injection (Auth, DB session)
│       │   └── v1/
│       │       ├── auth.py   # API đăng ký, đăng nhập
│       │       ├── chat.py   # API hội thoại, lấy lịch sử chat
│       │       └── order.py  # API tạo đơn, tra cứu đơn
│       ├── core/             # Cấu hình hệ thống (config, security)
│       ├── db/               # SQLAlchemy Session & DB helpers
│       ├── models/           # SQLAlchemy ORM Models
│       ├── schemas/          # Pydantic validation schemas
│       └── services/         # Nghiệp vụ logic (Auth, Chat, Order)
│
└── ai/                       # Phân hệ Agent & Công cụ tính toán
    ├── agent.py              # Xây dựng LangGraph Workflow
    ├── state.py              # Cấu trúc AgentState (TypedDict)
    ├── nodes.py              # Logic xử lý của các Node trong Đồ thị
    ├── tools.py              # BurgerPrints API Client Wrapper (Mock & Real)
    ├── pricing_engine.py     # Bộ công cụ tính toán Landed Cost & Margin
    ├── vector_rag.py         # Quản lý ChromaDB Semantic Chat Memory
    └── data/                 # Thư mục chứa sqlite.db và ChromaDB index
```

---

## 3. Lộ trình Triển khai Chi tiết (Phase-by-Phase Roadmap)

### Giai đoạn 1: Môi trường & Khởi tạo Cấu trúc (Day 1 - Sáng)
* **Tác vụ 1:** Khởi tạo môi trường ảo Python bằng `uv venv`.
* **Tác vụ 2:** Xây dựng file `pyproject.toml` khai báo các thư viện:
  - Backend: `fastapi`, `uvicorn`, `pydantic`, `pydantic-settings`, `sqlalchemy`, `python-jose[cryptography]`, `passlib[bcrypt]`
  - AI: `langgraph`, `langchain-google-genai`, `chromadb`, `httpx`
  - Testing & Dev: `pytest`, `pytest-asyncio`
* **Tác vụ 3:** Tạo bộ khung thư mục rỗng cho `Product/backend/` và `Product/ai/`.

### Giai đoạn 2: Cơ sở Dữ liệu & Semantic Memory (Day 1 - Chiều)
* **Tác vụ 4:** Thiết kế SQLAlchemy Models cho 5 bảng SQLite:
  - `User`: Quản lý tài khoản seller.
  - `UserPreference`: Lưu sở thích lâu dài (thị trường, margin mục tiêu, ship SLA).
  - `Conversation`: Phiên chat (thread_id).
  - `Message`: Lưu lịch sử chat, hỗ trợ lưu JSON metadata cho bảng so sánh.
  - `OrderHistory`: Lưu đơn hàng đã được tạo thành công trên BurgerPrints.
* **Tác vụ 5:** Phát triển pipeline ChromaDB (`vector_rag.py`) lưu trữ và truy hồi lịch sử chat ngữ nghĩa (Semantic Recall) sử dụng Gemini Embeddings (`text-embedding-004`).

### Giai đoạn 3: BurgerPrints API & Pricing Engine (Day 2 - Sáng)
* **Tác vụ 6:** Xây dựng `Product/ai/tools.py` đóng gói BurgerPrints API v2.0 Client:
  - `search_catalog(query, category)`: Tìm kiếm sản phẩm lấy `product_id`.
  - `get_factory_quotes(product_id, variant_id, market)`: Lấy báo giá thô từ các xưởng.
  - `get_shipping_options(origin_factory_id, destination_country, zip_code)`: Ước tính cước vận chuyển.
  - `create_order(...)`: Gửi payload tạo đơn (Scenario 1 của Create Order sử dụng catalog SKU).
  - *Fallback:* Tích hợp dữ liệu JSON Mock chất lượng cao đọc từ file cục bộ khi `USE_MOCK_API=true`.
* **Tác vụ 7:** Phát triển `Product/ai/pricing_engine.py` tính toán deterministic:
  - Tính Landed Cost = Base Cost + Printing Cost + Shipping Cost + Tax.
  - Tính Margin Percentage dựa trên giá bán hoặc tự động đề xuất.
  - Đánh giá chỉ số rủi ro vận chuyển SLA.

### Giai đoạn 4: LangGraph Agent Engine (Day 2 - Chiều)
* **Tác vụ 8:** Định nghĩa `AgentState` trong `Product/ai/state.py`.
* **Tác vụ 9:** Lập trình các nodes trong `Product/ai/nodes.py`:
  - `extract_intent_node`: Gọi Gemini API structured output bóc tách slots.
  - `clarify_node`: Sinh câu hỏi làm rõ nếu thiếu `product_type` hoặc `market`.
  - `retrieve_catalog_node`: Gọi API wrapper lấy candidates.
  - `calculate_pricing_node`: Gọi Pricing Engine tính toán landed cost.
  - `rank_and_recommend_node`: Xếp hạng scoring và dùng Gemini sinh giải trình.
  - `execute_order_node`: Gọi API tạo đơn (Human-in-the-loop).
* **Tác vụ 10:** Liên kết đồ thị trong `Product/ai/agent.py` và cấu hình bộ nhớ SqliteSaver checkpoint.

### Giai đoạn 5: FastAPI Gateway & Service Integration (Day 3 - Sáng)
* **Tác vụ 11:** Thiết lập core config, CORS và các middleware bảo mật.
* **Tác vụ 12:** Lập trình REST endpoints:
  - `/api/v1/auth/register` & `/api/v1/auth/login`: Xác thực seller và cấp JWT.
  - `/api/v1/chat/message`: Gửi câu hỏi chat, điều phối luồng LangGraph và khôi phục trạng thái bằng `thread_id`.
  - `/api/v1/chat/history`: Lấy lịch sử chat hiển thị lại.
  - `/api/v1/order/confirm`: Endpoint xác nhận chốt tạo đơn hàng thực tế.
* **Tác vụ 13:** Viết lớp nghiệp vụ `chat_service.py` và `order_service.py` để kết nối API endpoints với các xử lý SQLite/ChromaDB.

### Giai đoạn 6: Đóng gói Docker & Kiểm thử Toàn diện (Day 3 - Chiều)
* **Tác vụ 14:** Cấu hình `Dockerfile.backend` và `docker-compose.yml` để đóng gói độc lập.
* **Tác vụ 15:** Viết các unit tests bằng `pytest` cho Pricing Engine, database migration và API routes. Thực thi kiểm thử đầu cuối để nghiệm thu sản phẩm.

---

## 4. Đặc tả Quy trình Kiểm thử & Nghiệm thu (Verification Checklist)

Để đảm bảo chất lượng Staff Engineer, các tiêu chí sau phải được kiểm tra trước khi bàn giao:

| Thành phần | Phương pháp xác thực | Kết quả mong đợi |
| :--- | :--- | :--- |
| **Môi trường & Package** | Chạy `uv sync` | Không xung đột package, cài đặt hoàn tất dưới 3 phút |
| **Cơ sở dữ liệu** | Run script khởi tạo DB | Tạo thành công file `sqlite.db` với đầy đủ schema 5 bảng |
| **ChromaDB** | Thực hiện nhúng thử 1 đoạn chat | Vector 768 chiều được lập chỉ mục và truy hồi thành công |
| **Pricing Engine** | `pytest test_pricing.py` | Kết quả chính xác 100%, không bị sai lệch số float |
| **BurgerPrints Wrapper** | Gọi mock & real endpoints | Lấy đúng thông tin SKU và tạo đơn hàng nháp thành công |
| **LangGraph Agent** | Gửi tin nhắn test thông qua đồ thị | Chuyển dịch trạng thái đúng logic, hỏi lại khi thiếu slots |
| **FastAPI REST API** | Truy cập `/docs` | Swagger hiển thị đầy đủ endpoints và cho phép test trực quan |
| **Docker Compose** | `docker compose up --build -d` | Build thành công, service backend khởi chạy trên port 8000 |

---

## 5. Kịch bản Mock Data Dự phòng (Mock API Schema)

Để hỗ trợ việc demo suôn sẻ trong trường hợp API BurgerPrints bị lỗi kết nối, hệ thống sẽ chuẩn bị sẵn các bộ Mock Data tĩnh tại file `Product/ai/data/mock_data.json` bao gồm:
1. **Catalog Search Mock:** Trả về danh sách phôi áo T-Shirt, Hoodie và Cốc sứ phổ biến.
2. **Factory Quotes Mock:** Báo giá từ ít nhất 3 xưởng (1 xưởng US, 1 xưởng EU, 1 xưởng VN) cho từng dòng sản phẩm để làm nổi bật tính năng so sánh địa lý.
3. **Shipping Options Mock:** Chi phí và thời gian giao hàng thực tế từ các xưởng trên tới Mỹ, Châu Âu và Việt Nam.
4. **Order Creation Mock:** Trả về mã đơn dạng `bp_ord_mock_12345` kèm theo tóm tắt tài chính và trạng thái `pending`.
