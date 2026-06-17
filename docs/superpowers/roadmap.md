# Lộ trình Phát triển BurgerPrints Smart Agent (Roadmap)

## 📌 Các Phase Phát triển Hệ thống

- [x] **Phase 1: Setup Backend & Cấu hình Biến môi trường** `(Status: VERIFIED & LOCKED)`
  - [x] Khởi tạo FastAPI Server và kết nối DB.
  - [x] Tạo cơ sở dữ liệu in-memory thử nghiệm và seed data.
  - [x] Viết unit tests kiểm tra tích hợp API và config.
  - [x] **Nghiệm thu:** 100% tests PASSED (`test_config.py`).

- [x] **Phase 2: Tích hợp Engine & Tính toán Margin / Landed Cost** `(Status: VERIFIED & LOCKED)`
  - [x] Tích hợp logic tính toán Landed Cost đa chiều bao gồm in 1/2 mặt (print_sides), phí ship, thuế.
  - [x] Triển khai giải thuật Đa dạng hóa nguồn xưởng (Round Robin) trong tìm kiếm sản phẩm.
  - [x] Triển khai tính toán Giá bán đề xuất (Suggested Selling Price) dựa trên min_margin.
  - [x] Cải tiến AgentEngine hỗ trợ tính toán và gợi ý chính xác.
  - [x] **Nghiệm thu:** 100% tests PASSED (`test_agent.py` và `test_config.py`).

- [ ] **Phase 3: Gợi ý Sản phẩm theo Mùa  & Vùng địa lý (Seasonal & Regional Engine)** `(Status: IN_PROGRESS)`
  - [ ] Khởi tạo interface `ITrendService` và mô hình dữ liệu.
  - [ ] Xây dựng logic phân loại thời tiết theo Bán cầu địa lý (Bắc / Nam).
  - [ ] Thiết lập liên kết văn hóa và sự kiện lễ hội lớn theo từng quốc gia và tháng.
  - [ ] Tích hợp tính năng tự động phát hiện và Fallback quốc gia không được hỗ trợ sang phương án tối ưu gần nhất.
  - [ ] Viết unit tests cho `TrendService` và tích hợp vào AgentEngine.
  - [ ] **Nghiệm thu:** Chạy kiểm thử thành công và kiểm chứng hoạt động.

- [ ] **Phase 4: Tích hợp Sandbox Order & Bảo mật Thông tin PII** `(Status: PENDING)`
  - [ ] Xây dựng REST API tạo đơn hàng Sandbox tới API BurgerPrints v2.
  - [ ] Tích hợp cơ chế che giấu thông tin nhạy cảm (PII Masking) trong hội thoại AI.
  - [ ] Triển khai cơ chế Xác nhận 2 bước nghiêm ngặt trước khi tạo đơn thực tế.
  - [ ] **Nghiệm thu:** Kiểm thử luồng tạo đơn và che giấu thông tin thành công.
[x] **Phase 5: Cải tiến Giao diện & Trải nghiệm Người dùng (Fronte
nd UI/UX Enhancements)** `(Status: VERIFIED & LOCKED)`
  - [x] Triển khai hoạt ảnh chờ (Waiting/Shimmer State) cho Thought
Process trước khi stream token đầu tiên.
  - [x] Tích hợp hiệu ứng nhấp nháy cho các dấu chấm (blinking stagg
ered dots) và hiệu ứng mờ dần (fade-out 300ms) khi bắt đầu nhận phản
 hồi.
  - [x] **Nghiệm thu:** Kiểm thử typecheck và build frontend thành c
ông.
