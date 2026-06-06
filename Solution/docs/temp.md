### 1. Chuẩn bị thông tin kết nối và File cấu hình mẫu ( .env.example )

• Kiểm tra API Credentials: Xác thực quyền truy cập vào BurgerPrints API v2.
0 (Base URL, API Keys, Credentials) do Ban tổ chức cung cấp.
• Tạo file cấu hình mẫu: Thiết lập file .env.example chứa các biến cấu
hình cần thiết (như GEMINI_API_KEY , BURGERPRINTS_API_KEY , DATABASE_URL ,
JWT_SECRET ) đảm bảo tuân thủ nguyên tắc bảo mật của topic.md (Không
upload API key lên public repo).

### 2. Thiết lập dữ liệu giả lập (Mock API Data / Mock Server)

• Do BurgerPrints API v2.0 có thể gặp rủi ro về độ trễ (Latency) hoặc Rate
Limit trong quá trình code và demo, chúng ta cần chuẩn bị sẵn một bộ dữ
liệu giả lập dạng JSON (Mock Data) khớp chính xác với cấu trúc thực tế của
catalog BurgerPrints.
• Thiết lập cờ USE_MOCK_API=true trong cấu hình để Backend có thể switch
(chuyển đổi) mượt mà giữa gọi API thật và gọi dữ liệu Mock khi phát sinh sự
cố.

### 3. Khởi tạo dự án và cấu hình Standard Linting (Project Initialization)

• Backend: Khởi tạo môi trường ảo Python, cấu hình requirements.txt hoặc
pyproject.toml với các thư viện cốt lõi ( fastapi , langgraph , chromadb ,
sqlalchemy ).
• Frontend: Khởi tạo template dự án Vite + React + TypeScript bằng lệnh non-
interactive (ví dụ: npm create vite@latest product-frontend -- --template
react-ts ).
• Lắp đặt Code Style & Hooks: Cấu hình ESLint/Prettier cho frontend và
Black/Ruff cho backend để tự động format code khi lưu/commit, đảm bảo giữ
codebase luôn sạch sẽ theo AGENTS.md.

### 4. Viết sẵn kịch bản kiểm thử tích hợp (Integration Test Cases)

• Soạn thảo sẵn file test script hoặc file kịch bản test API thô (ví dụ:
file .http để gọi REST Client) để kiểm thử độc lập 3 tình huống mẫu của
Seller ngay khi code xong từng Graph Node. Bước này giúp ta phát hiện sớm
lỗi logic tính toán margin hoặc lỗi trích xuất slots mà không cần chờ UI
hoàn thiện.
