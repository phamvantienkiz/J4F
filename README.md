# BurgerPrints POD Catalog Assistant (AI Agent)

Dự án này là một hệ thống AI Chatbot hội thoại (State-driven Agent) tích hợp với API BurgerPrints v2.0 nhằm hỗ trợ những nhà bán hàng (Sellers) tìm kiếm, so sánh sản phẩm fulfill, tính toán landed cost/margin, gợi ý theo mùa vụ/vùng miền và tạo đơn hàng nháp trực tiếp từ các cuộc trò chuyện tự nhiên.

## 🚀 Tính Năng Chính

1. **Đồng Bộ Dữ Liệu Offline-First:** 
   - Đồng bộ hóa định kỳ (mỗi 6 giờ) thông tin sản phẩm, biến thể (variants) và biểu phí vận chuyển từ BurgerPrints API về cơ sở dữ liệu để đảm bảo tốc độ truy xuất cực nhanh.
2. **AI Agent Trợ Lý Thông Minh (State-Driven Agent):**
   - Hỗ trợ hội thoại đa lượt bằng cách lưu giữ ngữ cảnh cuộc trò chuyện (`ChatSession`).
   - Sử dụng cơ chế **Slot Filling** để nhận diện và thu thập các thông tin còn thiếu từ người dùng (như quốc gia, loại sản phẩm, ngân sách, v.v.).
3. **Tính Toán Chi Phí Chi Tiết (Landed Cost & Profit Margin):**
   - Tự động áp dụng công thức tính Landed Cost: `Landed Cost = Base Cost * Quantity + Shipping Fee + Tax Fee`
   - Tính toán chi tiết lợi nhuận (`Profit`) và tỷ suất lợi nhuận (`Margin %`) dựa trên giá bán đề xuất của seller.
   - Hỗ trợ chế độ cảnh báo nếu Margin thực tế thấp hơn Margin tiêu chuẩn của seller.
4. **Hệ Thống Gợi Ý Theo Mùa Vụ & Vùng Miền (Regional & Seasonal Suggestion):**
   - Đưa ra khuyến nghị sản phẩm phù hợp theo từng quốc gia (Mỹ - US, Đức - DE, Việt Nam - VN...) và tháng lựa chọn dựa trên yếu tố thời tiết và các sự kiện lễ hội lớn (như Giáng sinh, Halloween, Quốc khánh...).
   - **Tự động nhận diện ngữ cảnh thời gian và địa điểm:** Hệ thống đã loại bỏ hoàn toàn các dropdown Market và Month cứng nhắc trên Header UI. AI Agent sẽ tự động trích xuất quốc gia và tháng dựa trên nội dung trò chuyện (sử dụng hệ quy chiếu thời gian hệ thống cố định là **Tháng 6 năm 2026** để xử lý các từ tương đối như *mùa hè, tháng sau, tháng này*). Giao diện frontend sẽ tự động phản hồi và đồng bộ các gợi ý thời tiết/sản phẩm theo ngữ cảnh động này.
5. **Nearest Alternative Mode (Lựa chọn thay thế gần nhất):**
   - Nếu không tìm thấy sản phẩm đáp ứng 100% tiêu chí lọc của seller (ví dụ: quá ngân sách hoặc giao hàng lâu hơn yêu cầu), AI Agent sẽ tự động chuyển sang đề xuất các biến thể có thông số gần nhất và đưa ra cảnh báo cụ thể.
6. **Double Confirmation & PII Protection (Bảo mật & Rào chắn an toàn):**
   - Yêu cầu xác nhận 2 bước ("xác nhận tạo sandbox order") trước khi gọi API thật để tạo đơn hàng nháp.
   - Tự động che giấu thông tin nhạy cảm của khách hàng (PII) như Tên, Số điện thoại, Email, Địa chỉ và Mã Zip trước khi hiển thị trên màn hình chat của seller.

---

## 🛠️ Kiến Trúc Hệ Thống

Dự án được chia làm 2 phần chính:
- **Backend (FastAPI):**
  - **SQLModel:** Định nghĩa CSDL và tương tác với DB PostgreSQL (Supabase) hoặc SQLite.
  - **OpenAI API / Heuristic Parse:** Hỗ trợ NLP để trích xuất ý định (intent) và dữ liệu (slots) từ tin nhắn của người dùng.
  - **APScheduler:** Thực hiện đồng bộ dữ liệu catalog chạy nền tự động.
- **Frontend (React + Vite + TypeScript):**
  - Giao diện chat trực quan tích hợp danh sách sản phẩm gợi ý và form tạo đơn hàng (Draft Order).

---

## 💻 Hướng Dẫn Cài Đặt

### 1. Cấu Hình Biến Môi Trường (.env)

Tạo tệp `.env` trong thư mục `backend/` với các thông số sau:
```env
BURGERPRINTS_API_KEY=your_burgerprints_api_key_here
BURGERPRINTS_API_BASE_URL=https://api.burgerprints.com/v2
BURGERPRINTS_ENABLE_SANDBOX_CREATE_ORDER=true
SUPABASE_DB_URL=postgresql://postgres:postgres@localhost:5432/postgres  # Hoặc SQLite: sqlite:///database.db
OPENAI_API_KEY=mock-key  # Hoặc OpenAI Key thật của bạn
```

### 2. Cài Đặt & Chạy Backend (FastAPI)

Yêu cầu: **Python 3.10+**

Chạy các lệnh sau tại thư mục `backend/`:
```bash
# Tạo môi trường ảo (khuyến nghị)
python -m venv venv
source venv/bin/activate  # Trên Windows dùng: venv\Scripts\activate

# Cài đặt thư viện phụ thuộc
pip install -r requirements.txt

# Khởi chạy API Server
uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```

FastAPI Server sẽ chạy tại địa chỉ `http://127.0.0.1:8000`. Bạn có thể truy cập tài liệu API tự động tại `http://127.0.0.1:8000/docs`.

### 3. Cài Đặt & Chạy Frontend (React)

Yêu cầu: **Node.js 18+**

Chạy các lệnh sau tại thư mục `frontend/`:
```bash
# Cài đặt dependencies
npm install

# Khởi chạy chế độ phát triển
npm run dev
```

Ứng dụng Frontend sẽ chạy tại `http://127.0.0.1:5173`.

---

## 🧪 Chạy Kiểm Thử (Tests)

Hệ thống được phát triển đi kèm bộ kiểm thử tự động toàn diện cho API, Agent Engine và các logic tính toán.

Để chạy kiểm thử backend, di chuyển vào thư mục `backend/` và thực thi:
```bash
PYTHONPATH=. pytest
```

---

## 💬 Hướng Dẫn Sử Dụng Chatbot

Bạn có thể tương tác với chatbot bằng Tiếng Việt hoặc Tiếng Anh thông qua các câu lệnh tự nhiên:
* **Tìm kiếm & Gợi ý:** *"Tìm áo thun cotton ở Mỹ dưới $10"*
* **So sánh xưởng:** *"So sánh phí ship hoodie ở Đức"*
* **Tính toán Margin:** *"Tính margin cho SKU USG5000-Black-S tại US với giá bán 25 đô"*
* **Tạo đơn hàng nháp:** *"Tạo đơn cho Nguyễn Văn A, 123 Đường Láng, Hà Nội, 100000, VN"* -> Chatbot sẽ yêu cầu bạn nhập dòng chữ xác nhận: `xác nhận tạo sandbox order` để hoàn tất.
