# PROJECT STRUCTURE AND LAYOUT SPECIFICATION: PRINTFLOW AI

Tài liệu này định nghĩa cấu trúc thư mục tiêu chuẩn cho toàn bộ mã nguồn của dự án **PrintFlow AI** đặt trong thư mục `@Product/`. Cấu trúc được thiết kế theo mô hình Clean Architecture để dễ dàng mở rộng, kiểm thử, và quản lý giữa ba phân hệ chính: Backend (FastAPI), Frontend (Vite/TypeScript), và AI (LangGraph).

---

## 1. Bản Đồ Thư Mục Tổng Thể (Global Directory Map)

Toàn bộ dự án sẽ nằm trong thư mục `@Product/` và được chia nhỏ như sau:

```
@Product/
├── backend/                # FastAPI Application (API Gateway & Business Logic)
├── frontend/               # React Vite Application with TypeScript & Vanilla CSS
├── ai/                     # LangGraph Agent Engine & Pricing Engine
├── docker-compose.yml      # Cấu hình container chạy thử MVP
└── README.md               # Hướng dẫn khởi chạy nhanh dự án
```

---

## 2. Chi Tiết Phân Hệ Backend (FastAPI Application)

Backend được xây dựng theo cấu trúc Module chuẩn của FastAPI để phân tách rõ ràng trách nhiệm giữa Database Models, Schema Validation, Router Endpoints và Business Services:

```
backend/
├── app/
│   ├── api/                # Cổng kết nối API endpoints
│   │   ├── deps.py         # Dependencies (Auth, DB session, API key injection)
│   │   └── v1/             # Phiên bản 1 của REST API
│   │       ├── auth.py     # API Đăng ký / Đăng nhập / Lấy Profile
│   │       ├── chat.py     # API gửi message / lấy lịch sử hội thoại
│   │       └── order.py    # API confirm tạo đơn hàng / tra cứu tracking
│   │
│   ├── core/               # Cấu hình hệ thống chung
│   │   ├── config.py       # Đọc biến môi trường (.env), CORS settings
│   │   └── security.py     # Mã hóa mật khẩu (bcrypt) & sinh JWT tokens
│   │
│   ├── db/                 # Kết nối cơ sở dữ liệu
│   │   ├── base.py         # Import tất cả models phục vụ migration
│   │   ├── session.py      # Khởi tạo SQLAlchemy Engine & SessionLocal
│   │   └── vector_db.py    # Khởi tạo và kết nối ChromaDB client
│   │
│   ├── models/             # SQLAlchemy ORM Models (Ánh xạ Database DDL)
│   │   ├── user.py
│   │   ├── preference.py
│   │   ├── conversation.py
│   │   ├── message.py
│   │   └── order.py
│   │
│   ├── schemas/            # Pydantic Schemas (Validation dữ liệu Request/Response)
│   │   ├── user.py
│   │   ├── chat.py
│   │   └── order.py
│   │
│   └── services/           # Lớp dịch vụ nghiệp vụ chính (Business Logic)
│       ├── auth_service.py # Xử lý logic đăng ký, so sánh hash pass
│       ├── chat_service.py # Lưu lịch sử chat, khôi phục session
│       └── order_service.py# Giao tiếp API BurgerPrints & cập nhật DB
│
├── requirements.txt        # Các thư viện Python backend (fastapi, sqlalchemy, jose...)
└── main.py                 # File chạy chính (Khởi tạo FastAPI app & Uvicorn router)
```

---

## 3. Chi Tiết Phân Hệ AI (LangGraph & Pricing Engine)

Mô hình điều phối AI được đóng gói riêng biệt dưới dạng một gói thư viện Python nội bộ, kết nối với Backend thông qua các interface API rõ ràng:

```
ai/
├── agent.py                # File khởi dựng LangGraph Workflow (Nodes, Edges, State)
├── state.py                # Định nghĩa cấu trúc TypedDict của Agent State
├── nodes.py                # Lập trình logic cho các Nodes (NLU, Retrieval, Recommendation)
├── tools.py                # Đóng gói bộ công cụ gọi API ngoài (search_catalog, create_order)
├── pricing_engine.py       # Deterministic Pricing Engine (Tính Margin, Landed Cost)
├── vector_rag.py           # Pipeline nhúng vector & truy vấn ChromaDB
├── data/                   # Thư mục lưu DB local
│   ├── sqlite.db           # SQLite database file
│   └── chromadb/           # Thư mục chứa index vector của ChromaDB
└── requirements.txt        # Thư viện AI (langgraph, langchain-google-genai, chromadb...)
```

---

## 4. Chi Tiết Phân Hệ Frontend (Vite + React + TypeScript)

Sử dụng Vite với React và TypeScript làm giải pháp mặc định để tăng tốc độ biên dịch (HMR) và tối ưu hóa thời gian phát triển trong khuôn khổ Hackathon. Toàn bộ styling sử dụng **Vanilla CSS** chuyên nghiệp, chia nhỏ theo component để dễ kiểm soát:

```
frontend/
├── public/                 # Các tài nguyên tĩnh (logo, favicon, sound effects)
├── src/
│   ├── assets/             # Hình ảnh, icon SVG
│   ├── components/         # Các Component giao diện tái sử dụng
│   │   ├── common/         # Button, Input, Modal, Loading Spinner dùng chung
│   │   ├── auth/           # LoginModal, RegisterModal
│   │   ├── chat/           # ChatWindow, MessageBubble, SuggestionChips
│   │   ├── sidebar/        # HistorySidebar, SessionItem
│   │   └── right_panel/    # ProductInspector, OrderHUD
│   │
│   ├── context/            # React Context quản lý trạng thái toàn cục
│   │   ├── AuthContext.tsx # Quản lý trạng thái login của Seller
│   │   └── ChatContext.tsx # Quản lý hội thoại, gửi tin nhắn, thread_id
│   │
│   ├── hooks/              # Custom React Hooks
│   │   ├── useFetch.ts     # Thao tác gọi HTTP API
│   │   └── useChat.ts      # Logic tự động cuộn chat, phím tắt
│   │
│   ├── services/           # Lớp kết nối HTTP API Client
│   │   └── api_client.ts   # Axios/Fetch client cấu hình sẵn JWT Header
│   │
│   ├── styles/             # Hệ thống CSS phân rã (Vanilla CSS)
│   │   ├── variables.css   # Định nghĩa Style Tokens (color, typography, transitions)
│   │   ├── global.css      # Cấu hình CSS chung, reset margin
│   │   ├── layout.css      # Cấu hình grid 3 cột chính
│   │   └── components/     # CSS cho từng component (Chat, Sidebar, HUD...)
│   │
│   ├── App.tsx             # Component chính (Quản lý layout và render)
│   ├── main.tsx            # Điểm khởi động ứng dụng React
│   └── vite-env.d.ts       # Khai báo kiểu TypeScript cho môi trường Vite
│
├── package.json            # Scripts khởi chạy & Danh sách dependencies
├── tsconfig.json           # Cấu hình TypeScript compiler
└── vite.config.ts          # Cấu hình build của Vite
```

---

## 5. Nguyên Tắc Tổ Chức & Tương Tác Mã Nguồn (Inter-component Rules)

1.  **Strict Boundary (Ngăn cách ranh giới):** Frontend không bao giờ được gọi trực tiếp sang module `ai` hay gọi trực tiếp API của BurgerPrints. Mọi tương tác phải đi qua FastAPI Gateway (`/api/v1/`).
2.  **No Direct AI Calculations (Không giao việc tính toán cho LLM):** Logic tính toán giá, ship, margin phải nằm trọn vẹn trong `ai/pricing_engine.py` và được import bởi node xử lý trong `ai/nodes.py`.
3.  **Unified State Schema (Schema thống nhất):** Pydantic model trong `backend/app/schemas/chat.py` phải khớp cấu trúc với `ai/state.py` để đảm bảo chuyển đổi kiểu dữ liệu (JSON serialization) không bị lỗi runtime.
4.  **Style Isolation (Cô lập phong cách styling):** Toàn bộ file css trong `frontend/src/styles/components/` phải sử dụng quy tắc đặt tên BEM (Block-Element-Modifier) hoặc CSS Modules để tránh xung đột phong cách hiển thị giữa các cột panel.
