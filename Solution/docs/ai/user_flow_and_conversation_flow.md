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
    *   **When** Seller gửi tin nhắn: *"Tìm áo Unisex T-shirt màu đen giá landed cost dưới $15, ship đi Mỹ"*.
    *   **Then** Agent bóc tách thành công các slots `{product_type: "Unisex T-shirt", color: "black", max_cogs: 15.00, market: "US"}`.
    *   **And** Gọi API lấy báo giá và tính toán landed cost bằng Pricing Engine.
    *   **And** Hiển thị bảng so sánh Top 3 xưởng và cập nhật Constraints Panel ở thanh Sidebar.
*   **AC1.2: Thiết lập margin mục tiêu tự động (Edge Case)**
    *   **Given** Seller không khai báo margin mục tiêu trong câu hỏi.
    *   **When** Agent kiểm tra và thấy `user_preferences` có lưu `target_margin = 40.0`.
    *   **Then** Agent tự động sử dụng con số 40.0% này để tính toán giá bán đề xuất của từng phương án mà không cần hỏi lại Seller.
*   **AC1.3: Không tìm thấy sản phẩm đáp ứng ràng buộc chi phí (Negative Path)**
    *   **Given** Seller yêu cầu mức giá trần landed cost quá thấp (ví dụ: dưới $5 cho T-shirt in ship US).
    *   **When** Pricing Engine tính toán thấy landed cost thấp nhất của các xưởng là $9.50.
    *   **Then** Agent không báo lỗi sập hệ thống, mà trả về phản hồi: *"Hiện không có xưởng nào đáp ứng landed cost dưới $5. Phương án rẻ nhất em tìm thấy là $9.50 từ xưởng GlobalPrint (VN) với thời gian ship 12 ngày. Bạn có muốn điều chỉnh ngân sách không?"*

### 2.3. Conversation Script (Luồng hội thoại thực tế)

*   **User:** *"Tìm cho mình áo Unisex T-shirt màu đen gửi đi thị trường US, giá landed cost trần là $13."*
*   **System (Constraints Panel):** Cập nhật hiển thị:
    *   *Product:* Unisex T-Shirt
    *   *Color:* Black
    *   *Market:* US
    *   *Max Landed Cost:* $13.00
    *   *Target Margin:* 40% (Kế thừa từ bộ nhớ thiết lập của Seller)
*   **Agent:** *"Em đã tìm thấy 3 phương án tối ưu đáp ứng yêu cầu của bạn tại thị trường US. Dưới đây là bảng so sánh:"*
*   **System (Comparison Panel - UI):**
    | Tiêu chí | Option 1 (Khuyên dùng) | Option 2 (Giá rẻ nhất) | Option 3 (Ship nhanh nhất) |
    | :--- | :--- | :--- | :--- |
    | **Xưởng in** | SwiftPrint (US) | GlobalPrint (VN) | ExpressInk (US) |
    | **Landed Cost** | $11.50 | **$9.80** | $12.80 |
    | **Thời gian Ship** | 4 - 6 ngày | 10 - 14 ngày | **2 - 3 ngày** |
    | **Giá bán gợi ý** | $19.20 | $16.30 | $21.30 |
    | **Dự kiến Margin** | **40.1%** | 40.0% | 40.0% |
*   **Agent:** 
    *   *Giải trình:* Option 1 từ xưởng SwiftPrint (US) là tối ưu nhất vì sản xuất ngay tại Mỹ, thời gian giao hàng 4-6 ngày đảm bảo SLA dưới 7 ngày của bạn, landed cost $11.50 (nằm dưới ngân sách $13) mang lại margin 40.1%.
    *   *Gợi ý hành động:* *"Bạn có muốn chốt Option 1 không, hay cần đổi sang EU market?"*

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

*   **AC2.1: Hiển thị so sánh đối chiếu xưởng in (Happy Path)**
    *   **Given** Seller đang muốn bán sản phẩm Hoodie.
    *   **When** Seller gửi tin nhắn: *"So sánh cho mình xưởng in Hoodie gửi đi Mỹ giữa xưởng Mỹ và xưởng Việt Nam"*.
    *   **Then** Agent truy xuất dữ liệu quotes của 2 nhóm xưởng US và VN.
    *   **And** Pricing Engine tính toán landed cost bao gồm giá base cost sản phẩm, phí in hai mặt (nếu có) và phí vận chuyển xuyên biên giới (đối với xưởng VN).
    *   **And** Hiển thị bảng so sánh làm nổi bật sự chênh lệch chi phí và thời gian giao hàng.
*   **AC2.2: Thay đổi ưu tiên tối ưu hóa giữa chừng (Edge Case)**
    *   **Given** Bảng so sánh đang được hiển thị với ưu tiên mặc định là "tối ưu lợi nhuận" (margin).
    *   **When** Seller nhắn: *"Mình cần ship cực nhanh trước Giáng Sinh, hãy xếp hạng lại theo tốc độ"*.
    *   **Then** Agent thay đổi trọng số trong hàm Scoring Function (`fulfillment_priority = 'speed'`).
    *   **And** Cập nhật lại thứ tự xếp hạng trên bảng so sánh, đẩy xưởng ExpressInk (US) lên vị trí số 1 thay vì xưởng giá rẻ của VN.
*   **AC2.3: API xưởng in Việt Nam bị lỗi (Negative Path)**
    *   **Given** Kết nối mạng sang xưởng VN bị gián đoạn.
    *   **When** Agent gọi API lấy quote xưởng VN bị timeout.
    *   **Then** Agent tự động truy xuất dữ liệu báo giá gần nhất đã được lưu trong SQLite Cache.
    *   **And** Hiển thị ghi chú cảnh báo: *"Dữ liệu báo giá xưởng VN là dữ liệu ước tính từ hệ thống lưu trữ (cập nhật 2 giờ trước)."*

### 3.3. Conversation Script (Luồng hội thoại thực tế)

*   **User:** *"So sánh hộ mình xưởng in Hoodie màu xám size XL gửi đi Mỹ giữa xưởng Mỹ và xưởng Việt Nam."*
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

## 4. Scenario 03: Xác nhận & Tạo đơn hàng (Create Order)

### 4.1. User Story

**US-003**: Tạo đơn hàng POD
*   **As a** POD Seller đã chốt được phương án sản xuất tối ưu.
*   **I want to** xác nhận thông tin đơn hàng và gửi yêu cầu tạo đơn hàng lên BurgerPrints.
*   **So that** đơn hàng của tôi được chuyển ngay vào quy trình sản xuất và vận chuyển tới khách hàng.

#### Bảng INVEST Self-check:
| Tiêu chí | Đánh giá | Chi tiết |
| :--- | :---: | :--- |
| **I**ndependent | ⚠️ | Phụ thuộc vào việc đã tìm và chọn được biến thể SKU từ Scenario 01/02. |
| **N**egotiable | ✅ | Cho phép Seller sửa thông tin địa chỉ hoặc số lượng ở bước xác nhận nháp. |
| **V**aluable | ✅ | Hoàn thành vòng lặp hành động (Action Execution) của Agent, tăng tính thực tiễn. |
| **E**stimable | ✅ | Thực hiện qua API POST `/orders` chuẩn của BurgerPrints. |
| **S**mall | ✅ | Chỉ bao gồm tạo đơn và trả mã tracking, không quản lý ví tiền hay thanh toán sâu. |
| **T**estable | ✅ | Dễ kiểm thử bằng cách verify trạng thái đơn hàng trên API Sandbox. |

### 4.2. Acceptance Criteria (Given-When-Then)

*   **AC3.1: Xác nhận và tạo đơn hàng thành công (Happy Path)**
    *   **Given** Agent đang lưu thông tin đơn hàng nháp ở `order_draft` (SKU: `BP-HD-GRY-XL`, Xưởng: Texas Apparel Lab).
    *   **When** Seller gõ chat: *"Chốt tạo đơn cho David Miller, 742 Evergreen Terrace, Springfield, IL, 62704, US"* hoặc click nút "Confirm Order" trên Streamlit UI.
    *   **Then** Agent gọi API `create_order` thành công.
    *   **And** Trả về mã đơn hàng `bp_ord_88776655`, mã vận đơn tracking `9400100000000000000000`, và thông báo thành công.
*   **AC3.2: Phát hiện sai sót địa chỉ giao hàng (Edge Case)**
    *   **Given** Người dùng cung cấp địa chỉ giao hàng thiếu Zip Code.
    *   **When** Agent chạy logic validate địa chỉ trước khi call API.
    *   **Then** Agent chặn tiến trình gửi API và phản hồi: *"Địa chỉ của khách hàng thiếu Zip Code tại bang Illinois. Bạn vui lòng bổ sung Zip Code để em tạo đơn hàng."*
*   **AC3.3: Lỗi Out-of-stock từ xưởng in (Negative Path)**
    *   **Given** Xưởng Texas Apparel Lab đột ngột hết phôi áo xám size XL.
    *   **When** Agent gọi API tạo đơn và nhận về lỗi HTTP 422 (Out of stock).
    *   **Then** Agent thông báo rõ lỗi cho Seller.
    *   **And** Tự động đề xuất xưởng thay thế khả dụng (ví dụ: xưởng ExpressInk US với landed cost $21.50).

### 4.3. Conversation Script (Luồng hội thoại thực tế)

*   **User:** *"Chốt đơn Option A (Texas Apparel Lab) gửi cho khách: David Miller, 742 Evergreen Terrace, Springfield, IL, US. Số lượng: 1 chiếc."*
*   **System (Constraints Panel):** Chuyển sang trạng thái khóa đơn (Locked).
*   **Agent:** *"Em đã kiểm tra và xác nhận thông tin đơn hàng nháp:"*
*   **System (Order Draft Panel - UI):**
    *   **Sản phẩm:** Grey Hoodie (Size XL)
    *   **Nhà in:** Texas Apparel Lab (US)
    *   **Khách hàng:** David Miller
    *   **Địa chỉ:** 742 Evergreen Terrace, Springfield, IL, US
    *   **Landed Cost dự kiến:** $20.70
    *   ⚠️ *Cảnh báo:* Thiếu ZIP code giao hàng tại bang Illinois (IL).
*   **Agent:** *"Địa chỉ giao hàng hiện thiếu Zip Code tại bang Illinois. Bạn vui lòng cung cấp mã Zip Code để em hoàn tất tạo đơn hàng."*
*   **User:** *"Zip code là 62704."*
*   **Agent:** *"Thông tin địa chỉ đã hợp lệ (Zip Code: 62704). Em tiến hành gửi đơn lên BurgerPrints..."*
*   *(Hệ thống gọi API `create_order`)*
*   **Agent:** *"Đặt đơn hàng thành công! Trực quan thông tin đơn hàng:"*
*   **System (Order Confirmation UI):**
    *   🎉 **Mã đơn hàng:** `#BP-88776655`
    *   **Trạng thái:** `Pending Fulfillment` (Đang chờ xử lý in)
    *   **Mã vận đơn:** `USPS-9400100000000000000000`
    *   **Link theo dõi:** [Track Order](https://tools.usps.com/go/TrackConfirmAction?tLabels=9400100000000000000000)
*   **Agent:** *"Đơn hàng đã được ghi nhận vào hệ thống. Bạn có cần em hỗ trợ gì thêm không?"*
