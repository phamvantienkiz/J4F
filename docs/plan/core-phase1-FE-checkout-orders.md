# Kế hoạch triển khai: Billing Summary, Checkout & Order HUD (FE - Giai đoạn 1)

## 1. Liên kết Yêu cầu & Tài liệu tham chiếu
- **User Story liên quan:**
  - [US-003: Đặt Đơn Sandbox Qua Order HUD](file:///E:/MyProject/BurgerAgent/docs/product/burgeragent-core-prd.md#L135-L157)
  - [US-004: Theo Dõi Trạng thái Lịch Sử Đơn Hàng](file:///E:/MyProject/BurgerAgent/docs/product/burgeragent-core-prd.md#L159-L176)
- **Functional Requirements:**
  - [F-5: Giao Dịch Đặt Đơn Sandbox - Thông tin người nhận & confetti](file:///E:/MyProject/BurgerAgent/docs/product/burgeragent-core-prd.md#L223-L230)
- **Technical Constraints & Architecture:**
  - [Quy trình Đặt Hàng Đa Kênh Sequence Diagram](file:///E:/MyProject/BurgerAgent/docs/product/burgeragent-core-architecture.md#L329-L355)
  - [Tab 1: Fulfillment Checkout & Tab 2: Lịch Sử Đơn](file:///E:/MyProject/BurgerAgent/docs/product/burgeragent-frontend-design.md#L125-L140)
  - [Trực Quan Hóa SLA Bằng Tiến Trình Gradient (SLA Risk Timeline)](file:///E:/MyProject/BurgerAgent/docs/product/burgeragent-frontend-design.md#L199-L213)
  - [Đặc Tả Chi Tiết Orders API (/v1/orders)](file:///E:/MyProject/BurgerAgent/docs/product/burgeragent-core-api.md#L179-L253)
- **QA/QC Test Cases:**
  - [TC-009: Cập nhật Billing Summary thời gian thực](file:///E:/MyProject/BurgerAgent/docs/product/burgeragent-core-qa-qc.md#L87)
  - [TC-010: Validation thông tin nhận hàng - Viền đỏ lỗi](file:///E:/MyProject/BurgerAgent/docs/product/burgeragent-core-qa-qc.md#L88-L89)
  - [TC-011: Đặt đơn hàng Sandbox thành công - Confetti bùng nổ](file:///E:/MyProject/BurgerAgent/docs/product/burgeragent-core-qa-qc.md#L90)
  - [TC-012: Đặt đơn Sandbox không trừ ví](file:///E:/MyProject/BurgerAgent/docs/product/burgeragent-core-qa-qc.md#L91)

---

## 2. Đặc tả Kỹ thuật
- **Billing Summary (Hóa đơn động):**
  - Tự động cộng chi phí `2nd_price` khi có thiết kế mặt sau.
  - Áp thuế suất tương ứng với quốc gia giao hàng.
  - Tổng số tiền `Landed Cost` được in đậm màu xanh Emerald (`--success`).
- **Form Checkout & Xác thực:**
  - Chặn submit và hiển thị viền đỏ xung quanh các ô nhập liệu bị bỏ trống.
  - Nút bấm tạo đơn bị khóa (`disabled`), hiển thị loading spinner khi gửi POST.
- **Confetti Celebration:** Đơn hàng tạo thành công sẽ kích hoạt hiệu ứng pháo hoa giấy bay mượt mà trên toàn màn hình.
- **Order HUD Tab (Lịch sử đơn):**
  - Tải danh sách đơn hàng đã đặt từ SQLite.
  - Click vào từng đơn mở xem thông tin vận đơn trực quan lấy từ API `GET /v1/orders/{id}?expand=tracking`.
  - SLA tiến trình hiển thị dưới dạng thanh tiến trình màu chuyển đổi: Xanh (an toàn) -> Vàng -> Đỏ (vượt SLA preferences).

---

## 3. Kế hoạch Triển khai (Mã nguồn & Cấu trúc)
1. **Phát triển Billing Summary Component:**
   - Tạo React component `BillingSummary` nhận các props: `base_cost`, `print_cost` (bằng 0 nếu in 1 mặt, bằng `2nd_price` nếu in 2 mặt), `shipping_fee`, `tax_rate`, và `quantity`.
   - Tính toán và kết xuất chi tiết hóa đơn, giá tổng cộng in đậm màu `--success`.
2. **Xây dựng Form Nhập thông tin & Xử lý Xác nhận:**
   - Tạo component `CustomerCheckoutForm` quản lý các input state: `recipient_name`, `address_line1`, `address_line2`, `city`, `state`, `postal_code`, `country`.
   - Viết hàm validate: Nếu các trường bắt buộc trống, lưu danh sách lỗi vào state để cập nhật CSS `.border-red` viền đỏ cho các ô input tương ứng, hiển thị banner cảnh báo.
   - Gắn sự kiện `onSubmit`: Gọi API `POST /v1/orders`. Khóa nút bấm và hiển thị spinner.
   - Sử dụng thư viện `canvas-confetti` để kích hoạt bắn pháo hoa giấy khi API trả về mã thành công. Hiển thị Popup kết quả chứa Order ID sandbox và tracking number.
3. **Phát triển Order History Tab:**
   - Tạo component `OrderHistoryTab` kéo dữ liệu từ API `/v1/orders` kèm các tham số phân trang.
   - Map danh sách đơn hàng thành các card dọc: Mã đơn monospace, SKU, số lượng, tổng tiền và badge trạng thái màu tương ứng (*Pending* - xám, *Production* - xanh dương, *Shipped* - xanh lá, *Failed* - đỏ).
4. **Triển khai Màn hình Chi tiết Vận đơn (Tracking Details):**
   - Click card đơn hàng -> Trực quan hóa thông tin vận chuyển.
   - Gọi API `/v1/orders/{id}?expand=tracking` để lấy carrier, tracking code, estimated delivery, và last checkpoint.
   - Vẽ thanh SLA Timeline nằm ngang dạng gradient chỉ báo độ trễ so với SLA preferences.

---

## 4. Kịch bản Kiểm thử & QA/QC (Không Mock Data)
- **TC-ORDERHUD-001: Tính giá Billing Summary động**
  - **Mục tiêu:** Cập nhật tiền chính xác khi đổi các tùy chọn sản phẩm.
  - **Cách test:** Chọn phôi Hoodie, số lượng 2. Tải thiết kế mặt sau lên -> Billing Summary phải tự động hiển thị thêm dòng giá in mặt thứ hai, cộng phí shipping, tính thuế suất và nhân đôi tổng tiền Landed Cost chính xác.
- **TC-ORDERHUD-002: Form Validation và thông báo lỗi**
  - **Mục tiêu:** Chặn gửi form và báo đỏ các trường thiếu.
  - **Cách test:** Để trống trường "Zip Code" và click "Confirm Fulfillment Order" -> Form không được gửi đi, viền ô Zip Code đổi màu đỏ và xuất hiện thông báo: `"Vui lòng nhập đầy đủ địa chỉ giao hàng để tính toán ship và đặt đơn"`.
- **TC-ORDERHUD-003: Đặt đơn thành công và Confetti**
  - **Mục tiêu:** Hiển thị hiệu ứng pháo hoa giấy và khóa click đúp khi thanh toán.
  - **Cách test:** Điền đầy đủ địa chỉ, click "Confirm Fulfillment Order" -> Nút bấm đổi sang Loading spinner, khóa tương tác chuột. Sau khi backend trả về order thành công -> Pháo hoa giấy confetti bùng nổ trên màn hình, hiển thị popup mã đơn sandbox.
- **TC-ORDERHUD-004: Mở rộng hành trình vận đơn (Tracking Expansion)**
  - **Mục tiêu:** Hiển thị chi tiết checkpoint hành trình thực tế.
  - **Cách test:** Chuyển sang tab Lịch sử đơn, click vào một đơn hàng bất kỳ đã ship -> Màn hình phải tải chi tiết đơn hàng và hiển thị sơ đồ checkpoint các địa điểm mà gói hàng đã đi qua (ví dụ: Arrived at facility, USPS...) kéo về từ API BurgerPrints.
