# Kế hoạch triển khai: Database, Repository & FTS5 (BE - Giai đoạn 1)

## 1. Liên kết Yêu cầu & Tài liệu tham chiếu
- **User Story liên quan:**
  - [US-001: Tra Cứu & So Sánh Xưởng Qua Chatbot](file:///E:/MyProject/BurgerAgent/docs/product/burgeragent-core-prd.md#L88-L110)
  - [US-004: Theo Dõi Trạng Thái Lịch Sử Đơn Hàng](file:///E:/MyProject/BurgerAgent/docs/product/burgeragent-core-prd.md#L159-L176)
- **Functional Requirements:**
  - [F-1: Thiết kế LangGraph Stateful Agent Loop - Domain Retrieval](file:///E:/MyProject/BurgerAgent/docs/product/burgeragent-core-prd.md#L182-L195)
  - [F-5: Giao Dịch Đặt Đơn Sandbox - Ghi đơn hàng vào DB SQLite](file:///E:/MyProject/BurgerAgent/docs/product/burgeragent-core-prd.md#L223-L230)
- **Technical Constraints & Architecture:**
  - [Kiến Trúc SQLite Lai (Hybrid JSON/NoSQL Database)](file:///E:/MyProject/BurgerAgent/docs/product/burgeragent-core-prd.md#L276-L286)
  - [Thiết kế Cơ sở dữ liệu lai (Hybrid SQL/NoSQL Database)](file:///E:/MyProject/BurgerAgent/docs/product/burgeragent-core-architecture.md#L138-L156)
  - [Bảng Catalog Cache & FTS5](file:///E:/MyProject/BurgerAgent/docs/product/burgeragent-core-architecture.md#L225-L264)
- **QA/QC Test Cases:**
  - [TC-018: Hiệu năng phản hồi cục bộ](file:///E:/MyProject/BurgerAgent/docs/product/burgeragent-core-qa-qc.md#L107-L112)

---

## 2. Đặc tả Kỹ thuật
- **Kiến trúc dữ liệu:** SQLite Lai (Hybrid).
  - **Bảng Tĩnh (Statically-typed):** `users`, `user_preferences`, `sessions`, `chat_history`, `orders`.
  - **Bảng Động (NoSQL TEXT/JSON):** `catalog_cache` (lưu thô JSON từ API), `shipping_rate_cache`.
  - **Bảng Ảo Tìm Kiếm (FTS5):** `catalog_fts5` (tự động đồng bộ từ `catalog_cache` để tìm kiếm toàn văn không dùng VectorDB/RAG).
- **Lớp thiết kế:** Repository Pattern (`DataRepository`) nhằm trừu tượng hóa truy cập SQL, độc lập hoàn toàn với lớp logic nghiệp vụ.

---

## 3. Kế hoạch Triển khai (Mã nguồn & Cấu trúc)
1. **Thiết lập Cấu hình Kết nối và Session Database:**
   - Tạo file cấu hình session trong [backend/app/db/session.py](file:///E:/MyProject/BurgerAgent/docs/product/burgeragent-backend-ai-structure.md#L62-L64) khởi tạo SQLAlchemy Engine với file SQLite local.
   - Bật cờ `pragma foreign_keys=ON` cho kết nối SQLite để đảm bảo toàn vẹn dữ liệu.
2. **Xác định các SQLAlchemy Models:**
   - Tạo mô hình `User` (email, password_hash, store_name, created_at) trong [backend/app/models/user.py](file:///E:/MyProject/BurgerAgent/docs/product/burgeragent-backend-ai-structure.md#L67).
   - Tạo mô hình `UserPreferences` (user_id, preferred_market, target_margin, max_sla_days, priority_criteria) trong [backend/app/models/user_preferences.py](file:///E:/MyProject/BurgerAgent/docs/product/burgeragent-backend-ai-structure.md#L70).
   - Tạo mô hình `Session` và `ChatHistory` trong [backend/app/models/session.py](file:///E:/MyProject/BurgerAgent/docs/product/burgeragent-backend-ai-structure.md#L68) và [backend/app/models/chat_history.py](file:///E:/MyProject/BurgerAgent/docs/product/burgeragent-backend-ai-structure.md#L69).
   - Tạo mô hình `Order` (order_id, user_id, bp_order_id, sku, quantity, total_landed_cost, status, tracking_number, created_at) trong [backend/app/models/order.py](file:///E:/MyProject/BurgerAgent/docs/product/burgeragent-backend-ai-structure.md#L71).
   - Tạo mô hình `CatalogCache` (product_id, short_code, data_raw_json, updated_at) và `ShippingRateCache` (product_id, destination_country, shipping_fee, estimated_days, updated_at).
3. **Cấu hình Bảng Ảo FTS5:**
   - Viết các câu lệnh SQL khởi tạo bảng ảo `catalog_fts5` sử dụng module FTS5 tích hợp của SQLite chứa các cột: `product_id`, `short_code`, `searchable_text`.
   - Viết triggers hoặc logic hàm Python đồng bộ hóa index: khi một bản ghi trong `catalog_cache` được thêm/cập nhật, bóc tách mô tả, tên, chất liệu trong JSON thô và cập nhật `catalog_fts5`.
4. **Xây dựng Repository Layer:**
   - Tạo Base Repository trong [backend/app/repositories/base.py](file:///E:/MyProject/BurgerAgent/docs/product/burgeragent-backend-ai-structure.md#L74) cung cấp các hàm CRUD cơ bản sử dụng SQLAlchemy.
   - Tạo `UserRepository`, `OrderRepository` xử lý nghiệp vụ ghi đơn hàng sandbox, lấy lịch sử.
   - Tạo `CatalogRepository` trong [backend/app/repositories/catalog_repo.py](file:///E:/MyProject/BurgerAgent/docs/product/burgeragent-backend-ai-structure.md#L77) chứa logic:
     - `get_catalog_json(product_id: str)`: lấy dữ liệu JSON thô của sản phẩm.
     - `search_catalog_fts(keyword: str)`: truy vấn tìm kiếm toàn văn nhanh chóng bằng câu lệnh `MATCH`.
     - `get_mapping_metadata()`: đọc tệp ánh xạ schema mapper.
5. **Cấu hình Tự động Tạo Bảng (Migrations):**
   - Viết code chạy tự động tạo tất cả các bảng tĩnh và bảng ảo FTS5 trong lần đầu chạy ứng dụng (ở file [backend/app/main.py](file:///E:/MyProject/BurgerAgent/docs/product/burgeragent-backend-ai-structure.md#L86)).

---

## 4. Kịch bản Kiểm thử & QA/QC (Không Mock Data)
- **TC-DB-001: Khởi tạo schema và khóa ngoại**
  - **Mục tiêu:** Đảm bảo tất cả các bảng được tạo chính xác và ràng buộc khóa ngoại hoạt động.
  - **Cách test:** Chạy ứng dụng, kết nối database SQLite qua tool SQL client, chèn thử bản ghi `user_preferences` không tồn tại `user_id` -> Phải nhận về lỗi vi phạm ràng buộc khóa ngoại (`Foreign Key Constraint`).
- **TC-DB-002: Kiểm tra tìm kiếm toàn văn FTS5**
  - **Mục tiêu:** Tìm kiếm phôi sản phẩm thành công bằng từ khóa mô tả.
  - **Cách test:** Chèn tay 1 dòng dữ liệu phôi vào `catalog_cache` với JSON chứa từ khóa `"100% cotton T-shirt"`, chạy logic bóc tách đồng bộ sang `catalog_fts5`. Thực hiện gọi hàm `search_catalog_fts("cotton")` -> Phải trả về chính xác `product_id` tương ứng trong thời gian dưới **200ms**.
- **TC-DB-003: Cập nhật cache ghi đè**
  - **Mục tiêu:** Kiểm tra cơ chế cache ghi đè bản ghi catalog khi sync lại.
  - **Cách test:** Thực hiện chèn bản ghi phôi trùng `product_id`, sử dụng lệnh `upsert` để ghi đè -> Kiểm tra trường `updated_at` phải được cập nhật thời gian mới và dữ liệu JSON được cập nhật chính xác.
