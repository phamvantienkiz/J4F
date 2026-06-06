# BÁO CÁO TRIỂN KHAI PHÂN HỆ BACKEND VÀ AI: BURGERPRINTS AGENT

Báo cáo này tóm tắt chi tiết các thành phần, cấu trúc và kết quả triển khai thực tế của phân hệ **Backend (FastAPI)** và **AI (LangGraph Agent & Pricing Engine)** cho dự án **BurgerPrints Agent** (Trợ lý Danh mục sản phẩm POD) trong Phase hiện tại.

---

## 1. Tổng Quan Kỹ Thuật (Technical Overview)

Toàn bộ mã nguồn được triển khai trong thư mục [Product/](file:///E:/Hackathon2026/J4F/Product) tuân thủ cấu trúc Clean Architecture và được quản lý hiệu quả bằng trình quản lý gói hiện đại `uv`.

- **Môi trường:** Python 3.12, được đồng bộ hóa môi trường ảo thông qua `uv sync`.
- **Backend Framework:** FastAPI (Async) hỗ trợ sinh tài liệu Swagger UI tự động tại `/docs`.
- **AI State Machine:** LangGraph hỗ trợ quản lý trạng thái đa bước (Stateful Multi-turn Chat) và phục hồi ngữ cảnh bằng checkpointer SQLite.
- **Relational DB:** SQLite kết hợp SQLAlchemy ORM (Async Engine và Session).
- **Vector DB:** ChromaDB (Local Persistent) kết hợp Gemini Embeddings (`text-embedding-004`) cho bộ nhớ hồi tưởng (Semantic Recall Memory).

---

## 2. Chi Tiết Các Thành Phần Đã Triển Khai (Components Implemented)

### 2.1. Quản lý Môi trường & Dependency
- File cấu hình [pyproject.toml](file:///E:/Hackathon2026/J4F/Product/pyproject.toml) định nghĩa các gói thư viện chuẩn xác bao gồm `fastapi`, `uvicorn`, `sqlalchemy`, `aiosqlite`, `langgraph`, `chromadb`, `google-genai`, `email-validator`, `bcrypt`, và `pytest`.

### 2.2. Cơ Sở Dữ Liệu Quan Hệ (Relational Database)
- Cấu hình session và engine bất đồng bộ được đặt tại [session.py](file:///E:/Hackathon2026/J4F/Product/backend/app/db/session.py).
- File khai báo metadata gộp [base.py](file:///E:/Hackathon2026/J4F/Product/backend/app/db/base.py) giúp tự động liên kết các bảng.
- Script khởi tạo bảng [init_db.py](file:///E:/Hackathon2026/J4F/Product/backend/app/db/init_db.py) thực thi đồng bộ schema.
- Các models ORM chi tiết được triển khai tại:
  - [user.py](file:///E:/Hackathon2026/J4F/Product/backend/app/models/user.py) - Bảng `users` quản lý tài khoản seller.
  - [preference.py](file:///E:/Hackathon2026/J4F/Product/backend/app/models/preference.py) - Bảng `user_preferences` ghi nhớ cấu hình mặc định (market, target margin, shipping SLA, priority).
  - [conversation.py](file:///E:/Hackathon2026/J4F/Product/backend/app/models/conversation.py) - Bảng `conversations` tương đương với các `thread_id` quản lý phiên trò chuyện.
  - [message.py](file:///E:/Hackathon2026/J4F/Product/backend/app/models/message.py) - Bảng `messages` lưu lịch sử hội thoại chi tiết kèm JSON metadata cho các bảng so sánh.
  - [order.py](file:///E:/Hackathon2026/J4F/Product/backend/app/models/order.py) - Bảng `order_history` lưu các đơn hàng được đẩy qua API thành công.

### 2.3. Semantic Chat Memory (Vector RAG)
- Triển khai tại [vector_rag.py](file:///E:/Hackathon2026/J4F/Product/ai/vector_rag.py).
- Hỗ trợ hàm `index_message` lưu trữ vector nhúng tin nhắn mới nhất.
- Hỗ trợ hàm `recall_context` tìm kiếm ngữ cảnh trò chuyện cũ tương tự của Seller, tự động điền các tham số còn thiếu mà không cần Seller nhắc lại nhiều lần.
- Có cơ chế fallback dùng vector 0 nếu `GEMINI_API_KEY` chưa được thiết lập.

### 2.4. BurgerPrints Tools & Pricing Engine
- **Client API Wrapper:** Triển khai tại [tools.py](file:///E:/Hackathon2026/J4F/Product/ai/tools.py) bao gồm các chức năng `search_catalog`, `get_factory_quotes`, `get_shipping_options`, và `create_order`. Tích hợp chế độ dự phòng đọc từ [mock_data.json](file:///E:/Hackathon2026/J4F/Product/ai/data/mock_data.json) khi bật `USE_MOCK_API=true` để phục vụ demo mượt mà.
- **Pricing Engine:** Triển khai tại [pricing_engine.py](file:///E:/Hackathon2026/J4F/Product/ai/pricing_engine.py). Tính toán chính xác landed cost (Base + Print + Ship + Tax), margin và rủi ro trễ hẹn SLA (`sla_risk_score`) dựa trên địa lý/khoảng cách vận chuyển.

### 2.5. LangGraph Agent Workflow
- Định nghĩa cấu trúc Agent State tại [state.py](file:///E:/Hackathon2026/J4F/Product/ai/state.py).
- Triển khai các nodes xử lý tại [nodes.py](file:///E:/Hackathon2026/J4F/Product/ai/nodes.py):
  1. `extract_intent_node` (Sử dụng Gemini structured output để bóc tách slots).
  2. `clarify_node` (Yêu cầu làm rõ nếu thiếu thông tin bắt buộc).
  3. `retrieve_catalog_node` (Gọi API tìm kiếm phôi và danh sách nhà in).
  4. `calculate_pricing_node` (Gọi pricing engine tính toán landed cost).
  5. `rank_and_recommend_node` (Tự động xếp hạng và tạo bảng so sánh trade-offs trực quan).
  6. `execute_order_node` (Human-in-the-loop để tạo đơn hàng chính thức).
- Lắp ghép sơ đồ chuyển dịch trạng thái có điều kiện (conditional routing) và persistence checkpointer SQLite tại [agent.py](file:///E:/Hackathon2026/J4F/Product/ai/agent.py).

### 2.6. REST API Gateway Endpoints & Services
- Tách biệt logic API Gateway với các router tại:
  - [deps.py](file:///E:/Hackathon2026/J4F/Product/backend/app/api/deps.py) (Inject Database Session và Auth Middleware).
  - [auth.py](file:///E:/Hackathon2026/J4F/Product/backend/app/api/v1/auth.py) (Đăng ký, Đăng nhập, Profile, Preference).
  - [chat.py](file:///E:/Hackathon2026/J4F/Product/backend/app/api/v1/chat.py) (Phiên chat, Lịch sử chat, và gửi tin nhắn kích hoạt Agent).
  - [order.py](file:///E:/Hackathon2026/J4F/Product/backend/app/api/v1/order.py) (Xác nhận đẩy đơn và tra cứu tracking thời gian thực).
- Các lớp service điều phối dữ liệu: [auth_service.py](file:///E:/Hackathon2026/J4F/Product/backend/app/services/auth_service.py), [chat_service.py](file:///E:/Hackathon2026/J4F/Product/backend/app/services/chat_service.py), và [order_service.py](file:///E:/Hackathon2026/J4F/Product/backend/app/services/order_service.py).
- Điểm khởi chạy API Gateway: [main.py](file:///E:/Hackathon2026/J4F/Product/backend/main.py).

### 2.7. Đóng Gói
- File [Dockerfile.backend](file:///E:/Hackathon2026/J4F/Product/Dockerfile.backend) và [docker-compose.yml](file:///E:/Hackathon2026/J4F/Product/docker-compose.yml) được chuẩn bị sẵn sàng cho việc đóng gói ứng dụng.

---

## 3. Báo Cáo Kiểm Thử (Testing & Verification Report)

Hệ thống đã được kiểm thử toàn diện thông qua bộ thư viện `pytest` và đạt kết quả **100% thành công (13/13 tests passed)**.

### 3.1. Danh Sách Các Bài Test Đã Thực Thi
1. **Kiểm thử Pricing Engine** ([test_pricing.py](file:///E:/Hackathon2026/J4F/Product/tests/test_pricing.py)):
   - `test_calculate_landed_cost_us`: Kiểm tra công thức landed cost và thuế 8% tại thị trường Mỹ.
   - `test_calculate_landed_cost_eu`: Kiểm tra công thức landed cost và thuế 19% tại thị trường châu Âu.
   - `test_calculate_margin`: Kiểm tra tính toán margin % từ giá bán.
   - `test_suggest_retail_price`: Kiểm tra đề xuất giá bán lẻ dựa trên target margin.
   - `test_calculate_sla_risk`: Kiểm tra thuật toán chấm điểm rủi ro giao hàng trễ hẹn.
2. **Kiểm thử Workflow Agent** ([test_agent.py](file:///E:/Hackathon2026/J4F/Product/tests/test_agent.py)):
   - `test_agent_clarify_flow`: Kiểm tra đồ thị chuyển tiếp đúng sang node `clarify_node` khi thiếu các tham số lọc cốt lõi.
   - `test_agent_retrieve_flow`: Kiểm tra đồ thị chạy xuyên suốt từ extraction, retrieval, pricing sang node recommendation thành công khi đầy đủ tham số.
3. **Kiểm thử Security** ([test_security.py](file:///E:/Hackathon2026/J4F/Product/tests/test_security.py)):
   - `test_password_hashing`: Kiểm tra mã hóa mật khẩu và khớp chuỗi băm trực tiếp qua gói `bcrypt`.
   - `test_jwt_tokens`: Kiểm tra tạo và giải mã JWT Token phục vụ phân quyền.
   - `test_jwt_invalid_token`: Kiểm tra từ chối các token không hợp lệ.
4. **Kiểm thử Tích hợp API Gateway** ([test_api.py](file:///E:/Hackathon2026/J4F/Product/tests/test_api.py)):
   - `test_root_endpoint`: Kiểm tra trạng thái hoạt động của cổng Gateway `/`.
   - `test_auth_workflow`: Kiểm tra chuỗi API Đăng ký -> Đăng nhập -> Lấy thông tin -> Cập nhật cài đặt sở thích.
   - `test_chat_workflow`: Kiểm tra chuỗi API Tạo chat -> Gửi tin nhắn tư vấn và nhận phản hồi chi tiết từ Agent.

### 3.2. Kết quả pytest thực tế
```bash
E:\Hackathon2026\J4F\Product> uv run python -m pytest
============================= test session starts =============================
platform win32 -- Python 3.12.3, pytest-9.0.3, pluggy-1.6.0
rootdir: E:\Hackathon2026\J4F\Product
configfile: pyproject.toml
plugins: anyio-4.13.0, langsmith-0.8.9, asyncio-1.4.0
collected 13 items

tests\test_agent.py ..                                                   [ 15%]
tests\test_api.py ...                                                    [ 38%]
tests\test_pricing.py .....                                              [ 76%]
tests\test_security.py ...                                               [100%]

======================= 13 passed, 10 warnings in 3.22s =======================
```

---

## 4. Hướng Dẫn Vận Hành Trực Tiếp (Direct Execution Guide)

Trong trường hợp không dùng Docker, ban giám khảo/người dùng có thể chạy trực tiếp phân hệ Backend như sau:

1. **Cài đặt thư viện:**
   ```bash
   cd Product
   uv sync
   ```
2. **Khởi tạo database:**
   ```bash
   uv run python backend/app/db/init_db.py
   ```
3. **Chạy server FastAPI:**
   ```bash
   uv run uvicorn backend.main:app --host 0.0.0.0 --port 8000 --reload
   ```
   *Truy cập [http://localhost:8000/docs](http://localhost:8000/docs) để thực hiện test API trực tiếp.*
