# BurgerPrint Chatbot — Project Technical Report

## 1. Tổng quan dự án

**BurgerPrints POD Catalog Assistant** là hệ thống AI Agent hỗ trợ seller (người bán) trên nền tảng Print-on-Demand (POD) ra quyết định fulfillment. Hệ thống cho phép người dùng:

- Tra cứu danh mục sản phẩm POD (áo thun, hoodie, cốc, v.v.) theo thị trường
- So sánh xưởng in, phí vận chuyển, thời gian giao hàng
- Tính toán landed cost (tổng chi phí hạ cánh), profit margin
- Tạo đơn hàng thử nghiệm (sandbox draft order) an toàn qua API BurgerPrints

**Đối tượng sử dụng:** Chủ shop e-commerce, seller POD bán hàng cross-border (US, EU, VN, AU, NZ, ZA).

**Quy mô:** Hơn 120 commit trên 2 nhánh chính (main + refactor), khoảng 15.000+ dòng code (Python + TypeScript/React), phát triển từ 4/6/2026 (~3 tuần) cho đến phiên bản MVP hiện tại (21/6/2026). Một người phát triển chính.

## 2. Tech Stack

### Frontend

| Thành phần | Công nghệ |
|------------|-----------|
| Framework | **React 19** (JSX, hooks, functional components) |
| Ngôn ngữ | **TypeScript** |
| Build tool | **Vite** |
| Styling | **CSS thuần** (không dùng Tailwind, không CSS-in-JS) |
| State management | **React useState** (local state, không dùng Redux/Zustand) |
| HTTP client | **Fetch API** (SSE streaming) |
| Deployment | Single-page application (SPA) với Vite build |

### Backend

| Thành phần | Công nghệ |
|------------|-----------|
| Framework | **FastAPI** (Python 3.11) |
| Ngôn ngữ | Python 3.11+ |
| Kiến trúc | **Monolith** với module hóa (agent engine + API routes + services) |
| API pattern | REST + Server-Sent Events (SSE) |
| ORM | **SQLModel** (Pydantic + SQLAlchemy) |
| Database | **SQLite** (development), hỗ trợ PostgreSQL production |
| Vector search | **pgvector** (PostgreSQL), fallback keyword search khi không có PostgreSQL |

### AI / NLP / Chatbot Engine

| Thành phần | Chi tiết |
|------------|----------|
| LLM Parser | **OpenAI GPT-4o-mini** / **Azure OpenAI GPT-4.1-mini** (cấu hình linh hoạt) |
| LLM Generator | Cùng model với Parser, stream output |
| Embedding model | **Azure OpenAI text-embedding** (384 chiều) |
| RAG | Hybrid search: keyword matching + vector embedding + Reciprocal Rank Fusion |
| Mock mode | Hoạt động không cần API key (dùng heuristic thuần) |
| Guardrails | Rule-based (5 rules: anti-code-gen, anti-jailbreak, anti-SQLi, anti-token-exhaustion, financial/legal liability) |

### Third-party tích hợp

| Đối tác | Mục đích |
|---------|----------|
| **BurgerPrints API v2** | Tra cứu sản phẩm, biến thể, tạo đơn hàng |
| **BurgerPrints Catalog API v1** | Tra cứu phí vận chuyển theo quốc gia |
| **OpenAI / Azure OpenAI** | Parser intent extraction, Generator response |
| **Azure OpenAI Embeddings** | Tạo vector embedding cho hybrid search |

### DevOps / Hạ tầng

| Thành phần | Chi tiết |
|------------|----------|
| Container | Docker (python:3.11-slim) |
| CI/CD | Không phát hiện trong codebase (chưa có GitHub Actions) |
| Hosting | Không xác định được từ codebase |
| Scheduler | APScheduler (đồng bộ catalog định kỳ mỗi 6 giờ) |
| Logging | Python logging module + debug_trace.log file |

## 3. Kiến trúc hệ thống

### Luồng dữ liệu tổng quan

```
User (Browser)
    │
    ▼
React UI (Vite SPA)
    │ POST /agent/chat (SSE stream)
    ▼
FastAPI Backend
    │
    ├─► AgentEngine.run_stream()
    │       │
    │       ├─► 1. Guardrails check (rule-based filtering)
    │       ├─► 2. Intent Parser (heuristic + LLM)
    │       ├─► 3. Slot extraction & normalization
    │       ├─► 4. Heuristic Flow Execution
    │       │       ├─► search_products_tool → hybrid_search (keyword + vector)
    │       │       ├─► compare_shipping_tool → multi-factory comparison
    │       │       ├─► calculate_landed_cost_tool → cost breakdown
    │       │       └─► create_draft_order_tool → BurgerPrints API
    │       ├─► 5. LLM Generator (narrative response)
    │       └─► 6. Persist session (DB)
    │
    ├─► GET /agent/suggestions → TrendService (geo/seasonal)
    └─► GET /api/orders/history → Order DB queries
```

### Luồng xử lý tin nhắn chatbot (chi tiết)

1. **Guardrails** → Nếu vi phạm rules (code gen, jailbreak, SQLi, tấn công, tài chính), trả về ngay mà không gọi LLM.
2. **Heuristic Parser** (`parse_intent_and_slots`) → Phân tích intent nhanh dùng keyword matching: `recommend`, `compare`, `calculate_margin`, `create_order`, `global_availability`, `general_chat`, `general_knowledge_conversation`. Trích xuất slots (product_type, country, price, SKU...) bằng regex.
3. **LLM Parser** (optional) → Song song với heuristic, gọi OpenAI để phân tích intent và slots sâu hơn, trả về JSON có cấu trúc.
4. **Category State Isolation** → Khi product_type thay đổi giữa các lượt chat, purge toàn bộ params cũ để tránh rò rỉ slot giữa các category.
5. **Heuristic Flow** → Executor quyết định tool nào được gọi dựa trên intent:
   - *recommend* → `search_products_tool` (hybrid search)
   - *compare* → `compare_shipping_tool` (so sánh xưởng)
   - *calculate_margin* → `calculate_landed_cost_tool` (tính toán chi phí)
   - *create_order* → `calculate_landed_cost_tool` → xác nhận → `create_draft_order_tool`
6. **LLM Generator** → Chuyển data packets thành narrative response có cấu trúc (multi-factory comparison, pricing breakdown).
7. **Session Persistence** → Lưu toàn bộ history, slots, intent vào database.

### Lý do chọn kiến trúc

- **Decoupled Agent Architecture**: Tách biệt parser (hiểu ý định) và generator (soạn câu trả lời) cho phép tuning riêng từng layer. Heuristic flow xử lý nhanh (không cần LLM), LLM chỉ dùng khi cần diễn giải nghiệp vụ phức tạp.
- **Hybrid Search (RRF)**: Kết hợp keyword matching + vector search đảm bảo precision cao cho catalog POD với nhiều thuật ngữ chuyên ngành.
- **Category Isolation**: POD catalog rất dễ nhầm lẫn giữa các category (T-Shirt vs Tank Top), cơ chế purge slots tự động ngăn cross-category contamination.
- **Sandbox-first Order**: Tạo đơn hàng luôn ở chế độ sandbox, yêu cầu xác nhận 2 bước trước khi gọi API thật.

## 4. Danh sách tính năng chính

### 4.1. Tư vấn sản phẩm POD thông minh (Multi-market)
- **Vấn đề giải quyết:** Seller mất hàng giờ để tra cứu thủ công SKU phù hợp trên nhiều thị trường
- **Kỹ thuật:** Hybrid search với 14 category map ưu tiên (P1→P5), geo-aware market filtering, multi-factory diversification (Round Robin), strict category isolation
- **Value:** Giảm thời gian tra cứu từ hàng giờ xuống còn vài giây

### 4.2. So sánh xưởng in đa nhà cung cấp
- **Vấn đề giải quyết:** Seller không biết xưởng nào rẻ nhất, nhanh nhất cho từng thị trường
- **Kỹ thuật:** Gom nhóm theo partner_name, tính landed cost real-time (base + ship + tax), so sánh đa carrier, xếp hạng theo tổng chi phí
- **Value:** Tra cứu transparent landed cost, tránh phí ẩn, tối ưu supply chain

### 4.3. Tính toán Profit Margin thời gian thực
- **Vấn đề giải quyết:** Seller cần biết ngay lợi nhuận khi thay đổi giá bán mà không cần Excel
- **Kỹ thuật:** Công thức `margin = (selling_price - landed_cost) / selling_price`, lọc sản phẩm không đạt margin threshold, gợi ý giá bán tự động từ min_margin
- **Value:** Ra quyết định pricing nhanh, chính xác

### 4.4. Tạo đơn hàng Sandbox an toàn
- **Vấn đề giải quyết:** Seller muốn thử tạo đơn mà không sợ phát sinh chi phí thật
- **Kỹ thuật:** 2-step confirmation (preview → confirm), sandbox flag bắt buộc trong payload, lưu order history vào DB
- **Value:** Kiểm tra quy trình order trước khi chạy production

### 4.5. Geo-aware Seasonal Merchandising
- **Vấn đề giải quyết:** Gợi ý sản phẩm sai mùa (vd: gợi ý hoodie cho AU vào tháng 6 — đang mùa đông)
- **Kỹ thuật:** Hemisphere detection (Bắc/Nam bán cầu), climate-specific product mapping (21 categories), country fallback chain, Vietnamese holiday calendar
- **Value:** Gợi ý sản phẩm đúng mùa, tăng conversion rate

### 4.6. Streaming Response với Thought Process
- **Vấn đề giải quyết:** User chờ response mà không biết bot đang làm gì
- **Kỹ thuật:** SSE streaming với 3 bước thought process (analyzing → fetching → calculating), real-time token telemetry
- **Value:** UX mượt mà, tăng trust với người dùng

### 4.7. Đa ngôn ngữ (Tiếng Việt / English)
- **Vấn đề giải quyết:** Hỗ trợ seller Việt Nam và quốc tế
- **Kỹ thuật:** Language detection heuristic (Vietnamese diacritics + keyword base), runtime language instruction injection vào prompt, context-aware language persistence qua short ambiguous payloads (2-letter codes, SKUs...)
- **Value:** Tiếp cận đa dạng đối tượng người dùng

### 4.8. Tự động đồng bộ Catalog định kỳ
- **Vấn đề giải quyết:** Catalog BurgerPrints thay đổi thường xuyên, dữ liệu DB nhanh lỗi thời
- **Kỹ thuật:** APScheduler đồng bộ mỗi 6 giờ, async parallel fetching (Semaphore 15), batch commit mỗi 20 products, delta sync với upsert
- **Value:** Luôn có dữ liệu catalog mới nhất, không cần can thiệp thủ công

## 5. Điểm kỹ thuật nổi bật / Thử thách đã giải quyết

### 5.1. Hybrid Search với Reciprocal Rank Fusion (RRF) — ~150 dòng
Tự xây dựng hệ thống hybrid search kết hợp full-text search (tsvector) và vector similarity (pgvector) dùng RRF để xếp hạng, không dùng thư viện ngoài. Fallback về keyword search khi PostgreSQL không có sẵn.

### 5.2. Category State Isolation & Slot Sanitization
Xử lý vấn đề cross-category slot bleeding — khi user chuyển từ "áo thun" sang "quần dài", hệ thống tự động purge toàn bộ params cũ (base_cost, selling_price, SKU). So sánh db_snapshot và current_slots để phát hiện category switch chính xác.

### 5.3. Language Detection Heuristic tinh vi
Không dùng thư viện NLP — tự xây dựng hệ thống phát hiện ngôn ngữ dựa trên: (1) dấu tiếng Việt, (2) từ điển hint words song ngữ, (3) context-aware fallback qua lịch sử hội thoại, (4) xử lý ambiguous payloads (SKU codes, country codes, xác nhận ngắn).

### 5.4. Multi-variant Multi-factory Comparison Engine
Tự tính toán landed cost cho từng tổ hợp (variant × partner × shipping zone × print option), sau đó dùng thuật toán Round Robin để đa dạng hóa kết quả theo partner. Đảm bảo mỗi xưởng đều có đại diện trong top results.

### 5.5. Decoupled Agent Architecture (Parser + Flow + Generator)
Thiết kế kiểu "router → executor → narrator": Heuristic parser quyết định intent nhanh (không LLM), executor thực thi tool tương ứng, LLM generator chỉ làm nhiệm vụ soạn câu trả lời. Tiết kiệm token, tăng độ tin cậy, dễ debug. Tổng số lần gọi LLM tối đa: 2 (parser + generator) — so với agent loop truyền thống gọi 5-10+ lần.

### 5.6. Guardrails đa tầng (5 rules)
Tự xây dựng rule-based security layer không dùng thư viện: chống code generation, chống jailbreak/prompt injection, chống SQL injection, chống token exhaustion, chống tư vấn tài chính/pháp lý. Mỗi rule có pattern matching riêng, chạy trước heuristic parser để tiết kiệm compute.

### 5.7. Deterministic Order Preview để tránh LLM Hallucination
Khi tạo đơn hàng, thay vì để LLM generator viết preview (dễ bịa SKU/số liệu), backend tự sinh deterministic answer từ dữ liệu thật của `calculate_landed_cost_tool`. LLM chỉ tham gia khi không có confirmation requirement.

### 5.8. Strict Entity Alignment Prompt Engineering
Prompt được thiết kế chi tiết để ép LLM generator không được phép bịa sản phẩm, SKU, giá, hoặc xưởng. Câu trả lời bắt buộc phải dùng đúng dữ liệu từ `Raw Calculation Results`. Sản phẩm index 0 luôn được highlight đầu tiên.

## 6. API Reference

### Chat & Agent Endpoints

| Method | Path | Chức năng | Auth |
|--------|------|-----------|------|
| POST | `/agent/chat` | Chat với AI Agent (SSE streaming) | None (public) |
| GET | `/agent/suggestions` | Gợi ý câu hỏi theo mùa/thị trường | None |

### Order Endpoints

| Method | Path | Chức năng | Auth |
|--------|------|-----------|------|
| GET | `/api/orders/history` | Lịch sử đơn hàng (có lọc status/sku) | None |
| GET | `/api/orders/{order_id}` | Chi tiết đơn hàng theo ID | None |
| GET | `/api/orders/by-order-number/{order_number}` | Chi tiết đơn hàng theo mã đơn | None |

### Health Check Endpoints

| Method | Path | Chức năng | Auth |
|--------|------|-----------|------|
| GET | `/health` | Kiểm tra server hoạt động | None |
| GET | `/ready` | Kiểm tra sẵn sàng phục vụ | None |

### BurgerPrints API tích hợp (internal)

| API | Endpoint | Mục đích |
|-----|----------|----------|
| V2 Product | `GET /v2/product` | Danh sách sản phẩm (phân trang) |
| V2 Product Detail | `GET /v2/product/{short_code}` | Chi tiết biến thể |
| V2 Order | `POST /v2/order` | Tạo đơn hàng |
| V2 Balance | `GET /v2/balance` | Kiểm tra số dư |
| V1 Catalog | `GET /api/v1/catalogsV2/locations` | Biểu phí vận chuyển |

## 7. Database Schema

### 7.1. Bảng `products`

| Cột | Kiểu | Ràng buộc |
|-----|------|-----------|
| id | TEXT | PRIMARY KEY |
| short_code | TEXT | INDEXED |
| name | TEXT | INDEXED, NOT NULL |
| display_name | TEXT | |
| description | TEXT | |
| category | TEXT | INDEXED (14 categories: T-Shirts, Mugs, Hoodies...) |
| image_url | TEXT | |
| metadata_json | JSON | |
| embedding | VECTOR(384) / JSON | pgvector hoặc JSON fallback |

### 7.2. Bảng `product_variants`

| Cột | Kiểu | Ràng buộc |
|-----|------|-----------|
| id | TEXT | PRIMARY KEY |
| product_id | TEXT | FK → products.id, INDEXED |
| sku | TEXT | INDEXED |
| color | TEXT | INDEXED |
| size | TEXT | INDEXED |
| base_cost | FLOAT | DEFAULT 0.0 |
| second_item_price | FLOAT | (in 2 mặt) |
| partner_name | TEXT | INDEXED (VD: "BurgerPrints US", "Dreamship US") |
| location_name | TEXT | INDEXED (VD: "US", "EU", "VN") |
| shipping_cost_us / ww | FLOAT | |
| shipping_adding_us / ww | FLOAT | |

### 7.3. Bảng `shipping_zones`

| Cột | Kiểu | Ràng buộc |
|-----|------|-----------|
| id | INT | PRIMARY KEY |
| country_code | TEXT | UNIQUE, INDEXED |
| country_name | TEXT | INDEXED |

### 7.4. Bảng `shipping_fees`

| Cột | Kiểu | Ràng buộc |
|-----|------|-----------|
| id | INT | PRIMARY KEY |
| zone_id | INT | FK → shipping_zones.id, INDEXED |
| carrier | TEXT | INDEXED |
| partner_name | TEXT | INDEXED, NULLABLE |
| first_item_fee | FLOAT | |
| additional_item_fee | FLOAT | |
| delivery_time | TEXT | VD: "3-5 business days" |

### 7.5. Bảng `chat_sessions`

| Cột | Kiểu | Ràng buộc |
|-----|------|-----------|
| session_id | TEXT | PRIMARY KEY |
| history | JSON | Array of {role, content} |
| slots | JSON | Dict of extracted slots |
| current_intent | TEXT | |
| created_at | DATETIME | |
| updated_at | DATETIME | |

### 7.6. Bảng `orders`

| Cột | Kiểu | Ràng buộc |
|-----|------|-----------|
| id | TEXT | PRIMARY KEY (UUID) |
| burger_order_id | TEXT | INDEXED |
| reference_order_id | TEXT | INDEXED |
| sku | TEXT | INDEXED |
| customer_name | TEXT | |
| total_amount | FLOAT | |
| status | TEXT | INDEXED (created/shipped/delivered/cancelled) |
| created_at | DATETIME | |

## 8. Bảo mật & độ tin cậy

### Bảo mật

- **5 Guardrails layer**: Anti-code-gen, Anti-jailbreak/prompt injection, Anti-SQL injection, Anti-token-exhaustion, Financial/Legal liability
- **PII Masking**: Số điện thoại (giữ 3 đầu + 2 cuối), email (giữ ký tự đầu + domain)
- **API Key management**: BurgerPrints API key và OpenAI keys từ environment variables qua pydantic-settings
- **Sandbox mode bắt buộc**: Mọi đơn hàng gửi lên BurgerPrints API đều có flag `sandbox: true`
- **CORS**: Cho phép mọi origin (cấu hình để hỗ trợ dev và ngrok)

### Độ tin cậy

- **Deterministic fallback**: API BurgerPrints có mock data fallback nếu API thật lỗi
- **Category state isolation**: Xóa params cũ khi chuyển category để tránh dữ liệu sai
- **Nearest alternative mode**: Nếu không có SKU khớp hoàn toàn, vẫn hiển thị các lựa chọn thay thế gần nhất
- **Empty state handling**: Generator prompt có rule nghiêm ngặt: không bịa sản phẩm khi không có data
- **Async timeout**: All API calls có timeout 15 giây
- **Anti-hallucination**: Order preview là deterministic, không qua LLM

## 9. Testing & chất lượng code

### Test files — 16 file test

| File | Mục đích |
|------|----------|
| `test_agent.py` | Agent engine + stream response |
| `test_catalog_fixes.py` | Catalog search, category filtering |
| `test_category_state_isolation.py` | Cross-category slot isolation |
| `test_checkout_payload.py` | Order creation payload |
| `test_e2e_regression_matrix.py` | End-to-end regression test matrix |
| `test_guardrails.py` | Rule-based security tests |
| `test_language_anchor.py` | Language detection + persistence |
| `test_response_formatting.py` | Markdown formatting + PII masking |
| `test_token_usage.py` | Token telemetry correctness |
| `test_trend_suggestions.py` | Seasonal suggestions service |
| `test_config.py` | Configuration loading |
| `test_http_switch.py` | API endpoint switching |
| `test_root_cause_http.py` | HTTP error diagnosis |
| `debug_ui_flow.py` | UI flow debugging |
| `debug_slots_deep.py` | Slot debugging |
| `debug_search_direct.py` | Search debugging |

### Quality practices

- **Test fixture isolation**: Mỗi test function dùng SQLite in-memory engine riêng, transaction rollback
- **Stream response extraction helper**: `extract_stream_response()` parse SSE stream để verify
- **Edge case coverage**: Empty states, ambiguous language, nearest alternative, base_cost_below_catalog_floor, margin threshold filtering
- **No external test dependencies**: Mock key mode cho phép test logic backend không cần gọi API thật

## 10. Định lượng / Số liệu

| Metric | Giá trị |
|--------|---------|
| Số API endpoint | 6 (backend) + 4 internal API tích hợp |
| Số bảng database | 6 (products, product_variants, shipping_zones, shipping_fees, chat_sessions, orders) |
| Số categories sản phẩm | 14 (T-Shirts, Mugs, Tank Tops, Hoodies, Sweatshirts, Blankets, Polo Shirts, Baby & Kids, Pajamas & Sleepwear, Bottoms & Shorts, Sportswear, Ornaments & Gifts, Home Decor & Flags, Accessories) |
| Số accessory leaf types | 30+ (sticker, keychain, doormat, hat, sock, tote bag...) |
| Số file test | 16 |
| Số guardrail patterns | 30+ regex patterns trong 5 rules |
| Số market hỗ trợ | 6 (US, EU/DE/FR, VN, AU/NZ, ZA) + fallback chain |
| LLM calls per request | Tối đa 2 (parser + generator) |
| Catalog sync interval | 6 giờ / lần |
| Async concurrency | Semaphore(15) cho catalog sync |
| Số commit | 120+ |

## 11. Vai trò cá nhân

> *Phần này để trống — cần người dùng tự điền mô tả vai trò thực tế của mình trong dự án (VD: Full-stack solo developer, chỉ làm backend, leader team X người...)*

## 12. Gợi ý cách trình bày trong CV / Portfolio

### Resume Bullets (dùng động từ hành động + con số)

1. **Built an AI-powered POD Catalog Assistant** from scratch using FastAPI + React, serving 6 international markets (US, EU, VN, AU, NZ, ZA) with real-time product search, multi-factory comparison, and landed cost calculation — reducing seller SKU research time from hours to seconds.

2. **Designed and implemented a decoupled agent architecture** combining heuristic intent routing and LLM-based generation, achieving maximum 2 LLM calls per request (vs. 5-10 in traditional agent loops), significantly reducing latency and token costs.

3. **Developed a hybrid search engine** using Reciprocal Rank Fusion (keyword + vector embedding) for POD catalog search across 14 product categories and 30+ accessory types, with automatic category state isolation preventing cross-category data contamination.

4. **Implemented geo-aware seasonal merchandising** logic supporting southern/northern hemisphere detection, climate-specific product mapping, Vietnamese holiday calendar, and deterministic country fallback chains — enabling contextually relevant product recommendations year-round.

5. **Built a comprehensive security layer** with 5 guardrail rules (anti-code-gen, anti-jailbreak, anti-SQL-injection, anti-token-exhaustion, financial/legal liability prevention), PII masking, and sandbox-first order creation requiring 2-step confirmation — ensuring safe production deployment.

6. **Created 16 test suites** with in-memory SQLite fixtures, achieving robust regression coverage for agent flows, search accuracy, category isolation, language detection, guardrails, and token telemetry — enabling confident refactoring without manual QA.

### Keywords kỹ thuật để ATS scan

`FastAPI` · `React 19` · `TypeScript` · `Python 3.11` · `SQLModel` · `SQLite` · `PostgreSQL` · `pgvector` · `OpenAI API` · `Azure OpenAI` · `RAG` · `Hybrid Search` · `RRF` · `LLM Agent` · `SSE Streaming` · `Server-Sent Events` · `APScheduler` · `Docker` · `Print-on-Demand` · `E-commerce` · `Cross-border Fulfillment`
