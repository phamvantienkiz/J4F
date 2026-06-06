# AGENT WORKFLOW & NLU TEST SPECIFICATION

Tài liệu này đặc tả chi tiết các kịch bản kiểm thử luồng AI Agent (LangGraph), khả năng trích xuất NLU của Gemini, và logic tính toán chi phí (Pricing Engine) nhằm đảm bảo hoạt động nghiệp vụ của trợ lý **BurgerPrints Agent** luôn đúng đắn và chính xác.

Tài liệu này được thiết kế thống nhất và liên kết chặt chẽ với [Solution Overview](file:///E:/Hackathon2026/J4F/Solution/docs/ai/solution_overview.md), [Agent Design Specification](file:///E:/Hackathon2026/J4F/Solution/docs/ai/agent_design_specification.md), và [User Flow & Conversation Flow](file:///E:/Hackathon2026/J4F/Solution/docs/ai/user_flow_and_conversation_flow.md).

---

## 1. Kiểm Thử Trích Xuất Ngữ Cảnh (Gemini NLU & Slot Extraction)

Kiểm thử chức năng trích xuất Slots tại `extract_intent_node` để đảm bảo hệ thống hiểu đúng yêu cầu của Seller từ ngôn ngữ tự nhiên.

### Test Case NLU-001: Trích xuất đầy đủ thông số áo thun (Happy Path)
*   **Mục tiêu:** Xác thực Gemini NLU trích xuất thành công toàn bộ các slots từ câu hỏi chi tiết của người dùng.
*   **User Input:** `"Tôi muốn bán Unisex T-shirt màu đen size L ở thị trường Mỹ, giá vốn tối đa $9, giao hàng dưới 5 ngày bằng DTG."`
*   **Expected Output (State `requirements`):**
    ```json
    {
      "product_type": "Unisex T-shirt",
      "color": "Black",
      "size": "L",
      "market": "US",
      "max_cogs": 9.00,
      "print_method": "DTG"
    }
    ```

### Test Case NLU-002: Kế thừa thông số từ Preferences (Context Inheritance)
*   **Mục tiêu:** Xác thực khả năng điền tự động các tham số lọc từ bộ nhớ ưu tiên của Seller khi họ không nhắc lại trong câu chat.
*   **Initial State (`user_preferences`):**
    ```json
    {
      "preferred_market": "US",
      "target_margin": 45.0,
      "max_shipping_days": 7
    }
    ```
*   **User Input:** `"Tìm cho tôi áo Hoodie màu xám phôi cotton."`
*   **Expected Output (State `requirements`):**
    *   `product_type`: `"Hoodie"`
    *   `color`: `"Grey"`
    *   `market`: `"US"` (Kế thừa từ `preferred_market`)
    *   `max_shipping_days`: `7` (Kế thừa từ preferences)

### Test Case NLU-003: Xử lý thay đổi ý định đột ngột (Context Switch)
*   **Mục tiêu:** Xác thực Agent chuyển đổi ngữ cảnh mượt mà khi Seller đột ngột thay đổi sản phẩm.
*   **Initial State (`requirements`):** Đang chứa thông tin T-shirt US chuẩn bị tạo đơn.
*   **User Input:** `"Thôi không lấy áo thun nữa, tìm cho tôi cốc sứ 11oz gửi đi Pháp."`
*   **Expected Output (State `requirements`):**
    *   `product_type`: `"Ceramic Mug (11oz)"`
    *   `market`: `"FR"` (Pháp)
    *   Các trường `color`, `size`, `max_cogs` cũ của áo thun được reset về `None`.
    *   Agent hiển thị thông báo xác nhận: `"Em đã chuyển sang tìm kiếm Cốc sứ gửi đi Pháp. Đơn hàng nháp áo thun trước đó đã được hủy."`

---

## 2. Kiểm Thử Câu Hỏi Làm Rõ (Clarification Node)

Kiểm thử tại `clarify_node` khi thông tin đầu vào không đủ để truy xuất danh mục hoặc tính giá.

### Test Case CLA-001: Thiếu loại sản phẩm và thị trường (Trường hợp cốt lõi)
*   **Mục tiêu:** Xác thực Agent chặn luồng và đặt câu hỏi định hướng nếu thiếu `product_type` hoặc `market`.
*   **User Input:** `"Tìm xưởng in có giá vốn dưới $10 và ship nhanh."`
*   **Agent State:** `requirements.product_type` = `None`, `requirements.market` = `None`.
*   **Expected Action:**
    *   Chuyển luồng sang node `clarify_node`.
    *   `state['last_missing_fields']` được điền: `["product_type", "market"]`.
    *   Agent phản hồi: `"Để em tìm kiếm xưởng in tối ưu, bạn vui lòng cho biết bạn muốn bán loại sản phẩm nào (ví dụ: áo T-shirt, cốc sứ...) và gửi tới quốc gia nào?"`
    *   Đồ thị tạm dừng để đợi input tiếp theo.

---

## 3. Kiểm Thử Tính Toán Chi Phí (Deterministic Pricing Engine)

Các bài test này đảm bảo **cấm tuyệt đối LLM tính toán** và đảm bảo code Python xử lý chính xác 100% tài chính tại `calculate_pricing_node`.

### Test Case PRI-001: Tính toán Landed Cost & Margin của xưởng
*   **Mục tiêu:** Xác minh thuật toán tính toán của Pricing Engine.
*   **Đầu vào (Báo giá thô & Preferences):**
    *   `base_cost` = $5.50
    *   `printing_cost` = $2.00
    *   `shipping_cost` = $4.20
    *   `tax` = $0.50
    *   `selling_price` = $20.00
*   **Expected Calculation (Công thức Python):**
    *   $$LandedCost = 5.50 + 2.00 + 4.20 + 0.50 = 12.20$$
    *   $$MarginPercentage = \frac{20.00 - 12.20}{20.00} \times 100 = 39.0\%$$
*   **Expected State (`calculated_options`):** Chứa 1 đối tượng `CandidateOption` với `landed_cost` = `12.20` và `margin_percentage` = `39.0` (phải làm tròn đến 2 chữ số thập phân).

---

## 4. Kiểm Thử Xếp Hạng & Giải Trình (Ranking & Recommendation)

Xác thực logic xếp hạng Top 3 phương án và sinh giải thích trade-off tại `rank_and_recommend_node`.

### Test Case RNK-001: Xếp hạng ưu tiên Lợi nhuận (Margin Priority)
*   **Mục tiêu:** Xác thực xưởng có margin cao nhất được xếp vị trí số 1 khi preference của user là `'margin'`.
*   **Initial State (`user_preferences`):** `fulfillment_priority` = `"margin"`.
*   **calculated_options:**
    *   Xưởng A (US): Landed Cost $12.20, Margin 39.0%, Ship 4 ngày.
    *   Xưởng B (VN): Landed Cost $10.50, Margin 47.5%, Ship 12 ngày.
*   **Scoring Formula:**
    $$Score = MarginPercentage \times 0.6 + (10 - LandedCost) \times 0.2 + (15 - DeliveryDays) \times 0.2$$
    *   Score Xưởng A = $39.0 \times 0.6 + (10 - 12.20) \times 0.2 + (15 - 4) \times 0.2 = 23.4 - 0.44 + 2.2 = 25.16$
    *   Score Xưởng B = $47.5 \times 0.6 + (10 - 10.50) \times 0.2 + (15 - 12) \times 0.2 = 28.5 - 0.1 + 0.6 = 29.0$
*   **Expected Output (`ranking_results`):**
    *   Vị trí số 1: Xưởng B (VN) nhờ điểm số cao hơn.
    *   Agent sinh văn bản giải trình: Đề xuất Xưởng B (VN) vì đem lại lợi nhuận cao nhất (47.5%), nhưng cảnh báo về thời gian ship 12 ngày (trade-off).

### Test Case RNK-002: Xếp hạng ưu tiên Tốc độ giao hàng (Speed Priority)
*   **Mục tiêu:** Xác thực xưởng ship nhanh được xếp vị trí số 1 khi preference của user là `'speed'`.
*   **Initial State (`user_preferences`):** `fulfillment_priority` = `"speed"`.
*   **Expected Output (`ranking_results`):**
    *   Vị trí số 1: Xưởng A (US - ship 4 ngày) nhờ ưu tiên giao hàng nhanh hơn hẳn xưởng VN (12 ngày).

---

## 5. Kiểm Thử Đặt Đơn Hàng (Human-in-the-loop & Action Execution)

Xác thực node `execute_order_node` tương tác tạo đơn hàng qua BurgerPrints API.

### Test Case ORD-001: Xác thực địa chỉ thiếu thông tin (Edge Case)
*   **Mục tiêu:** Đảm bảo Agent phát hiện và chặn các đơn hàng có địa chỉ không hợp lệ.
*   **State `order_draft`:**
    ```json
    {
      "sku": "BP-TS-SWIFT-M",
      "quantity": 1,
      "shipping_name": "David Miller",
      "shipping_address_line1": "742 Evergreen Terrace",
      "shipping_city": "Springfield",
      "shipping_state": "IL",
      "shipping_zip": "",
      "shipping_country": "US"
    }
    ```
*   **Expected Action:**
    *   Hàm `validate_order_draft` trả về lỗi: `Missing field: shipping_zip`.
    *   Agent chặn không gọi API tạo đơn và phản hồi: `"Địa chỉ giao hàng hiện thiếu Zip Code tại bang Illinois. Bạn vui lòng bổ sung để em hoàn tất tạo đơn."`

### Test Case ORD-002: Xử lý hết phôi / Hết hàng từ API (Out-of-stock Fallback)
*   **Mục tiêu:** Đảm bảo hệ thống phục hồi khi nhà in được chọn phản hồi lỗi hết hàng.
*   **Action:** Gọi API `create_order` nhận mã lỗi `422 Unprocessible Entity` (Out of stock cho SKU tại xưởng được chọn Texas Apparel).
*   **Expected Fallback Action:**
    *   Agent thông báo cho Seller: `"Xưởng Texas Apparel hiện đã hết phôi size M cho dòng áo này."`
    *   Agent tự động tra cứu `calculated_options` còn lại trong state và đề xuất xưởng thay thế: `"Em đề xuất chuyển đơn sang xưởng SwiftPrint (US) với Landed Cost cao hơn $0.30 nhưng còn sẵn phôi. Bạn có muốn đổi xưởng không?"`

---

## 6. Kịch Bản Hội Thoại Hội Nhập Cuối (End-to-End Test Scripts)

Hệ thống được xác thực thành công khi chạy trơn tru qua 4 kịch bản hội thoại chuẩn dưới đây:

### Kịch bản 1: Tìm kiếm T-Shirt tối ưu cho thị trường US
1.  **User:** `"Tôi muốn bán T-shirt cho thị trường Mỹ, giá vốn dưới $8, ship dưới 5 ngày, chọn xưởng nào, SKU nào?"`
2.  **Agent (Expected):**
    *   Trích xuất slots và kế thừa `target_margin = 40%`.
    *   Gọi API lấy báo giá và tính Landed Cost.
    *   Hiển thị bảng so sánh Top 3 xưởng (SwiftPrint US, GlobalPrint VN, ExpressInk US).
    *   Giải thích trade-off: Khuyên dùng SwiftPrint (US) giá $8.50 (vượt trần $0.50 nhưng ship 4-5 ngày đạt yêu cầu, xưởng VN giá $7.20 rẻ nhưng ship 12 ngày không đạt).
    *   Hỏi: `"Bạn có muốn em tạo đơn nháp cho SwiftPrint không?"`

### Kịch bản 2: So sánh sản phẩm Hoodie giữa xưởng US và xưởng VN
1.  **User:** `"So sánh giá Hoodie giữa các xưởng đang có, xưởng nào ship EU rẻ nhất?"`
2.  **Agent (Expected):**
    *   Bóc tách product_type: `"Hoodie"`, market: `"EU"` (mặc định lấy Đức làm đại diện).
    *   Hiển thị bảng so sánh xưởng US vs xưởng VN gửi đi EU. Saigon Print (VN) có base cost rẻ ($10.20) nhưng ship đi EU $12.50 nên landed cost đắt hơn và ship lâu hơn xưởng nội địa US. Khuyên chọn xưởng US.
3.  **User:** `"Xem phí ship cụ thể tới Pháp."`
4.  **Agent (Expected):**
    *   Gọi lại API lấy phí ship tới Pháp.
    *   Cập nhật bảng so sánh chi phí với điểm đến là Pháp.

### Kịch bản 3: Gợi ý sản phẩm phù hợp theo giá bán lẻ và margin mục tiêu
1.  **User:** `"Tôi định bán giá $24.99, margin tối thiểu 40%, gợi ý sản phẩm phù hợp."`
2.  **Agent (Expected):**
    *   Tính toán Max Landed Cost = $24.99 * 0.60 = $14.99.
    *   Gọi API catalog lọc các sản phẩm có landed cost (gồm ship US trung bình) dưới $14.99.
    *   Đề xuất bảng so sánh 3 sản phẩm: Unisex Cotton T-Shirt (SwiftPrint - Landed Cost $8.50, Margin 66%), Ceramic Mug (Detroit Pottery - Landed Cost $9.20, Margin 63%), Canvas Tote Bag (VN - Landed Cost $12.80, Margin 48.8%).

### Kịch bản 4: Xác nhận và Tạo đơn hàng nháp (Human-in-the-loop)
1.  **User:** `"Chốt đơn Option 1 (SwiftPrint) gửi cho khách: David Miller, 742 Evergreen Terrace, Springfield, IL, US. Số lượng: 1 chiếc."`
2.  **Agent (Expected):**
    *   Phát hiện địa chỉ thiếu Zip Code.
    *   Chặn lại và phản hồi: `"Địa chỉ giao hàng hiện thiếu Zip Code tại bang Illinois. Bạn vui lòng bổ sung để em tạo đơn."`
3.  **User:** `"Zip code là 62704."`
4.  **Agent (Expected):**
    *   Validate địa chỉ thành công.
    *   Gọi API `create_order` và nhận về `bp_ord_88776655`.
    *   Hiển thị thông tin vận đơn thành công: Mã đơn `#BP-88776655`, trạng thái `Pending`, vận đơn `USPS-9400100000000000000000`.
