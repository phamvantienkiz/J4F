# USER FLOW & CONVERSATION FLOW: BURGERPRINTS AGENT

Tài liệu này đặc tả luồng người dùng (User Flow) và luồng hội thoại mẫu (Conversation Flow) của trợ lý **BurgerPrints Agent** khi hỗ trợ Seller. Các kịch bản dưới đây được xây dựng dựa trên các tiêu chuẩn chất lượng của skill [user-story-writer.md](file:///E:/Hackathon2026/J4F/.agents/skills/user-story-writer.md) nhằm đảm bảo tính khả thi, dễ kiểm thử và mang lại giá trị thực tế cao nhất cho Seller.

Tài liệu này được thiết kế thống nhất và liên kết chặt chẽ với [Solution Overview](file:///E:/Hackathon2026/J4F/Solution/docs/ai/solution_overview.md), [System Architecture](file:///E:/Hackathon2026/J4F/Solution/docs/ai/system_architecture.md), và [Agent Design Specification](file:///E:/Hackathon2026/J4F/Solution/docs/ai/agent_design_specification.md).

---

## 1. Nguyên Tắc Thiết Kế Hội Thoại (Conversation Design Principles)

Để tạo ra trải nghiệm "Wow" cho Seller và tối đa hóa cơ hội đạt giải tại Hackathon, BurgerPrints Agent tuân thủ 3 nguyên tắc thiết kế hội thoại:
1.  **Lấy quyết định làm trung tâm (Decision-Centric):** Mọi câu trả lời của Agent không chỉ dừng lại ở cung cấp thông tin thô, mà phải được xử lý, xếp hạng, và đưa ra gợi ý hành động tiếp theo rõ ràng để Seller chốt đơn ngay lập tức.
2.  **Kế thừa thông minh (Context Inheritance):** Sử dụng thông tin từ bộ nhớ dài hạn (Preferences Memory) để điền tự động các tham số lọc, hạn chế tối đa việc hỏi đi hỏi lại Seller những thông tin trùng lặp.
3.  **Hội thoại kết hợp giao diện động (Hybrid UX):** Kết hợp chặt chẽ giữa khung chat và các khối hiển thị đồ họa (Bảng so sánh xưởng in, Panel điều kiện lọc constraints) trên giao diện Streamlit UI để tăng tính trực quan.

---

## 2. Scenario 01: Tìm kiếm T-Shirt tối ưu cho thị trường US (Find Best T-Shirt)

### 2.1. User Story

**US-001**: Tìm kiếm sản phẩm áo thun tối ưu
*   **As a** POD Seller đang tập trung bán hàng tại thị trường US.
*   **I want to** tìm kiếm sản phẩm áo thun (T-shirt) có giá landed cost tốt nhất và thời gian giao hàng dưới 7 ngày.
*   **So that** tôi có thể tối ưu hóa lợi nhuận (margin mục tiêu 40%) và đảm bảo độ hài lòng của khách hàng mua hàng tại Mỹ.

#### Bảng INVEST Self-check:
| Tiêu chí | Đánh giá | Chi tiết |
| :--- | :---: | :--- |
| **I**ndependent | ✅ | Story này độc lập với việc quản lý tài khoản hay thanh toán. |
| **N**egotiable | ✅ | Không ràng buộc cứng thuật toán xếp hạng, cho phép Agent tự động đề xuất dựa trên điểm số. |
| **V**aluable | ✅ | Giúp Seller tiết kiệm 30 phút tìm kiếm và tính toán chi phí xưởng in thủ công. |
| **E**stimable | ✅ | Dev hoàn toàn ước lượng được nhờ các API catalog có sẵn của BurgerPrints. |
| **S**mall | ✅ | Chỉ tập trung vào việc tìm kiếm và lọc sản phẩm T-shirt, không bao gồm đặt hàng. |
| **T**estable | ✅ | QA có thể viết test case kiểm chứng các thông số trả ra có thỏa mãn giá và SLA không. |

### 2.2. Acceptance Criteria (Given-When-Then)

*   **AC1.1: Tìm kiếm thành công với đầy đủ thông số lọc (Happy Path)**
    *   **Given** Seller đang mở cửa sổ chat và hệ thống đã tải preferences mặc định (Market: US).
    *   **When** Seller gửi tin nhắn: *"Tôi muốn bán T-shirt cho thị trường Mỹ, giá vốn dưới $8, ship dưới 5 ngày, chọn xưởng nào, SKU nào?"*.
    *   **Then** Agent bóc tách thành công các slots `{product_type: "T-shirt", market: "US", max_cogs: 8.00, max_shipping_days: 5}`.
    *   **And** Gọi BurgerPrints API v2.0 thời gian thực để lấy danh sách xưởng và báo giá thô.
    *   **And** Tính toán Landed Cost, SLA ngày ship bằng Python Pricing Engine và hiển thị bảng so sánh Top 3 xưởng.
*   **AC1.2: Kế thừa margin từ preferences (Edge Case)**
    *   **Given** Seller không khai báo margin mục tiêu trong câu hỏi.
    *   **When** Agent kiểm tra thấy `user_preferences` có lưu `target_margin = 40.0`.
    *   **Then** Agent tự động sử dụng con số 40.0% này để tính toán giá bán đề xuất của từng phương án mà không cần hỏi lại Seller.
*   **AC1.3: Cân nhắc đánh đổi khi không có phương án hoàn hảo (Negative Path)**
    *   **Given** Seller yêu cầu mức giá trần landed cost quá thấp (dưới $8) và ship nhanh dưới 5 ngày.
    *   **When** Pricing Engine tính toán thấy các xưởng nội địa US đáp ứng ship < 5 ngày đều có giá vốn từ $8.50 trở lên, còn xưởng VN giá $7.20 nhưng ship 10-12 ngày.
    *   **Then** Agent không báo lỗi sập, mà trả về bảng so sánh và giải trình trade-off: Khuyên dùng xưởng US ($8.50) vì sát ngân sách nhất và đạt SLA giao hàng dưới 5 ngày, thay vì chọn VN ($7.20) bị chậm.

### 2.3. Conversation Script (Luồng hội thoại thực tế)

*   **User:** *"Tôi muốn bán T-shirt cho thị trường Mỹ, giá vốn dưới $8, ship dưới 5 ngày, chọn xưởng nào, SKU nào?"*
*   **System (Constraints Panel):** Cập nhật hiển thị:
    *   *Product:* T-Shirt
    *   *Market:* US
    *   *Max Price:* $8.00
    *   *Max Ship Days:* 5 ngày
    *   *Target Margin:* 40% (Kế thừa từ preferences)
*   **Agent:** *"Em đã tìm thấy 3 phương án tối ưu tại thị trường US từ BurgerPrints API. Dưới đây là bảng so sánh:"*
*   **System (Comparison Panel - UI):**
    | Tiêu chí | Option 1 (Khuyên dùng) | Option 2 (Giá rẻ nhất) | Option 3 (Ship nhanh nhất) |
    | :--- | :--- | :--- | :--- |
    | **Xưởng in** | SwiftPrint (US) | GlobalPrint (VN) | ExpressInk (US) |
    | **Landed Cost** | $8.50 | **$7.20** | $9.20 |
    | **Thời gian Ship** | **4 - 5 ngày** | 10 - 12 ngày | **2 - 3 ngày** |
    | **SKU gợi ý** | `BP-TS-SWIFT-M` | `BP-TS-GLOBAL-M` | `BP-TS-EXPRESS-M` |
    | **Giá bán gợi ý** | $14.20 | $12.00 | $15.30 |
    | **Dự kiến Margin** | **40.1%** | 40.0% | 40.0% |
*   **Agent:** 
    *   *Giải trình:* Option 1 từ xưởng SwiftPrint (US) là tối ưu nhất. Dù giá vốn ($8.50) cao hơn $0.50 so với ngân sách của bạn, đây là xưởng duy nhất có giá gần mức $8 nhất đáp ứng được thời gian giao hàng 4-5 ngày. Option 2 (xưởng VN) rẻ nhất ($7.20) nhưng thời gian giao hàng 10-12 ngày không đạt yêu cầu dưới 5 ngày.
    *   *Gợi ý hành động:* *"Bạn có muốn đặt đơn nháp cho Option 1 không, hay muốn xem thêm xưởng khác?"*

---

## 3. Scenario 02: So sánh sản phẩm Hoodie giữa các xưởng (Compare Hoodie)

### 3.1. User Story

**US-002**: So sánh xưởng in cho sản phẩm Hoodie
*   **As a** POD Seller.
*   **I want to** so sánh chi tiết các lựa chọn sản xuất Hoodie giữa xưởng nội địa US và xưởng tại Việt Nam gửi sang US.
*   **So that** tôi có thể cân nhắc đánh đổi (trade-off) giữa giá vốn (Landed Cost) và tốc độ vận chuyển giao hàng (SLA).

#### Bảng INVEST Self-check:
| Tiêu chí | Đánh giá | Chi tiết |
| :--- | :---: | :--- |
| **I**ndependent | ✅ | Story này chỉ xử lý nghiệp vụ hiển thị so sánh. |
| **N**egotiable | ✅ | Có thể tùy biến thuật toán so sánh tùy theo ưu tiên của Seller. |
| **V**aluable | ✅ | Giúp Seller đưa ra quyết định kinh doanh chiến lược (chọn giá rẻ hay chọn ship nhanh). |
| **E**stimable | ✅ | Ước lượng dễ dàng vì các tham số đầu vào của Hoodie tương tự T-shirt. |
| **S**mall | ✅ | Nằm gọn trong một lượt tương tác phân tích đối chiếu. |
| **T**estable | ✅ | Có thể kiểm thử bằng cách thay đổi giá bán để kiểm tra margin biến động tương ứng. |

### 3.2. Acceptance Criteria (Given-When-Then)

*   **AC2.1: Hiển thị so sánh đối chiếu xưởng in ship EU (Happy Path)**
    *   **Given** Seller muốn bán sản phẩm Hoodie sang thị trường Châu Âu (EU).
    *   **When** Seller gửi tin nhắn: *"So sánh giá Hoodie giữa các xưởng đang có, xưởng nào ship EU rẻ nhất?"*.
    *   **Then** Agent gọi API lấy thông tin xưởng in và phí ship sang quốc gia EU đại diện (ví dụ: Đức).
    *   **And** Tính toán Landed Cost, xếp hạng và làm nổi bật xưởng in có tổng landed cost rẻ nhất khi ship sang EU.
*   **AC2.2: Lọc theo quốc gia EU cụ thể (Edge Case)**
    *   **Given** Bảng so sánh hiển thị phí ship EU chung.
    *   **When** Seller gõ: *"Xem phí ship cụ thể tới Pháp"*.
    *   **Then** Agent gọi lại API lấy quote ship của các xưởng tới địa chỉ ở Pháp, cập nhật lại bảng so sánh ngay lập tức.
*   **AC2.3: Lỗi kết nối BurgerPrints API (Negative Path)**
    *   **Given** Trực tiếp gọi API BurgerPrints gặp lỗi 500 hoặc timeout.
    *   **Then** Agent trả về thông báo rõ ràng cho Seller và khuyên thử lại sau, tuyệt đối không bịa số liệu: *"Hiện kết nối đến BurgerPrints API đang gặp sự cố. Bạn vui lòng thử lại sau vài giây."*

### 3.3. Conversation Script (Luồng hội thoại thực tế)

*   **User:** *"So sánh giá Hoodie giữa các xưởng đang có, xưởng nào ship EU rẻ nhất?"*
*   **System (Constraints Panel):** Cập nhật hiển thị:
    *   *Product:* Hoodie
    *   *Color:* Grey
    *   *Size:* XL
    *   *Market:* US
*   **Agent:** *"Em đã phân tích dữ liệu từ xưởng nội địa US và xưởng sản xuất tại Việt Nam vận chuyển sang US. Dưới đây là bảng so sánh đối chiếu:"*
*   **System (Comparison Panel - UI):**
    | Tiêu chí | Phương án A (Xưởng US) | Phương án B (Xưởng VN) |
    | :--- | :--- | :--- |
    | **Tên xưởng** | Texas Apparel Lab (US) | Saigon Print & Co (VN) |
    | **Base Cost** | $14.50 | **$10.20** |
    | **Ship Cost (đi US)**| **$6.20** (Nội địa US) | $12.50 (Xuyên biên giới) |
    | **Landed Cost** | **$20.70** | $22.70 |
    | **Thời gian Ship** | **3 - 5 ngày** | 12 - 15 ngày |
    | **Điểm tin cậy (SLA)**| **98.2%** | 89.5% |
*   **Agent:**
    *   *Giải trình:* Trong trường hợp sản phẩm Hoodie XL này, **Phương án A (Xưởng US) chiếm ưu thế tuyệt đối**. Dù xưởng Việt Nam có giá sản xuất rẻ hơn ($10.20 so với $14.50), nhưng phí ship xuyên biên giới quá cao ($12.50) dẫn tới landed cost của phương án VN đắt hơn phương án US $2.00, đồng thời thời gian giao hàng lâu hơn 10 ngày.
    *   *Gợi ý hành động:* *"Em khuyên bạn nên chọn Phương án A (Texas Apparel Lab). Bạn có muốn đặt thử đơn nháp không?"*

---

## 4. Scenario 03: Gợi ý sản phẩm phù hợp theo giá bán và margin mục tiêu (Find Product by Margin)

### 4.1. User Story

**US-003**: Gợi ý sản phẩm dựa trên Margin và Giá bán lẻ
*   **As a** POD Seller muốn lên kế hoạch bán sản phẩm mới với mức giá bán lẻ cố định.
*   **I want to** yêu cầu gợi ý sản phẩm phù hợp với mức giá bán lẻ và margin tối thiểu mong muốn.
*   **So that** tôi có thể tìm ra dòng sản phẩm sinh lời tốt nhất và đáp ứng được chi phí quảng cáo.

#### Bảng INVEST Self-check:
| Tiêu chí | Đánh giá | Chi tiết |
| :--- | :---: | :--- |
| **I**ndependent | ✅ | Độc lập, chỉ yêu cầu tính toán logic ngược và truy vấn danh mục. |
| **N**egotiable | ✅ | Trọng số đề xuất có thể ưu tiên theo doanh số bán chạy hoặc giá base. |
| **V**aluable | ✅ | Giúp Seller định hướng dòng sản phẩm ngay lập tức khi biết giá thị trường. |
| **E**stimable | ✅ | Khả thi nhờ thuật toán tính ngược giá vốn tối đa từ margin và retail price. |
| **S**mall | ✅ | Nằm gọn trong nghiệp vụ đề xuất danh sách phù hợp. |
| **T**estable | ✅ | Cực kỳ dễ test bằng cách nhân % margin với giá bán lẻ xem có ra landed cost khớp không. |

### 4.2. Acceptance Criteria (Given-When-Then)

*   **AC3.1: Đề xuất thành công các dòng sản phẩm đạt margin (Happy Path)**
    *   **Given** Seller nhập giá bán lẻ và margin mục tiêu.
    *   **When** Seller nhắn: *"Tôi định bán giá $24.99, margin tối thiểu 40%, gợi ý sản phẩm phù hợp."*.
    *   **Then** Agent tính ngược giá vốn tối đa (Max Landed Cost = $24.99 * (1 - 0.40) = $14.99).
    *   **And** Gọi BurgerPrints API lấy danh mục sản phẩm có landed cost (bao gồm cả phí ship US trung bình) dưới $14.99.
    *   **And** Trả về danh sách Top 3 sản phẩm đạt tiêu chuẩn kèm theo tính toán margin thực tế.
*   **AC3.2: Không tìm thấy sản phẩm nào đạt margin mong muốn (Edge Case)**
    *   **Given** Seller đặt margin quá cao so với giá bán lẻ thấp (ví dụ: bán $10, margin 80% -> giá vốn tối đa $2).
    *   **When** Không có sản phẩm nào có landed cost dưới $2.
    *   **Then** Agent thông báo lịch sự: *"Không tìm thấy sản phẩm nào có tổng landed cost (gồm ship) dưới $2.00. Sản phẩm có giá vốn thấp nhất hiện tại là Cốc sứ (Mug) với landed cost $9.20 (mang lại margin 8.0% ở mức giá bán $10)."*

### 4.3. Conversation Script (Luồng hội thoại thực tế)

*   **User:** *"Tôi định bán giá $24.99, margin tối thiểu 40%, gợi ý sản phẩm phù hợp."*
*   **System (Constraints Panel):** Cập nhật hiển thị:
    *   *Selling Price:* $24.99
    *   *Target Margin:* 40%
    *   *Max Landed Cost Target:* $14.99
*   **Agent:** *"Để đạt margin tối thiểu 40% ở mức giá bán lẻ $24.99, giá vốn (landed cost) của sản phẩm phải dưới $14.99. Dưới đây là 3 dòng sản phẩm phù hợp nhất từ BurgerPrints API:"*
*   **System (Comparison Panel - UI):**
    | Dòng sản phẩm | Xưởng đề xuất | Landed Cost trung bình (ship US) | Dự kiến Margin thực tế | Đánh giá tiềm năng |
    | :--- | :--- | :--- | :--- | :--- |
    | **1. Unisex Cotton T-Shirt** | SwiftPrint (US) | $8.50 | **66.0%** (Margin cao, dễ bán) | Rất cao |
    | **2. Ceramic Mug (11oz)** | Detroit Pottery (US) | $9.20 | **63.2%** (Phù hợp bán quà tặng) | Cao |
    | **3. Canvas Tote Bag** | GlobalPrint (VN) | $12.80 | **48.8%** (Đã gồm ship xuyên biên giới) | Trung bình |
*   **Agent:** 
    *   *Giải trình:* Cả 3 dòng sản phẩm trên đều đạt mức margin mong muốn của bạn (>40%). Trong đó, **Unisex Cotton T-Shirt** mang lại margin cao nhất (66.0%) và là sản phẩm bán chạy nhất.
    *   *Gợi ý hành động:* *"Bạn muốn đi sâu xem báo giá chi tiết của dòng sản phẩm nào ở trên?"*

---

## 5. Scenario 04: Xác nhận & Tạo đơn hàng (Create Order)

### 5.1. User Story

**US-004**: Đặt đơn hàng POD
*   **As a** POD Seller đã chốt được phương án sản xuất tối ưu.
*   **I want to** xác nhận thông tin đơn hàng và gửi yêu cầu tạo đơn hàng lên BurgerPrints.
*   **So that** đơn hàng của tôi được chuyển ngay vào quy trình sản xuất và vận chuyển tới khách hàng.

#### Bảng INVEST Self-check:
| Tiêu chí | Đánh giá | Chi tiết |
| :--- | :---: | :--- |
| **I**ndependent | ⚠️ | Phụ thuộc vào việc đã tìm và chọn được biến thể SKU từ các Scenario trước. |
| **N**egotiable | ✅ | Cho phép Seller sửa thông tin địa chỉ hoặc số lượng ở bước xác nhận nháp. |
| **V**aluable | ✅ | Hoàn thành vòng lặp hành động (Action Execution) của Agent, tăng tính thực tiễn. |
| **E**stimable | ✅ | Thực hiện qua API POST `/orders` chuẩn của BurgerPrints. |
| **S**mall | ✅ | Chỉ bao gồm tạo đơn và trả mã tracking, không quản lý ví tiền hay thanh toán sâu. |
| **T**estable | ✅ | Dễ kiểm thử bằng cách verify trạng thái đơn hàng trên API Sandbox. |

### 5.2. Acceptance Criteria (Given-When-Then)

*   **AC4.1: Xác nhận và tạo đơn hàng thành công (Happy Path)**
    *   **Given** Agent đang lưu thông tin đơn hàng nháp ở `order_draft` (SKU: `BP-TS-SWIFT-M`, Xưởng: SwiftPrint).
    *   **When** Seller click nút "Confirm Fulfillment Order" trên Right Panel hoặc gõ chat: *"Chốt tạo đơn cho David Miller, 742 Evergreen Terrace, Springfield, IL, 62704, US"*.
    *   **Then** Agent gọi API `create_order` thành công.
    *   **And** Trả về mã đơn hàng `#BP-88776655`, mã vận đơn tracking `USPS-9400100000000000000000`, và hiển thị giao diện thành công.
*   **AC4.2: Phát hiện sai sót địa chỉ giao hàng (Edge Case)**
    *   **Given** Người dùng cung cấp địa chỉ giao hàng thiếu Zip Code.
    *   **When** Agent chạy logic validate địa chỉ trước khi call API.
    *   **Then** Agent chặn tiến trình gửi API và phản hồi: *"Địa chỉ của khách hàng thiếu Zip Code tại bang Illinois. Bạn vui lòng bổ sung Zip Code để em tạo đơn hàng."*
*   **AC4.3: Lỗi Out-of-stock từ xưởng in (Negative Path)**
    *   **Given** Xưởng in đột ngột hết phôi size M.
    *   **When** Agent gọi API tạo đơn và nhận về lỗi HTTP 422 (Out of stock).
    *   **Then** Agent thông báo rõ lỗi cho Seller.
    *   **And** Tự động đề xuất xưởng thay thế khả dụng còn phôi gần nhất.

### 5.3. Conversation Script (Luồng hội thoại thực tế)

*   **User:** *"Chốt đơn Option 1 (SwiftPrint) gửi cho khách: David Miller, 742 Evergreen Terrace, Springfield, IL, US. Số lượng: 1 chiếc."*
*   **System (Constraints Panel):** Chuyển sang trạng thái khóa đơn (Locked).
*   **Agent:** *"Em đã kiểm tra và xác nhận thông tin đơn hàng nháp:"*
*   **System (Right Panel - Order HUD):**
    *   **Sản phẩm:** Unisex Cotton T-Shirt (Size M)
    *   **Nhà in:** SwiftPrint (US)
    *   **Khách hàng:** David Miller
    *   **Địa chỉ:** 742 Evergreen Terrace, Springfield, IL, US
    *   **Landed Cost dự kiến:** $8.50
    *   ⚠️ *Cảnh báo:* Thiếu ZIP code giao hàng tại bang Illinois (IL).
*   **Agent:** *"Địa chỉ giao hàng hiện thiếu Zip Code tại bang Illinois. Bạn vui lòng cung cấp mã Zip Code để em hoàn tất tạo đơn hàng."*
*   **User:** *"Zip code là 62704."*
*   **Agent:** *"Thông tin địa chỉ đã hợp lệ (Zip Code: 62704). Em tiến hành gửi đơn lên BurgerPrints..."*
*   *(Hệ thống gọi API `create_order`)*
*   **Agent:** *"Đặt đơn hàng thành công! Dưới đây là thông tin vận đơn:"*
*   **System (Right Panel - Order Confirmation HUD):**
    *   🎉 **Mã đơn hàng:** `#BP-88776655`
    *   **Trạng thái:** `Pending Fulfillment` (Đang chờ in)
    *   **Mã vận đơn:** `USPS-9400100000000000000000`
    *   **Link theo dõi:** [Track Order](https://tools.usps.com/go/TrackConfirmAction?tLabels=9400100000000000000000)
*   **Agent:** *"Đơn hàng đã được ghi nhận vào hệ thống. Bạn có cần em hỗ trợ gì thêm không?"*
