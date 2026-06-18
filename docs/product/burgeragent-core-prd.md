# TÀI LIỆU YÊU CẦU SẢN PHẨM (PRODUCT REQUIREMENTS DOCUMENT - PRD)

## TÊN TÍNH NĂNG: BURGERAGENT CORE FULFILLMENT ASSISTANT (HỆ THỐNG CỐT LÕI)

**Phiên bản**: 1.0  
**Ngày tạo**: 2026-06-16  
**Tác giả**: Antigravity (Product Owner Agent)  
**Điểm Đánh Giá Chất Lượng Yêu Cầu (Requirements Quality Score)**: 98/100

---

📊 **Requirements Quality Score: 98/100**

Phân tích điểm số chi tiết:

- **Business Value & Goals**: 30/30 (Bài toán tối ưu hóa Landed Cost và rủi ro SLA xưởng cực kỳ rõ ràng).
- **Functional Requirements**: 24/25 (Mô tả tính năng và luồng xử lý Agent kết hợp Python Engine chi tiết, đầy đủ user story).
- **User Experience**: 20/20 (Kế thừa toàn bộ đặc tả Dashboard 3 cột Glassmorphic có độ nét cao từ UI/UX prototypes).
- **Technical Constraints**: 15/15 (Xác định rõ stack FastAPI, SQLite, Docker, .env và các Endpoint API BurgerPrints v2.0).
- **Scope & Priorities**: 9/10 (Rõ ràng các tính năng MVP cốt lõi loại bỏ phần tương lai).

_Điểm số đạt 98/100 (vượt điều kiện tối thiểu 90/100). Tiến hành tạo tài liệu PRD._

---

## 1. Problem Statement (Tuyên Bố Bài Toán)

### 1.1. Hiện Trạng & Khó Khăn (Current Situation)

Hiện tại, các seller kinh doanh Print-on-Demand (POD) trên BurgerPrints gặp rất nhiều khó khăn trong việc lựa chọn xưởng in và cấu hình SKU cho đơn hàng xuất khẩu (Mỹ, châu Âu, Việt Nam).

Mỗi sản phẩm có hàng ngàn biến thể (kết hợp của size, màu, vị trí in) và được cung cấp bởi nhiều xưởng in khác nhau với mức giá base (Base Cost), phí in mặt thứ hai (`2nd_price`), phí vận chuyển (Shipping Rate) và thời gian giao hàng (SLA) hoàn toàn khác nhau. Việc tính toán thủ công chi phí Landed Cost và so sánh để chọn ra xưởng in tốt nhất mất nhiều giờ, dẫn đến chậm trễ giao hàng và ảnh hưởng trực tiếp đến lợi nhuận.

### 1.2. Giải Pháp Đề Xuất (Proposed Solution)

Xây dựng hệ thống **BurgerAgent Core** là một chatbot AI hội thoại đa lượt, tích hợp cơ sở dữ liệu đệm (SQLite) đồng bộ với BurgerPrints API v2.0. Chatbot cho phép seller truy vấn, so sánh các nhà in thông qua ngôn ngữ tự nhiên (VN/EN).

Hệ thống hỗ trợ đồng thời hai kênh tương tác (Omni-channel Interface):

- **Web Dashboard:** Bố cục 3 cột trực quan (Left Sidebar, Center Chat, Right Product Inspector & Order HUD).
- **Telegram Chatbot Bot:** Trải nghiệm chatbot tương tác hoàn toàn trên Telegram, tự động chuyển đổi thông tin bảng biểu và hình ảnh mockup sang dạng text và media phù hợp.

### 1.3. Tác Động Kinh Doanh (Business Impact)

- Rút ngắn thời gian ra quyết định fulfillment từ trung bình 2 giờ xuống còn dưới 1 phút.
- Đảm bảo tính toán chính xác 100% chi phí Landed Cost bằng Python Engine để giữ vững biên lợi nhuận (Margin) mong muốn của seller.
- Tăng tỷ lệ hoàn thành đơn hàng fulfillment nhờ tích hợp mượt mà giữa khung chat tư vấn và HUD đặt hàng nhanh.

---

## 2. Success Metrics (Chỉ Số Đo Lường Thành Công)

### 2.1. Chỉ số KPI Chính (Primary KPIs)

- **Thời gian chọn xưởng (Time-to-Decision):** < 1 phút cho một yêu cầu tư vấn xưởng in hoàn chỉnh.
- **Độ chính xác tính toán chi phí (Calculation Accuracy):** Đạt 100% (Sai lệch chi phí Landed Cost so với hóa đơn thực tế của BurgerPrints = $0.00).
- **Thời gian phản hồi truy vấn dữ liệu (Response Latency):** < 2.0 giây cho các câu hỏi tra cứu catalog sản phẩm nhờ cơ chế SQLite Caching.
- **Tỷ lệ đặt đơn thành công (Checkout Success Rate):** > 98% trên môi trường sandbox.

### 2.2. Kiểm Chứng (Validation)

Các chỉ số này sẽ được đo lường tự động thông qua log hệ thống (Backend latency logs) và kiểm thử thực tế (UAT) của đội ngũ QA của BurgerPrints bằng kịch bản chạy thử đơn hàng sandbox.

---

## 3. User Personas (Chân Dung Người Dùng)

### 3.1. Persona Chính: Minh - Seller POD Mới (New Seller)

- **Vai trò:** Người mới bắt đầu bán áo thun 2D sang thị trường Mỹ trên Etsy.
- **Mục tiêu:** Tìm được xưởng in có Landed Cost thấp nhất để tối ưu hóa ngân sách vốn còn mỏng.
- **Nỗi đau:** Không biết xưởng nào ship nhanh, cách tính thuế VAT/Sales Tax của Mỹ quá phức tạp, sợ đặt nhầm SKU dẫn đến khách hoàn hàng.
- **Trình độ kỹ thuật:** Trung bình (biết sử dụng máy tính và các công cụ quản lý store cơ bản).

### 3.2. Persona Phụ: Sarah - Pro Seller (Experienced Seller)

- **Vai trò:** Trưởng nhóm vận hành store Shopify bán Hoodie/Mug sang thị trường châu Âu (EU) với sản lượng 50-100 đơn/ngày.
- **Mục tiêu:** Theo dõi sát sao rủi ro vận hành (SLA) của các xưởng in và đẩy nhanh tốc độ đặt hàng để kịp thời gian giao cho khách.
- **Nỗi đau:** Các xưởng thường xuyên trễ hẹn sản xuất vào mùa cao điểm mà không cảnh báo trước; mất quá nhiều thao tác để tạo thủ công từng đơn hàng.
- **Trình độ kỹ thuật:** Khá tốt (đã quen với các giao thức API và hệ thống OMS/ERP).

---

## 4. User Stories & Acceptance Criteria (Yêu Cầu Từ Người Dùng)

_(Viết theo chuẩn INVEST và cú pháp Given-When-Then của Gherkin)_

### US-001: Tra Cứu & So Sánh Xưởng Qua Chatbot

**As a** Seller POD trên BurgerPrints,  
**I want to** đặt câu hỏi bằng ngôn ngữ tự nhiên (tiếng Việt hoặc tiếng Anh) để tra cứu thông tin sản phẩm và so sánh các xưởng in,  
**So that** tôi có thể chọn được phương án fulfillment tối ưu nhất về chi phí và thời gian mà không cần dò bảng giá thủ công.

#### Tiêu chí nghiệm thu (Acceptance Criteria):

- **AC1: Truy vấn thành công và hiển thị Bảng so sánh (Happy Path)**
  - **Given** Seller đã đăng nhập thành công vào hệ thống.
  - **When** Seller nhập prompt `"So sánh Hoodie các xưởng ship đi EU rẻ nhất"`.
  - **Then** AI Agent nhận dạng được ý định (Hoodie, thị trường EU, độ ưu tiên giá rẻ), truy xuất DB và hiển thị bảng so sánh gồm đầy đủ thông tin: Xưởng in, Base Cost, Print Cost, Shipping Fee, Tax, Landed Cost, Margin, SLA và đánh giá Rủi ro SLA.
  - **And** hàng đề xuất tối ưu nhất (Option 1) được làm nổi bật bằng viền tím và gắn badge `"RECOMMENDED"`.
- **AC2: Xử lý thiếu thông tin đầu vào (Edge Case)**
  - **Given** Seller nhập prompt quá chung chung `"Tôi muốn tìm xưởng in T-shirt"`.
  - **When** AI Agent phân tích thấy thiếu thị trường đích (Destination) và số lượng mặt in.
  - **Then** Chatbot phản hồi bằng một câu hỏi thân thiện để yêu cầu Seller cung cấp thêm thông tin: `"Bạn muốn gửi T-shirt sang quốc gia nào (US, EU, VN) và thiết kế của bạn in 1 mặt hay 2 mặt?"`.
- **AC3: Dự phòng lỗi kết nối API (Error Path)**
  - **Given** Kết nối mạng từ Backend đến BurgerPrints API v2.0 bị mất hoặc API gặp sự cố.
  - **When** Seller thực hiện truy vấn so sánh.
  - **Then** Hệ thống tự động sử dụng dữ liệu catalog và giá ship lưu trong SQLite cache để tính toán, đồng thời hiển thị cảnh báo nhỏ: `"Đang sử dụng dữ liệu ngoại tuyến (offline) đồng bộ gần nhất lúc [Thời gian]"`.

---

### US-002: Xem Mockup & Tùy Biến Sản Phẩm

**As a** Seller POD trên BurgerPrints,  
**I want to** cấu hình màu sắc, kích thước và tải lên ảnh thiết kế trực quan tại Right Panel,  
**So that** tôi có thể kiểm tra sản phẩm hiển thị thực tế và cập nhật chính xác hóa đơn Landed Cost trước khi chốt đơn.

#### Tiêu chí nghiệm thu (Acceptance Criteria):

- **AC1: Đồng bộ sản phẩm từ Chat sang Mockup Inspector (Happy Path)**
  - **Given** Seller thấy bảng so sánh xưởng in ở cột Chat.
  - **When** Seller click nút `"Chọn Xưởng"` tại dòng của xưởng mong muốn.
  - **Then** Cột Right Panel tự động chuyển sang tab _"Fulfillment Checkout"_, hiển thị hình ảnh mockup phôi sản phẩm tương ứng dưới dạng đồ họa SVG/Ảnh, đồng thời hiển thị bảng chọn màu sắc (Color swatches) và kích thước (Size selectors) khả dụng.
- **AC2: Lồng ghép thiết kế lên Mockup (Happy Path - Design Placement)**
  - **Given** Giao diện Product Inspector đang mở phôi áo Navy.
  - **When** Seller nhập đường link ảnh thiết kế vào ô `"Front Design URL"` hoặc chọn file tải lên trực tiếp.
  - **Then** Đồ họa thiết kế tự động được căn chỉnh tỷ lệ và lồng đè lên vùng ngực của mockup áo Navy để hiển thị bản xem trước mặt trước (Front view).
- **AC3: Tự động tính giá in mặt thứ hai (Happy Path - 2nd Print Cost)**
  - **Given** Seller đã cấu hình thiết kế mặt trước.
  - **When** Seller tiếp tục tải lên thiết kế thứ hai vào ô `"Back Design URL"`.
  - **Then** Hệ thống tự động kích hoạt tính năng in 2 mặt, mockup hiển thị thêm nút chuyển xem mặt sau (Back view) và Billing Summary tự động cập nhật cộng thêm chi phí `2nd_price` (lấy từ dữ liệu API `/v2/product/{id}`).

---

### US-003: Đặt Đơn Sandbox Qua Order HUD

**As a** Seller POD trên BurgerPrints,  
**I want to** nhập thông tin nhận hàng và xác nhận thanh toán đơn hàng Sandbox trực tiếp từ Order HUD,  
**So that** tôi có thể kiểm tra toàn bộ luồng tạo đơn hàng và tích hợp hệ thống mà không cần lo lắng về tài chính.

#### Tiêu chí nghiệm thu (Acceptance Criteria):

- **AC1: Đặt đơn Sandbox thành công và kích hoạt hiệu ứng (Happy Path)**
  - **Given** Seller đã điền đầy đủ các thông tin địa chỉ giao nhận bắt buộc và cấu hình mockup.
  - **When** Seller click nút `"Confirm Fulfillment Order"`.
  - **Then** Hệ thống thực hiện gọi API tạo đơn Sandbox của BurgerPrints, khóa nút bấm để tránh click trùng, sau khi thành công sẽ kích hoạt hiệu ứng pháo hoa giấy (confetti) bùng nổ trên màn hình.
  - **And** Hiển thị màn hình thành công liệt kê mã đơn hàng sandbox, tổng chi phí thực tế và mã vận đơn (Tracking number).
- **AC2: Kiểm tra dữ liệu địa chỉ bắt buộc (Validation)**
  - **Given** Một hoặc nhiều trường thông tin giao nhận (Full Name, Address 1, City, Zip Code) bị bỏ trống.
  - **When** Seller cố gắng nhấn nút `"Confirm Fulfillment Order"`.
  - **Then** Hệ thống không gửi yêu cầu đi, làm nổi bật viền đỏ xung quanh các trường bị thiếu và hiển thị thông báo lỗi: `"Vui lòng nhập đầy đủ địa chỉ giao hàng để tính toán ship và đặt đơn"`.
- **AC3: Đặt đơn sandbox không trừ ví (Sandbox Payment Constraint)**
  - **Given** Tài khoản của Seller trên hệ thống Sandbox BurgerPrints có số dư ví là $0.00.
  - **When** Seller nhấn xác nhận đặt đơn Sandbox.
  - **Then** Yêu cầu tạo đơn API vẫn được chấp nhận và trả về trạng thái đặt đơn thành công vô điều kiện.

---

### US-004: Theo Dõi Trạng Thái Lịch Sử Đơn Hàng

**As a** Seller POD trên BurgerPrints,  
**I want to** xem danh sách đơn hàng đã đặt và kiểm tra chi tiết tracking vận đơn thời gian thực,  
**So that** tôi có thể quản lý hành trình đơn hàng và thông báo cho khách hàng của mình.

#### Tiêu chí nghiệm thu (Acceptance Criteria):

- **AC1: Hiển thị danh sách đơn hàng (Happy Path)**
  - **Given** Seller chuyển sang tab _"Lịch sử đơn"_ ở Right Panel.
  - **When** Giao diện tải dữ liệu.
  - **Then** Hệ thống hiển thị danh sách các đơn hàng đã đặt xếp dọc lấy từ cơ sở dữ liệu SQLite, mỗi đơn gồm mã đơn hàng, ngày đặt, SKU phôi, số lượng, tổng tiền (màu xanh lá) và badge trạng thái (Pending, Production, Shipped, Failed).
- **AC2: Xem chi tiết và tracking trực tiếp từ API (Happy Path)**
  - **Given** Seller click vào một thẻ đơn hàng bất kỳ trong danh sách.
  - **When** Giao diện chuyển sang màn hình Chi tiết Đơn hàng.
  - **Then** Hệ thống thực hiện gọi trực tiếp API Order Tracking của BurgerPrints để lấy trạng thái vận đơn mới nhất (Carrier, Tracking Number, Trạng thái thực tế từ nhà vận chuyển) và hiển thị trực quan lên màn hình.

---

## 5. Functional Requirements (Yêu Cầu Chức Năng Chi Tiết)

### 5.1. Khối Tính Năng MVP (Core Scope)

#### F-1: Hệ thống AI Chatbot và Thiết kế LangChain Agent Loop Tự Do

- **Mô tả:** Nhận đầu vào ngôn ngữ tự nhiên tiếng Anh/Việt từ seller. Thay vì sử dụng LangGraph với các trạng thái (states) cứng nhắc làm giảm tính linh hoạt, hệ thống sử dụng **LangChain làm nền tảng cốt lõi** và tự phát triển Agent Loop tùy biến để tối ưu hóa khả năng suy nghĩ của LLM.
- **Không gian suy nghĩ (Thinking Space) của LLM:**
  - LLM được cung cấp system prompt hỗ trợ Chain-of-Thought (suy nghĩ từng bước) sâu sắc.
  - LLM được "tự do" suy nghĩ và lập kế hoạch thực hiện trước khi quyết định gọi Tool Python tính toán, truy cập cơ sở dữ liệu hay phản hồi trực tiếp cho người dùng.
  - Giao diện hỗ trợ hiển thị hoặc ẩn các khối suy nghĩ này tùy theo cấu hình của hệ thống.
- **Quy trình hoạt động:**
  1. Nhận câu hỏi từ Seller và nạp vào Agent Loop cùng với Memory (Short/Long-term).
  2. LLM tự động phân tích để xác định các thực thể: loại sản phẩm, thị trường đích, tiêu chí ưu tiên (giá rẻ nhất, ship nhanh nhất) và cấu hình mặt in (1 mặt, 2 mặt).
  3. Nếu thiếu tham số bắt buộc, LLM tự động nhận biết thông tin còn thiếu và tự tạo câu hỏi ngược lại cho seller để làm rõ.
  4. Nếu đủ thông tin, Agent gọi Tool Python Calculator tương ứng.
- **Xử lý ngoại lệ:** Nếu đầu vào không liên quan đến sản phẩm/fulfillment của BurgerPrints, Agent phản hồi linh hoạt từ chối và khéo léo định hướng lại người dùng.

#### F-2: Công Cụ Tính Toán Độc Lập (Python Calculation Engine)

- **Mô tả:** Để tránh LLM bị ảo giác khi tính toán các con số tài chính phức tạp, hệ thống bắt buộc sử dụng một engine Python riêng để tính toán chi phí trước khi nạp lại kết quả cho LLM phản hồi.
- **Quy thức tính toán:**
  - `Base Cost` = `price` lấy từ API (gồm 1 mặt in mặc định).
  - `Print Cost` = `2nd_price` (nếu in 2 mặt) hoặc `addition_price` (nếu in 3 mặt, nếu khác null).
  - `Shipping Fee` = Query từ Shipping Rate API dựa trên quốc gia nhận hàng và loại sản phẩm.
  - `Tax` = `(Base Cost + Print Cost + Shipping Fee) * Mức thuế cố định của quốc gia` (US = 8.25%, EU = 19%, VN = 10%).
  - `Landed Cost` = `Base Cost + Print Cost + Shipping Fee + Tax`.
  - `Margin` = `(Giá bán lẻ đề xuất - Landed Cost) / Giá bán lẻ đề xuất`.
- **Rủi ro SLA:** Đọc lịch sử vận đơn từ DB, tính toán số ngày lệch trung bình giữa ngày giao thực tế và ngày cam kết của từng xưởng in. Nếu độ lệch > 2 ngày, gán thẻ rủi ro "Cao", ngược lại là "Thấp".

#### F-3: Bảng So Sánh Candidate Table Trong Chat

- **Mô tả:** Trình bày kết quả so sánh xưởng dưới dạng bảng HTML/React nhúng trực tiếp trong chat bubble.
- **Các thông tin bắt buộc:** Tên xưởng, Base Cost, Print Cost, Shipping, Tax, Landed Cost, Margin %, Ship SLA, Rủi ro SLA, Nút hành động "Chọn Xưởng".
- **Giao diện:** Highlight hàng đầu tiên (xưởng tối ưu nhất theo cấu hình Preferences của Seller) bằng viền nổi bật và huy hiệu RECOMMENDED.

#### F-4: Product Inspector & Preview Mockup Lồng Ghép Thiết Kế

- **Mô tả:** Panel hiển thị trực quan sản phẩm đang cấu hình.
- **Yêu cầu:**
  - Đọc màu sắc và kích thước từ API sản phẩm để hiển thị swatch tròn chọn màu và các chip chọn size.
  - Tải lên ảnh thiết kế (mặt trước/mặt sau) thông qua link URL hoặc file upload (chuyển sang Base64 để hiển thị local).
  - Lồng ảnh thiết kế lên ngực/lưng mockup phôi áo để hiển thị bản preview sản xuất.
  - Cập nhật Billing Summary theo thời gian thực khi seller đổi tùy chọn (ví dụ: chuyển từ áo 1 mặt sang áo 2 mặt).

#### F-5: Giao Dịch Đặt Đơn Sandbox

- **Mô tả:** Xử lý gửi yêu cầu đặt đơn sandbox sang BurgerPrints API v2.0.
- **Yêu cầu:**
  - Gom dữ liệu bao gồm: Mã SKU phôi, màu sắc, size, link ảnh thiết kế mặt trước/sau, thông tin người nhận.
  - Gọi endpoint POST đơn hàng của BurgerPrints API v2.0 ở chế độ sandbox.
  - Nhận về thông tin đơn hàng thành công, hiển thị Order ID và mã vận đơn (Tracking number).
  - Ghi đơn hàng vào bảng dữ liệu đơn của SQLite nội bộ để lưu lịch sử.

#### F-6: Giao diện Chatbot Telegram & Quy trình Đặt hàng Hội thoại (Telegram Bot Adapter & Conversational Checkout)

- **Mô tả:** Bộ tương thích (Adapter) cho phép đồng bộ toàn bộ luồng hội thoại cốt lõi từ web sang ứng dụng nhắn tin Telegram.
- **Đặc tả chuyển đổi giao diện sang Telegram:**
  - **Bảng so sánh (Candidate Table) -> Text formatting & Inline Buttons:** Chuyển đổi bảng so sánh 10 cột phức tạp thành danh sách văn bản Markdown được định dạng sạch sẽ, ngắn gọn trên Telegram. Mỗi option đi kèm một nút bấm inline (ví dụ: `[Chọn Factory A - Landed Cost $10.5]`) để người dùng click nhanh.
  - **Mockup Display -> Server-side Image Composite:** Phía Backend sử dụng thư viện xử lý ảnh (ví dụ: Pillow/Canvas) để tự động ghép ảnh thiết kế của seller đè lên ảnh phôi sản phẩm thực tế, sau đó Telegram Bot sẽ gửi ảnh ghép này (.png/.jpg) kèm mô tả thông số kỹ thuật đến người dùng.
  - **Cấu hình sản phẩm (Inspector swatches) -> Inline Menus:** Cung cấp danh sách nút bấm tròn/swatch text để người dùng chọn màu sắc và kích thước (S, M, L, XL).
  - **Checkout Form -> Hội thoại hỏi đáp từng bước:** Thay thế các form nhập địa chỉ dài bằng luồng chatbot hỏi đáp từng bước (ví dụ: _"Vui lòng nhập Tên người nhận"_ -> _"Nhập Địa chỉ dòng 1"_...) hoặc sử dụng Telegram Web App (TWA) để mở form nhập liệu tối giản.
  - **Tóm tắt hóa đơn (Billing Summary) & Thanh toán:** Hiển thị bằng khối text tóm tắt chi phí rõ ràng và nút bấm Inline Keyboard `"Xác Nhận Đơn Hàng"`. Khi bấm, hệ thống thực hiện luồng đặt đơn sandbox và thông báo kết quả.

### 5.2. Các Tính Năng Ngoài Phạm Vi (Out of Scope - Không triển khai ở MVP)

- Tính năng tự động tạo thiết kế bằng AI (Generative AI Design Assistant).
- Tính năng tạo báo cáo marketing/sale dạng PDF/Excel.
- Dashboard tích hợp theo dõi đa cửa hàng (Shopify, Etsy, Amazon, TikTok Shop).

### 5.3. Kiến Trúc Bộ Nhớ & Quản Lý Phiên (Memory & Session Architecture)

Để đảm bảo Agent thông minh, ghi nhớ được ngữ cảnh dài hạn và tối ưu hóa chi phí token context window của LLM khi hội thoại kéo dài, hệ thống được thiết kế kiến trúc bộ nhớ phân lớp sau:

- **Bộ nhớ ngắn hạn (Short-term Conversation Memory):**
  - Sử dụng cơ chế lưu trữ lịch sử tin nhắn trong SQLite theo từng `Session ID` (Web Session hoặc Telegram Chat ID).
  - Sử dụng phương pháp **Sliding Window Buffer** (ví dụ: chỉ gửi 8-10 lượt hội thoại gần nhất kèm theo các system prompt cho LLM) để giữ cho chi phí token thấp và tốc độ xử lý nhanh.
- **Cơ chế Tóm Tắt Hội Thoại (Conversation Summarizer Worker):**
  - Khi lịch sử chat vượt quá giới hạn Token nhất định (ví dụ: > 3000 tokens), hệ thống sẽ kích hoạt một background task sử dụng LLM để tóm tắt (Summarize) toàn bộ nội dung hội thoại trước đó.
  - Bản tóm tắt này (Session Summary) sẽ được liên tục cập nhật và đưa vào System Prompt như là ngữ cảnh nền (Context Background), giúp Agent không bị "quên" những thỏa thuận/sản phẩm đã chốt từ các lượt chat cũ.
- **Bộ nhớ dài hạn (Long-term Profile Memory):**
  - Lưu trữ thông tin cá nhân của Seller, lịch sử đơn hàng đã đặt, và các cấu hình ưu tiên (Preferred Market, Lợi nhuận mục tiêu, SLA tối đa) lưu trong SQLite.
  - Cho phép Agent tự động đọc Preferences của Seller ngay khi phiên làm việc được khởi tạo để cá nhân hóa kết quả xếp hạng xưởng.

---

## 6. Technical Constraints (Ràng Buộc Kỹ Thuật)

### 6.1. Hiệu Năng & Tài Nguyên (Performance)

- **Tốc độ gọi API cục bộ:** Mọi truy vấn đọc Catalog sản phẩm đã được cache từ DB SQLite bắt buộc có phản hồi dưới **200ms**.
- **Cơ chế Sync dữ liệu:** Tiến trình nền (Background task) đồng bộ dữ liệu từ BurgerPrints API v2.0 về SQLite chạy định kỳ **5 giờ một lần**. Không thực hiện gọi API trực tiếp lấy catalog khi seller đang nhắn tin trừ khi cache trống.

### 6.2. Bảo Mật & Xác Thực (Security & Compliance)

- **Quản lý khóa API:** Tuyệt đối không lưu API Key của BurgerPrints trong database của client-side hoặc code. Khóa phải được nạp thông qua file `.env` trên môi trường docker-compose ở phía Backend server.
- **Mã hóa:** Thông tin tài khoản người dùng đăng nhập hệ thống được mã hóa password bằng thuật toán brypt trước khi lưu vào SQLite.

### 6.3. Khả Năng Tích Hợp (Integration) & Kiến Trúc SQLite Lai (Hybrid JSON/NoSQL Database)

- **BurgerPrints API v2.0:** Kết nối thông qua giao thức HTTPS RESTful API chuẩn (`https://api.burgerprints.com/`).
- **SQLite Database - Kiến trúc Lai (Hybrid):** Tách biệt logic nghiệp vụ thông qua lớp Repository Pattern. Hệ thống áp dụng cấu trúc lai:
  - **Bảng Tĩnh (Statically-typed Tables):** Các bảng nghiệp vụ tĩnh (`users`, `orders`, `chat_history`, `preferences`) được định nghĩa cứng bằng SQL Schema để Backend truy vấn an toàn và hiệu năng.
  - **Bảng Động (Dynamic JSON Documents):** Dữ liệu Catalog sản phẩm và Shipping rules từ BurgerPrints API được lưu trữ nguyên bản dưới dạng JSON (TEXT/JSON column trong SQLite).
- **Cơ chế Tự Phục Hồi Schema (Self-healing Schema Mapper):**
  - **First-run Mapping:** Trong lần chạy đầu tiên, hệ thống gọi LLM đọc response từ API BurgerPrints để sinh ra một file cấu hình mapping (JSON Mapping Metadata) định nghĩa các JSON path đến trường dữ liệu (ví dụ: `price` tương ứng với `$.price`).
  - **Normal Sync:** Các tiến trình đồng bộ (Background Sync) định kỳ ghi đè dữ liệu JSON thô trực tiếp vào DB SQLite mà không qua LLM để tối đa tốc độ và không tốn token.
  - **Tự Phục Hồi (Self-healing):** Khi cấu hình API BurgerPrints thay đổi (đổi tên trường JSON), Backend phát hiện lỗi Parse dữ liệu sẽ kích hoạt một Background LLM task. LLM đọc response mới, tự cập nhật lại file JSON Mapping Metadata để khôi phục hệ thống mà không cần chạy SQL Migration hay thay đổi cấu trúc bảng SQLite.

### 6.4. Công Nghệ Sử Dụng (Technology Stack)

- **Frontend/Client:** Next.js (React), CSS Vanilla (Glassmorphism), Telegram Bot API.
- **Backend:** FastAPI (Python 3.10+), SQLAlchemy, Pillow/OpenCV (xử lý hình ảnh mockup phía server).
- **Database:** SQLite (cực kỳ nhẹ) cho cấu hình & lịch sử chat, ChromaDB/FAISS (VectorDB cục bộ) cho Catalog RAG.
- **AI Engine:** **LangChain** (tự phát triển Agent Loop tùy biến, không sử dụng LangGraph) kết hợp API Gemini-3.1-flash-lite (hoặc model tự host chuẩn API OpenAI).
- **Đóng gói:** Dockerfile và docker-compose.yml.

---

## 7. MVP Scope & Phasing (Phân Kỳ Dự Án)

### 7.1. Giai đoạn 1 (MVP - Hiện tại)

- Thiết lập cơ sở dữ liệu SQLite và Repository Layer (tích hợp VectorDB local ChromaDB/FAISS).
- Xây dựng cơ chế lưu trữ SQLite Lai (lưu JSON thô cho Catalog và Schema Mapper).
- Viết task đồng bộ dữ liệu catalog/shipping định kỳ 5h và cập nhật VectorDB.
- Phát triển module tự phục hồi (Self-healing Schema Mapper) sử dụng LLM để sinh Mapping Metadata khi API thay đổi.
- Xây dựng FastAPI endpoints cung cấp dữ liệu tính toán Landed Cost và logic Memory (Sliding Window, Summarizer).
- Cấu hình **LangChain Custom Agent Loop** (không sử dụng LangGraph) để hỗ trợ LLM tự do suy nghĩ (CoT) và gọi Tool Python tính toán chính xác.
- Phát triển song song Giao diện Web Dashboard 3 cột và Giao diện Telegram Bot Adapter (hỗ trợ text-based checkout và dynamic mockup render).
- Kết nối luồng tạo đơn Sandbox API BurgerPrints.

### 7.2. Giai đoạn 2 (Post-MVP)

- Tích hợp thêm AI Design Generator hỗ trợ seller thiết kế ảnh in bằng văn bản trực tiếp trong chat.
- Nghiên cứu cơ chế đồng bộ thuế động thay thế flat rates hiện tại thông qua liên kết trực tiếp hệ thống BurgerPrints.

---

## 8. Risk Assessment (Đánh Giá Rủi Ro)

| Rủi Ro                                                                                             | Khả Năng Xảy Ra | Mức Độ Ảnh Hưởng | Biện Pháp Giảm Thiểu                                                                                                     |
| :------------------------------------------------------------------------------------------------- | :-------------- | :--------------- | :----------------------------------------------------------------------------------------------------------------------- |
| **API Rate Limits:** BurgerPrints API v2.0 giới hạn số lần gọi trên phút trong mùa cao điểm.       | Trung bình      | Cao              | Tối ưu hóa tối đa SQLite cache để hạn chế gọi API Catalog trực tiếp; chỉ gọi API khi tính shipping thực tế và checkout.  |
| **LLM Ảo Giác Số Liệu:** AI tính toán sai Landed Cost hoặc Margin dẫn đến seller bị lỗ.            | Cao             | Nghiêm trọng     | Nghiêm cấm LLM tự tính toán số. Bắt buộc chuyển toàn bộ biến giá vào Python Engine để trả ra con số chuẩn xác tuyệt đối. |
| **Trải nghiệm bảng biểu trên di động:** Bảng Candidate Table 10 cột bị vỡ khung trên màn hình nhỏ. | Cao             | Trung bình       | Tích hợp responsive thiết kế ẩn cột phụ hoặc chuyển sang dạng Card View vuốt ngang trên thiết bị di động.                |

---

## 9. Dependencies & Blockers (Phụ Thuộc & Điểm Nghẽn)

- **Phụ thuộc (Dependencies):**
  - Cần tài khoản sandbox và API Credentials hợp lệ từ ban tổ chức/BurgerPrints để chạy thử nghiệm các endpoint thực tế.
  - Phụ thuộc vào tốc độ phản hồi của API Shipping Rate của BurgerPrints để tính Landed Cost thời gian thực.
- **Điểm nghẽn (Blockers):**
  - Nếu API Sandbox của BurgerPrints bị bảo trì hoặc lỗi, luồng checkout sẽ bị gián đoạn. Cần xây dựng sẵn mock server giả lập API Order để phòng ngừa.

---

_Tài liệu PRD này được xây dựng tuân thủ đầy đủ các tiêu chí kỹ thuật và nghiệp vụ cốt lõi, sẵn sàng chuyển sang giai đoạn phát triển mã nguồn._
