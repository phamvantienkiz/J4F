Tôi sẽ chọn một hướng rất thực dụng cho hackathon này:

FastAPI + LangGraph + Gemini API + Streamlit là bộ khung phù hợp nhất cho MVP.
FastAPI cho backend vì là framework Python hiệu năng cao, dựa trên type hints và tự sinh OpenAPI/interactive docs (/docs, /redoc), rất tiện khi giám khảo test trực tiếp. LangGraph phù hợp hơn LangChain thuần hoặc ADK cho bài toán này vì nó được thiết kế cho agent stateful, có nodes/edges, conditional routing, persistence/checkpoints, streaming và human-in-the-loop. Gemini API hỗ trợ function calling và structured outputs JSON Schema, nên rất hợp để gọi BurgerPrints API và ép đầu ra theo format ra quyết định. Streamlit thì đúng kiểu “build nhanh để demo”, chạy bằng streamlit run, phù hợp khi bạn cần một UI seller tương tác trong thời gian ngắn.

### 1) Bài toán thật sự cần giải là gì?

Đề này không phải bài “chatbot trả lời câu hỏi”. Nó là decision agent cho seller POD. Nghĩa là agent phải làm 4 việc liên tiếp: hiểu nhu cầu, truy xuất catalog, tính toán ràng buộc chi phí/ship/margin, rồi đưa ra khuyến nghị đủ chắc để người bán quyết định ngay. Bonus tạo đơn hàng là bước “execute”, nên kiến trúc phải tách rõ analysis và action. Đây là lý do tôi không khuyên làm form lọc tĩnh; giám khảo sẽ đánh rất nặng trải nghiệm hội thoại nhiều lượt và độ “seller-like”.

### 2) Kiến trúc đề xuất

**Tầng UI**

Chọn Streamlit làm UI chính cho MVP. Lý do là nó cho phép dựng giao diện chat, bảng so sánh, chip lọc, nút “Confirm order” rất nhanh trong một app Python duy nhất. Nếu muốn kênh chat tự nhiên hơn, có thể thêm Telegram bot như một adapter phụ, nhưng không nên để nó là UI chính của demo vì khó show bảng so sánh và ít “wow” hơn.

**Tầng Backend**

Dùng FastAPI làm API gateway và business backend. Backend này chịu trách nhiệm:

- nhận message từ UI,
- lưu session/thread,
- gọi agent workflow,
- gọi BurgerPrints API,
- chuẩn hoá kết quả,
- trả response cho UI,
- và mở endpoint tạo đơn hàng cho bước xác nhận.

FastAPI đặc biệt hợp vì tự sinh schema và docs, giúp bạn debug nhanh ngay cả khi có nhiều request/response shape khác nhau.

**Tầng Agent Orchestration**

Dùng LangGraph làm “bộ não điều phối”. Tôi không khuyên dùng multi-agent phức tạp ngay từ đầu; chỉ cần 1 agent chính + tool layer + state machine là đủ mạnh cho đề này. LangGraph cho bạn:

- state xuyên suốt hội thoại,
- rẽ nhánh theo điều kiện,
- checkpoint/persistence để resume hội thoại,
- human-in-the-loop để hỏi lại khi thiếu dữ kiện,
- và kiểm soát luồng tốt hơn agent loop tự do.

**Tầng LLM**

Chọn Gemini API. Với bài này, Gemini có 2 điểm rất đáng giá:

- Function calling để model quyết định khi nào gọi tool nội bộ/BurgerPrints API.
- Structured outputs để ép đầu ra thành JSON rõ ràng, ví dụ: `recommendations`, `comparisons`, `missing_fields`, `confidence`, `next_question`.

**Tầng dữ liệu và persistence**

Dùng SQLite cho MVP nếu muốn cài nhanh, hoặc Postgres nếu muốn chắc hơn và dễ mở rộng. LangGraph hỗ trợ checkpoint/persistence, nên bạn có thể lưu thread_id, lịch sử hội thoại ngắn hạn, và preferences dài hạn của seller như thị trường ưu tiên, mức margin tối thiểu, ngưỡng ship tối đa.

### 3) Luồng agent nên thiết kế như thế nào?

Tôi đề xuất một workflow 6 bước:

**Bước 1 — Intent & slot extraction**
Agent đọc câu hỏi, bóc tách các slot quan trọng: market, product type, target price, max COGS, max ship time, region ship, material, printing method, margin mục tiêu, và mức ưu tiên giữa giá / tốc độ / chất lượng.

**Bước 2 — Clarification nếu thiếu dữ kiện**

Nếu thiếu thông tin then chốt, agent phải hỏi lại, ví dụ:

- “Bạn ưu tiên US hay EU?”
- “Ngân sách là base cost hay landed cost?”
- “Margin tính trên giá bán trước hay sau phí nền tảng?”

Đây là chỗ LangGraph rất hợp vì bạn có thể cho graph rẽ sang nhánh “ask_clarifying_question” thay vì đoán mò.

**Bước 3 — Catalog retrieval**

Agent gọi BurgerPrints API để lấy danh sách sản phẩm/xưởng/SKU phù hợp.
Vì bạn chưa có schema API trong prompt, tôi giả định bạn sẽ map các tool nội bộ như:

- `search_products`
- `get_product_variants`
- `get_factory_quotes`
- `get_shipping_estimate`
- `get_tax_estimate`
- `get_inventory_or_leadtime`
- `create_order`

Điểm quan trọng là không nhúng cứng dữ liệu, mọi thứ phải đi qua API thật.

**Bước 4 — Deterministic pricing engine**

Sau khi lấy dữ liệu, đừng để LLM tự cộng trừ. Hãy dùng code Python tính:

- base cost
- printing cost
- ship cost
- tax/customs
- platform fee nếu bạn có thể ước lượng
- tổng landed cost
- gross margin
- shipping SLA risk

LLM chỉ nên diễn giải kết quả và chọn phương án. Còn phép tính nên deterministic để tránh “ảo giác số”.

**Bước 5 — Ranking & explanation**

Agent xếp hạng theo một scoring function đơn giản:

`score = w1*margin + w2*speed + w3*reliability + w4*availability - w5*cost`

Sau đó xuất:

- top 3 option,
- lý do chọn,
- trade-off của từng option,
- và “option tôi khuyên dùng nhất”.

**Bước 6 — Confirmation & order creation**

Khi seller nói “chốt option 2” hoặc “tạo đơn”, agent chuyển sang trạng thái xác nhận:

- product / SKU
- size / color / print method
- quantity
- ship-to address / market
- price check cuối cùng
- Sau khi xác nhận đủ, mới gọi create_order.

### 4) Vì sao không dùng ADK làm lựa chọn chính?

ADK là framework agent open-source định hướng production, hỗ trợ build/debug/deploy agent và có nhiều ngôn ngữ như Python, TypeScript, Go, Java, Kotlin. Nó cũng có khái niệm Session và state cho hội thoại. Tuy nhiên, với bài hackathon này, bạn cần một workflow rõ ràng, dễ kiểm soát, dễ demo, dễ debug hơn là một nền tảng agent rộng và thiên về hệ sinh thái enterprise. Vì vậy, tôi xem ADK là phương án thay thế tốt nếu team bạn muốn đi sâu vào hệ Google, còn LangGraph là lựa chọn an toàn hơn cho demo hội thoại nhiều lượt + state + tool-calling.

### 5) Thiết kế state của agent

State tối thiểu nên có:

- `thread_id`
- `user_profile`
  - `market ưu tiên`
  - `target platform`
  - `margin target`
  - `ship SLA target`
- `conversation_history`
- `extracted_requirements`
- `candidate_products`
- `candidate_quotes`
- `ranking_results`
- `last_missing_fields`
- `order_draft`
- `order_status`

Về mặt kỹ thuật, đây chính là nơi LangGraph phát huy lợi thế vì state được giữ xuyên suốt luồng và có checkpoint để resume sau mỗi bước.

### 6) Bộ tool nên có

Tôi khuyên tách tool layer thành 2 nhóm:

**A. Read tools**

- `search_catalog(query, market, product_type, attributes)`
- `get_product_detail(product_id)`
- `get_factory_quotes(product_id, variant_id, market, quantity)`
- `get_shipping_options(origin_factory, destination_market, - - service_level)`
- `estimate_land_cost(...)`
- `compare_products(product_ids, constraints)`

**B. Action tools**

- `validate_order_draft(...)`
- `create_order(...)`
- `get_order_status(order_id)`

Với Gemini, function calling là đúng kiểu để model quyết định lúc nào gọi những tool này thay vì trả lời bằng text suông. Structured outputs cũng giúp bạn kiểm soát schema phản hồi để UI render đẹp và ổn định.

### 7) Cách làm output “ra quyết định” thay vì chỉ trả lời

Mỗi response nên có 4 khối:

1. Kết luận ngắn
   “Em đề xuất T-shirt model A từ xưởng X.”

2. Top options
   Option 1, 2, 3 với giá landed, ship, margin, lead time.

3. Lý do chọn
   Ví dụ:

landed cost thấp hơn 12%
ship nhanh hơn 2 ngày
margin đạt 42%
ít rủi ro out-of-stock hơn

4. Next action

“Nếu bạn muốn, tôi có thể chốt đơn option 1 cho 50 chiếc.”
hoặc “Bạn cần đổi sang EU market hay giữ US?”

Nguyên tắc là: mỗi câu trả lời phải giúp seller đi gần hơn tới quyết định. Đừng để agent nói lan man kiểu tư vấn chung chung.

### 8) Cách làm “multi-turn” cho thật tốt

Đây là chỗ nhiều team yếu.

Tôi khuyên chia hội thoại thành 3 lớp nhớ:

Short-term memory: những gì đang bàn trong session hiện tại.
Preference memory: market, platform, margin target của seller.
Order draft memory: dữ liệu khi seller đang chốt đơn.

LangGraph có persistence/checkpoints nên việc này tự nhiên hơn. Bạn có thể cho agent nhớ rằng seller thường bán US, muốn margin tối thiểu 40%, thích ship dưới 5 ngày. Lần sau họ hỏi “T-shirt dưới $8” thì agent khỏi hỏi lại market nữa.

### 9) UI nên trình bày thế nào để ăn điểm UX

Dù chọn Streamlit hay Telegram, giao diện nên có 4 thành phần:

khung chat,
panel “Selected constraints”,
bảng so sánh 3 option,
nút “Create order”.

Streamlit là lựa chọn nhanh nhất để làm panel này vì nó sinh ra cho app dữ liệu và tương tác nhanh. Nếu làm Telegram thì nên dùng như kênh phụ, còn UI chính vẫn nên là web để hiển thị bảng so sánh rõ ràng.

### 10) MVP tốt nhất trong 10 phút cài đặt

MVP nên chỉ có:

1 backend FastAPI,
1 UI Streamlit,
1 agent LangGraph,
1 LLM Gemini,
1 file .env,
1 docker compose hoặc 1 lệnh chạy đơn giản.

Tuyệt đối tránh:

microservices nhiều lớp,
vector database nếu chưa thật cần,
multi-agent phức tạp,
frontend NextJS nếu team không đã quen.

Vì tiêu chí đề là results, không phải kiến trúc phô trương.

### 11) Bộ demo nên kể câu chuyện gì?

Demo 3–5 phút nên theo kịch bản này:

Cảnh 1: Seller hỏi bằng tiếng Việt hoặc Anh.
Cảnh 2: Agent hỏi lại đúng 1–2 câu nếu thiếu dữ kiện.
Cảnh 3: Agent trả top 3 option + so sánh.
Cảnh 4: Seller bấm “chốt”.
Cảnh 5: Agent tạo draft order hoặc order thật qua API.

Nếu làm được cảnh 5, điểm bonus sẽ rất mạnh vì nó chứng minh agent không chỉ “nói hay” mà còn “làm được việc”.

### 12) Rủi ro lớn nhất và cách né

Rủi ro 1: API latency / rate limit
Giải pháp: cache theo query, preload những catalog phổ biến, và tránh gọi API lặp lại khi state chưa đổi. Gemini API có rate limits nên cũng nên giảm số lần gọi model không cần thiết.

Rủi ro 2: LLM bịa số
Giải pháp: mọi số tiền, ship, tax, margin đều tính bằng Python, LLM chỉ diễn giải.

Rủi ro 3: Hội thoại thiếu ngữ cảnh
Giải pháp: bắt buộc lưu thread state và preference memory.

Rủi ro 4: Demo không “wow”
Giải pháp: UI phải có bảng so sánh và nút hành động, không chỉ là chat text.

### 13) Khuyến nghị chốt cuối cùng

Nếu phải chốt một cấu hình duy nhất, tôi khuyên:

Backend: FastAPI
Agent engine: LangGraph
LLM: Gemini API
UI: Streamlit
Persistence: SQLite cho MVP, Postgres nếu kịp
Pattern: Tool-calling + workflow/state machine + deterministic pricing engine
