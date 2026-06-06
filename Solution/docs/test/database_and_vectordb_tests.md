# DATABASE & VECTOR DATABASE TEST SPECIFICATION

Tài liệu này đặc tả chi tiết các kịch bản kiểm thử cho hệ thống lưu trữ dữ liệu của **BurgerPrints Agent**, bao gồm Cơ sở dữ liệu quan hệ **SQLite** (lưu phiên chat, tài khoản, cấu hình) và Vector Database **ChromaDB** (lưu trữ và truy xuất ngữ nghĩa bộ nhớ hội thoại).

Tài liệu này được thiết kế thống nhất và liên kết chặt chẽ với [System Architecture](file:///E:/Hackathon2026/J4F/Solution/docs/architecture/architecture.md), [Database & VectorDB Spec](file:///E:/Hackathon2026/J4F/Solution/docs/ai/database_and_vectordb_spec.md), và [Project Structure & Layout](file:///E:/Hackathon2026/J4F/Solution/docs/ai/project_structure_and_layout.md).

---

## 1. Kiểm Thử Cơ Sở Dữ Liệu Quan Hệ (SQLite Schema Validation)

Sử dụng thư viện `SQLAlchemy` để chạy các bài test xác thực tính toàn vẹn của database schema.

### 1.1. Xác thực cấu trúc bảng (Table Structures)

#### Test Case DB-001: Xác thực đầy đủ các Bảng và Trường
*   **Mục tiêu:** Đảm bảo SQLite khởi tạo đúng cấu trúc 5 bảng dữ liệu bắt buộc.
*   **Action:** Thực hiện kiểm tra metadata của database engine.
*   **Expected Results:**
    *   Tồn tại 5 bảng: `users`, `user_preferences`, `conversations`, `messages`, `order_history`.
    *   Bảng `users` phải chứa khóa chính `id` (TEXT) và trường `email` (TEXT).
    *   Bảng `user_preferences` phải chứa khóa ngoại `user_id` liên kết đến `users.id`.
    *   Bảng `conversations` phải chứa khóa chính `id` (dùng làm `thread_id`).
    *   Bảng `messages` phải chứa trường `sender` giới hạn kiểu dữ liệu và trường `metadata` dạng TEXT (chứa chuỗi JSON).
    *   Bảng `order_history` phải chứa trường `order_id` (TEXT UNIQUE).

### 1.2. Kiểm thử Ràng buộc và Khóa ngoại (Constraints & Foreign Keys)

#### Test Case DB-002: Kiểm tra ràng buộc duy nhất (Unique Constraints)
*   **Mục tiêu:** Đảm bảo không cho phép trùng lặp email đăng ký hoặc trùng lặp mã đơn hàng.
*   **Action:**
    1.  Insert bản ghi user với email `"duplicate@example.com"`.
    2.  Insert bản ghi user thứ hai với cùng email `"duplicate@example.com"`.
*   **Expected Result:** Database ném lỗi `IntegrityError` (Unique constraint failed: users.email).

#### Test Case DB-003: Kiểm tra ràng buộc kiểm tra của tin nhắn (Check Constraints)
*   **Mục tiêu:** Đảm bảo trường `sender` trong bảng `messages` chỉ chấp nhận hai giá trị định trước.
*   **Action:** Insert một tin nhắn với `sender` = `"hacker"`.
*   **Expected Result:** Database ném lỗi `IntegrityError` (Check constraint failed: sender IN ('user', 'assistant')).

#### Test Case DB-004: Kiểm tra xóa bắc cầu (Cascade Delete)
*   **Mục tiêu:** Đảm bảo khi tài khoản người dùng bị xóa, toàn bộ hội thoại và preferences liên quan cũng bị xóa sạch.
*   **Action:**
    1.  Tạo tài khoản user `usr_01`.
    2.  Tạo preferences và 2 conversations liên kết với `usr_01`.
    3.  Thực hiện lệnh xóa user `usr_01`.
*   **Expected Result:**
    *   Bản ghi trong bảng `user_preferences` có `user_id` = `"usr_01"` tự động bị xóa.
    *   Các bản ghi trong bảng `conversations` có `user_id` = `"usr_01"` tự động bị xóa.
    *   Các bản ghi trong bảng `messages` liên kết với các hội thoại trên tự động bị xóa.

---

## 2. Kiểm Thử Vector Database (ChromaDB Semantic Memory)

Sử dụng thư viện `chromadb` và `pytest` để xác thực luồng ghi và truy xuất bộ nhớ hội thoại ngữ nghĩa.

### 2.1. Kiểm thử quá trình Nhúng & Lập chỉ mục (Message Indexing Pipeline)

#### Test Case VDB-001: Nhúng tin nhắn thành công
*   **Mục tiêu:** Xác minh khi có tin nhắn mới, hệ thống tự động nhúng vector và lưu vào ChromaDB đúng metadata.
*   **Action:** 
    1.  Gửi tin nhắn: `"Tôi chỉ bán áo thun tại thị trường Mỹ."` từ người dùng `usr_01` trong conversation `conv_01`.
    2.  Gọi pipeline nhúng vector.
*   **Expected Results:**
    *   Gọi thành công Gemini API `text-embedding-004` trả về mảng vector số thực 768 chiều.
    *   Thêm thành công vào collection `chat_history_memory` của ChromaDB.
    *   Metadata được lưu chính xác:
        ```json
        {
          "conversation_id": "conv_01",
          "sender": "user",
          "user_id": "usr_01"
        }
        ```

---

### 2.2. Kiểm thử quá trình Tìm kiếm Ngữ nghĩa (Semantic Recall Pipeline)

#### Test Case VDB-002: Hồi tưởng bộ nhớ đúng ngữ cảnh (Semantic Search Accuracy)
*   **Mục tiêu:** Đảm bảo Agent tìm kiếm và gợi nhớ đúng thông tin lịch sử khi người dùng hỏi một chủ đề liên quan.
*   **Initial Vector Database State:** Collection `chat_history_memory` đã được nạp 3 tài liệu quá khứ:
    *   Doc 1: `"Tôi muốn bán Hoodie tại thị trường Pháp."` (User `usr_01`, 3 ngày trước)
    *   Doc 2: `"Tôi chuyên bán Cốc sứ đi Đức."` (User `usr_01`, 2 ngày trước)
    *   Doc 3: `"Tôi muốn bán T-shirt tại Mỹ."` (User `usr_02` - người dùng khác, 1 ngày trước)
*   **Action:** User `usr_01` mở phiên chat mới và hỏi: `"Tuần trước tôi có nói muốn bán áo Hoodie ở quốc gia nào ấy nhỉ?"`
*   **Expected Search Behavior (ChromaDB Query):**
    *   Truy vấn ChromaDB với chuỗi `"áo Hoodie ở quốc gia nào"` và bộ lọc metadata `{ "user_id": "usr_01" }` để bảo mật dữ liệu giữa các seller.
    *   Kết quả trả về phải xếp Doc 1 lên hàng đầu (độ tương đồng Cosine cao nhất).
    *   Hệ thống không được trả về Doc 3 (của user `usr_02`) dù có từ khóa `"Mỹ"` gần giống.
*   **Expected Agent Action:** Agent nhận được Doc 1 từ Vector DB, thực hiện phục hồi ngữ cảnh và phản hồi Seller: `"Theo lịch sử hội thoại trước đó, bạn đã đề cập muốn bán sản phẩm Hoodie tại thị trường Pháp (EU). Bạn có muốn em tìm kiếm các xưởng in Hoodie gửi đi Pháp không?"`
