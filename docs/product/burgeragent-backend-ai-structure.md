# CẤU TRÚC THƯ MỤC BACKEND & AI PHÂN TÁCH (INDEPENDENT SERVICES STRUCTURE)

## DỰ ÁN: BURGERAGENT CORE (HỆ THỐNG CỐT LÕI)

> [!IMPORTANT]
> **Tên tài liệu:** Cấu trúc dự án độc lập Backend & AI - BurgerAgent Core  
> **Phiên bản:** v1.1.0 (Bản phân tách microservices)  
> **Ngày cập nhật:** 2026-06-18  
> **Trạng thái:** DỰ THẢO (Chấp thuận thiết kế phân tách)

Tài liệu này đặc tả chi tiết cấu trúc thư mục phân tách độc lập (Monorepo but Isolated Services) giữa **phân hệ Backend (FastAPI)** và **phân hệ AI (FastAPI/LangChain)**. Thiết kế này giúp tách biệt hoàn toàn môi trường chạy, dependencies và luồng xử lý, đảm bảo khả năng mở rộng (Scale), triển khai (Deploy) độc lập và dễ dàng gỡ rối khi gặp sự cố vận hành.

---

## 1. Kiến Trúc Phân Tách Tổng Quan (Architecture Overview)

Ở giai đoạn phát triển hiện tại, cả 3 phân hệ (Frontend, Backend, AI) được phát triển chung trong một repository nhưng nằm ở các thư mục độc lập ở root. Backend và AI giao tiếp với nhau qua giao thức HTTP REST/WebSocket nội bộ.

```
[Web Client (Next.js)]       [Telegram Client]
        │                           │
        │ HTTP / WebSockets         │ HTTPS Webhook
        ▼                           ▼
┌──────────────────────────────────────────────┐
│            backend/ (Port 8000)              │
│       (Quản lý DB, Users, Orders, Bot)       │
└──────────────────────┬───────────────────────┘
                       │
                       │ HTTP API / JSON
                       ▼
┌──────────────────────────────────────────────┐
│              ai/ (Port 8001)                 │
│      (LangChain Agent, Tools, Pillow)        │
└──────────────────────────────────────────────┘
```

---

## 2. Bản Đồ Cấu Trúc Thư Mục Monorepo

```
BurgerAgent/ (Monorepo Root)
│
├── frontend/                  # Phân hệ Web Client (Next.js - độc lập)
│
├── backend/                   # Phân hệ Backend API (FastAPI - Chạy Port 8000)
│   ├── app/
│   │   ├── api/               # Controller Layer: Tiếp nhận HTTP/Websocket từ Client & Webhook
│   │   │   ├── v1/
│   │   │   │   ├── endpoints/
│   │   │   │   │   ├── auth.py             # Xác thực JWT tài khoản Seller
│   │   │   │   │   ├── chat_relay.py       # Tiếp nhận chat từ Web và relay sang AI Service
│   │   │   │   │   ├── orders.py           # Đẩy đơn sandbox lên BurgerPrints & xem lịch sử
│   │   │   │   │   └── webhook.py          # Tiếp nhận Webhook Telegram Bot & BurgerPrints
│   │   │   │   └── router.py
│   │   │   └── dependencies.py
│   │   │
│   │   ├── core/              # Cấu hình & Security của Backend
│   │   │   ├── config.py                   # Đọc env backend (.env)
│   │   │   └── security.py                 # bcrypt & JWT helper
│   │   │
│   │   ├── db/                # Cơ sở dữ liệu SQLite
│   │   │   ├── session.py                  # SQLAlchemy engine & sessionmaker
│   │   │   └── base_class.py
│   │   │
│   │   ├── models/            # SQLAlchemy Models (Bảng SQL tĩnh)
│   │   │   ├── user.py
│   │   │   ├── session.py
│   │   │   ├── chat_history.py
│   │   │   ├── user_preferences.py
│   │   │   └── order.py
│   │   │
│   │   ├── repositories/      # Repository Layer (Data Access)
│   │   │   ├── base.py                     # CRUD SQL helpers
│   │   │   ├── user_repo.py
│   │   │   ├── order_repo.py
│   │   │   └── catalog_repo.py             # Quản lý CATALOG_CACHE & FTS5 index
│   │   │
│   │   ├── services/          # Business Logic Layer
│   │   │   ├── auth_service.py
│   │   │   ├── order_service.py
│   │   │   ├── ai_client.py                # HTTP Client giao tiếp với AI Service (Port 8001)
│   │   │   └── sync_service.py             # Background task sync catalog định kỳ 5h
│   │   │
│   │   ├── utils/             # Helper functions dùng chung cho Backend
│   │   └── main.py            # FastAPI Entry Point cho Backend (Port 8000)
│   │
│   ├── tests/                 # Bộ test suite riêng cho Backend
│   ├── pyproject.toml         # File quản lý thư viện độc lập của Backend (dùng uv)
│   ├── uv.lock                # Tệp khóa thư viện Backend
│   ├── dockerfile             # Dockerfile build riêng cho Backend
│   └── .env                   # Biến môi trường Backend
│
├── ai/                        # Phân hệ AI Agent (FastAPI - Chạy Port 8001)
│   ├── app/
│   │   ├── api/               # API Gateway tiếp nhận yêu cầu suy luận từ Backend
│   │   │   ├── v1/
│   │   │   │   ├── endpoints/
│   │   │   │   │   ├── inference.py        # API endpoint chạy Agent Loop & trả kết quả
│   │   │   │   │   └── rendering.py        # API endpoint vẽ mockup sản phẩm
│   │   │   │   └── router.py
│   │   │   └── dependencies.py
│   │   │
│   │   ├── core/              # Cấu hình AI Service
│   │   │   └── config.py                   # Đọc env AI (.env) chứa GEMINI_API_KEY
│   │   │
│   │   ├── agent/             # Quy trình xử lý AI Agent (LangChain)
│   │   │   ├── custom_loop.py              # Custom LangChain Agent Loop (Thinking CoT)
│   │   │   └── prompts.py                  # System & User Prompts
│   │   │
│   │   ├── tools/             # Python Calculation & Search Engine (Internal Tools)
│   │   │   ├── calculation.py              # Tính toán Landed Cost, Margin, Tax chính xác
│   │   │   └── fts_search.py               # Truy vấn Catalog bằng SQLite FTS5
│   │   │
│   │   ├── memory/            # Quản lý bộ nhớ ngữ cảnh hội thoại
│   │   │   ├── sliding_window.py
│   │   │   └── summarizer.py
│   │   │
│   │   ├── schema_mapper/     # Module tự phục hồi API
│   │   │   ├── mapper.py                   # LLM mapping schema generator
│   │   │   └── mapping_metadata.json
│   │   │
│   │   ├── telegram_adapter/  # Module chuyển đổi định dạng hiển thị cho Telegram
│   │   │   ├── bot_formatter.py            # Format Candidate Table -> Markdown text
│   │   │   └── mockup_renderer.py          # Render ghép ảnh đè phôi sử dụng Pillow
│   │   │
│   │   └── main.py            # FastAPI Entry Point cho AI Service (Port 8001)
│   │
│   ├── tests/                 # Bộ test suite riêng cho AI
│   ├── pyproject.toml         # File quản lý thư viện độc lập của AI (dùng uv)
│   ├── uv.lock                # Tệp khóa thư viện AI
│   ├── dockerfile             # Dockerfile build riêng cho AI (Có thể build trên GPU base image)
│   └── .env                   # Biến môi trường AI
│
└── docs/                      # Tài liệu thiết kế hệ thống
    └── product/
```

---

## 3. Đặc Tả Quản Lý Độc Lập Bằng `uv` Cho Từng Phân Hệ

Do Backend và AI có nhiệm vụ hoàn toàn khác nhau, các gói thư viện phụ thuộc (`dependencies`) của từng thư mục được cấu hình độc lập để tránh xung đột phiên bản và giảm kích thước tệp Docker Image.

### 3.1. Quản lý Thư Viện Backend (`backend/pyproject.toml`)
Backend chỉ cần các thư viện phục vụ kết nối DB, API Gateway, JWT và các thư viện giao tiếp mạng cơ bản:

```toml
[project]
name = "burgeragent-backend"
version = "1.0.0"
description = "FastAPI Backend API for BurgerAgent"
requires-python = ">=3.10"
dependencies = [
    "fastapi>=0.110.0",
    "uvicorn[standard]>=0.28.0",
    "pydantic>=2.6.0",
    "pydantic-settings>=2.2.0",
    "sqlalchemy>=2.0.0",
    "bcrypt>=4.1.0",
    "pyjwt>=2.8.0",
    "python-multipart>=0.0.9",
    "python-dotenv>=1.0.1",
    "httpx>=0.27.0",
    "pytelegrambotapi>=4.16.0",
]

[dependency-groups]
dev = [
    "pytest>=8.0.0",
    "pytest-asyncio>=0.23.0",
]
```

### 3.2. Quản lý Thư Viện AI (`ai/pyproject.toml`)
AI Service cần tích hợp các gói nặng về tính toán và mô hình LLM:

```toml
[project]
name = "burgeragent-ai"
version = "1.0.0"
description = "LangChain AI Agent Service for BurgerAgent"
requires-python = ">=3.10"
dependencies = [
    "fastapi>=0.110.0",
    "uvicorn[standard]>=0.28.0",
    "pydantic>=2.6.0",
    "pydantic-settings>=2.2.0",
    "python-dotenv>=1.0.1",
    "httpx>=0.27.0",
    "langchain>=0.1.10",
    "langchain-google-genai>=1.0.0",
    "pillow>=10.2.0",
]

[dependency-groups]
dev = [
    "pytest>=8.0.0",
    "pytest-asyncio>=0.23.0",
]
```

---

## 4. Hướng Dẫn Vận Hành Độc Lập Khi Phát Triển Local

Để gỡ lỗi dễ dàng và cô lập tiến trình chạy, nhà phát triển mở 2 tab terminal riêng biệt và di chuyển (`cd`) vào từng thư mục để chạy:

### Tab 1: Khởi chạy Backend Service (Port 8000)
```bash
cd backend
uv venv
# Kích hoạt môi trường (Windows): .venv\Scripts\Activate.ps1
uv sync
uv run uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

### Tab 2: Khởi chạy AI Service (Port 8001)
```bash
cd ai
uv venv
# Kích hoạt môi trường (Windows): .venv\Scripts\Activate.ps1
uv sync
uv run uvicorn app.main:app --host 0.0.0.0 --port 8001 --reload
```

---

## 5. Tương Tác Nghiệp Vụ Giữa BE Và AI

1. **Relay tin nhắn chat:**
   Khi seller nhập chat trên Web, `backend/app/api/v1/endpoints/chat_relay.py` nhận request, gọi API POST sang `ai/app/api/v1/endpoints/inference.py` để lấy kết quả từ LangChain Agent, sau đó trả ngược về cho Client.
2. **Yêu cầu vẽ Mockup:**
   Khi checkout, backend gọi API POST sang `ai/app/api/v1/endpoints/rendering.py` kèm theo link ảnh thiết kế, nhận về file ảnh mockup đã ghép để hiển thị lên client.
3. **Đọc SQLite Database chung:**
   AI Service đọc trực tiếp file SQLite Database của Backend thông qua đường dẫn chung (Shared Volume khi deploy Docker hoặc path local khi chạy dev) để thực hiện truy vấn FTS5 tìm kiếm thông tin catalog nhanh mà không cần gọi API vòng lặp.

---

Thiết kế phân tách này đảm bảo tính bền vững của mã nguồn và sẵn sàng cho việc đóng gói Docker Compose độc lập ở giai đoạn chốt dự án. Mọi bổ sung module Backend hoặc AI phải tuân thủ nghiêm ngặt ranh giới cấu trúc này.
