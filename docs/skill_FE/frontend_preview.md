# BurgerPrintsAgent FE Preview

Reading this as: seller-facing POD assistant dashboard for Vietnamese sellers selling into international markets, with a clean SaaS/productivity language, leaning toward BurgerPrints brand tokens, compact commerce cards, and a strong right-side order workflow.

## Design source

Use these files as source of truth when implementing:

- `docs/skill_FE/design.md`
- `docs/skill_FE/SKILL.md`
- `docs/skill_FE/taste-skill/skills/taste-skill/SKILL.md`

Do not create a separate visual language. Use the existing BurgerPrints orange CTA, Gilroy font stack, white cards, muted section surfaces, token radius, token shadows, and token spacing from `design.md`.

---

## 1. Desktop layout overview

```text
┌──────────────────────────────────────────────────────────────────────────────────────────────┐
│ Header                                                                                       │
│ BurgerPrintsAgent        Market: US ▾        Month: June ▾        Balance / Sandbox status    │
├───────────────┬──────────────────────────────────────────────────────────────┬───────────────┤
│ History       │ Main chat workspace                                          │ Order panel   │
│               │                                                              │               │
│ Today         │ ┌──────────────────────────────────────────────────────────┐ │ Create order  │
│ - US summer   │ │ Assistant welcome / market prompt                       │ │ draft         │
│ - Hoodie CA   │ │ Suggested question chips                                │ │               │
│               │ │                                                          │ │ Selected SKU  │
│ Yesterday     │ │ Chat messages                                             │ │ Product image │
│ - Balance     │ │ User / Assistant bubbles                                  │ │ Product info  │
│ - Order draft │ │ SKU recommendation table/card                             │ │ Variant       │
│               │ │                                                          │ │ Shipping form │
│ Saved prompts │ │ Product suggestions row                                   │ │ Design fields │
│ - US trends   │ │ [SKU Card] [SKU Card] [SKU Card]                          │ │ CTA           │
│ - Fast ship   │ │                                                          │ │               │
│               │ │ Chat input + Send button                                  │ │               │
│               │ └──────────────────────────────────────────────────────────┘ │               │
└───────────────┴──────────────────────────────────────────────────────────────┴───────────────┘
```

### Layout proportions

| Region | Desktop width | Purpose |
|---|---:|---|
| History sidebar | 240-280px | Conversation history, saved prompts, quick market filters |
| Main chat workspace | fluid | Chat, suggestions, recommendation results, product cards |
| Order panel | 360-420px | Selected product/SKU preview and sandbox order draft |

Use CSS Grid for the shell. The right order panel should stay sticky on desktop so the seller can review product/order fields while scrolling chat results.

---

## 2. Header

### Content

```text
BurgerPrintsAgent
Find profitable POD SKUs, shipping cost, delivery, and sandbox order drafts.

Market: US ▾
Month: June ▾
Sandbox create: Disabled / Enabled
```

### Behavior

- `Market` controls `/agent/suggestions?country=...`.
- `Month` controls `/agent/suggestions?country=US&month=6`.
- Changing market/month refreshes suggested question chips.
- Header CTA/status should use `color.surface.raised` only for primary active actions.

### Header filter sync and dirty order state

If the user changes `Market` while the right order panel has a dirty draft, show a confirmation dialog before applying the new market.

Dialog copy:

```text
Thay đổi thị trường sẽ làm mới bản nháp đơn hàng hiện tại.
Bạn có muốn tiếp tục?

[Giữ bản nháp] [Tiếp tục đổi market]
```

Behavior:

- `Giữ bản nháp`: close dialog, keep current market, keep order panel data.
- `Tiếp tục đổi market`: clear selected SKU, reset order panel to empty state, update market, refetch `/agent/suggestions`.
- A draft is dirty when the user selected a SKU, changed quantity/color/size, or typed any shipping/design/reference field.
- If order panel is not dirty, market/month can update immediately.

---

## 3. History sidebar

### Sections

```text
Today
- Find Black size M T-shirt highest profit
- US summer POD ideas
- Create sandbox order draft

Yesterday
- Balance check
- Fast shipping hoodie CA

Saved prompts
- Mùa này ở US nên bán áo gì?
- Tìm SKU T-shirt ship Mỹ dưới 5 ngày
- Gợi ý niche POD cho US tháng này
```

### Card rules

- Each history item is a compact card row.
- Active conversation uses subtle orange left border or active background token.
- Long titles use ellipsis.
- Keyboard focus must be visible.
- Empty state:

```text
No chat history yet.
Start with a market suggestion or ask a SKU question.
```

---

## 4. Main chat workspace

### Top onboarding state

When no conversation is selected:

```text
Ask your BurgerPrints fulfillment assistant
Compare SKU, supplier, shipping fee, delivery, SLA, and profit before creating a sandbox order.

Suggested questions for US · June
[ Mùa này ở US nên bán áo gì? ]
[ Gợi ý niche POD cho US tháng này ]
[ Sắp tới ở US có event nào nên làm design? ]
[ Tìm SKU T-shirt phù hợp bán ở US mùa summer ]
```

### Chat message layout

#### User bubble

- Align right.
- Compact width.
- Use primary text on muted/raised contrast depending final design token.
- Example:

```text
Find Black size M T-shirt highest profit
```

#### Assistant bubble: missing country clarification

- Align left.
- White card with muted border.
- No order CTA.
- Example:

```text
Mình cần biết đơn này ship/fulfill tới nước nào để tính đúng shipping, delivery và xưởng.
Bạn muốn ship tới market nào? Ví dụ: US, CA, UK, AU, VN.

[US] [CA] [UK] [AU] [VN]
```

#### Assistant bubble: recommendation result

Use a structured commerce card instead of a wall of text.

```text
Recommended SKUs for US
Source: BurgerPrints Catalog API

┌────────────────────────────────────────────────────────────────────┐
│ SKU                  Product                 Supplier   Total cost  │
│ USEXMCC1717UL...     Comfort Colors 1717     Helia      $9.00      │
│ Delivery: 2-7 business days   Carrier: USPS   SLA: 67.24%          │
│ Profit: $...                  Margin: ...                            │
│ [View details] [Đặt đơn]                                             │
└────────────────────────────────────────────────────────────────────┘
```

### Streaming and loading skeleton state

Catalog recommendations can take 2-4 seconds while the backend fetches catalog, shipping, supplier and SLA data. Do not leave the recommendation area empty.

While `/agent/chat` is pending for a SKU/recommendation request:

```text
Assistant is checking Catalog API...

┌────────────────────────────────────────────────────────────────────┐
│ [image skeleton]  [product title skeleton..............]            │
│ [SKU skeleton....] [supplier skeleton] [price skeleton]             │
│ [delivery skeleton........] [carrier skeleton] [SLA skeleton]       │
└────────────────────────────────────────────────────────────────────┘
```

Skeleton rules:

- Image mockup box, SKU, product title, supplier, price, shipping, total cost, delivery, carrier and SLA cells show gray pulse placeholders.
- Skeleton background uses the chat-bot surface token: `var(--chatbot-color-bg-chat-bot)`.
- Pulse animation must respect `prefers-reduced-motion`; reduced motion uses static placeholders.
- If assistant text is streaming before product data is ready, render text normally and keep the product card/table skeleton below it.
- Replace skeleton with real `data.items` immediately when the response resolves.
- If response is missing-country clarification, remove skeleton and show market chips only.

### Chat input

```text
┌─────────────────────────────────────────────────────────────┐
│ Ask: Find Black size M T-shirt ship US highest profit...    │
└─────────────────────────────────────────────────────────────┘ [Send]
```

Rules:

- Enter sends message.
- Shift+Enter inserts newline if multiline is enabled.
- Disable send button while request is loading.
- Suggested question click sends that suggestion as `/agent/chat` message.

---

## 5. Product suggestions area under chat

This area appears below the latest assistant recommendation, not permanently above the conversation.

### Product suggestion card

```text
┌──────────────────────────────────────────────┐
│ [Product mockup image]                       │
│ Comfort Colors 1717                          │
│ SKU: USEXMCC1717UL-Black-M                   │
│ Color: Black     Size: M                     │
│ Supplier: Helia                              │
│ Ship: $0.50     Sell: $24.99     Total: $9.00│
│ Gross margin: 58.50%                           │
│ Delivery: 2-7 business days     Carrier: USPS │
│ [View] [Đặt đơn]                             │
└──────────────────────────────────────────────┘
```

### Data mapping

| UI field | Backend source |
|---|---|
| Image | `mockup_url` first, fallback `image_url`, fallback placeholder |
| Product name | `product_name` or `display_name` |
| SKU | `sku` |
| Color | `color` |
| Size | `size` |
| Supplier | `partner_name` or `location_name` |
| Base price | `base_cost` |
| Shipping | `shipping_fee` |
| Selling price | `selling_price`; show `Need selling price` / `Cần giá bán` when missing |
| Total cost | `total_cost` |
| Delivery | `delivery_time`; show ship-market hint instead of raw `N/A` when missing |
| Carrier | `carrier` |
| SLA | `sla` |
| Profit/Margin | `profit`, `margin_percent` when available |

### Behavior

- `View` expands full SKU detail inside the main chat area.
- `Đặt đơn` selects that SKU and opens/fills the right order panel.
- Only show `Đặt đơn` after a real recommendation result, never after missing-country clarification.

---

## 6. Right order panel

The right panel is always visible on desktop. On mobile, it becomes a bottom sheet or full-screen drawer.

### Empty state

```text
Create sandbox order
Select a recommended SKU to start a draft.

What will be filled automatically:
- Product image
- Product name
- Catalog SKU
- Color / Size
- Quantity
- Shipping country from market
- Supplier and cost summary
```

### Filled state after clicking `Đặt đơn`

```text
Create sandbox order draft

[Mockup image]
Comfort Colors 1717
SKU: USEXMCC1717UL-Black-M
Color: Black · Size: M
Supplier: Helia
Total fulfillment cost: $9.00
Delivery: 2-7 business days

Variant
[Color: Black ▾] [Size: M ▾]
[Quantity: 1  - +]

Shipping information
[Full name]
[Address line 1]
[City]
[State]
[ZIP]
[Country: US ▾]

Design
[Front design URL]
[Back design URL optional]

Reference
[Reference order ID]

[Create sandbox draft]
```

### Prefilled fields from selected product

| Field | Prefill rule |
|---|---|
| Product image | selected item `mockup_url` / `image_url` |
| Product name | selected item `product_name` |
| Catalog SKU | selected item `sku` |
| Color | selected item `color` |
| Size | selected item `size` |
| Quantity | selected item `quantity` or `1` |
| Shipping country | current market/country, e.g. `US` |
| Supplier | selected item `partner_name` / `location_name` |
| Cost summary | selected item `base_cost`, `shipping_fee`, `total_cost` |
| Delivery summary | selected item `delivery_time`, `carrier`, `sla` |

### Fields user still fills manually

```text
shipping_name
shipping_address1
shipping_city
shipping_state if US
shipping_zip
reference_order_id
design_url_front
```

### Safety state before final create

After user fills required fields, show a confirmation card:

```text
Ready to create sandbox order
PII will be masked in chat history.
This action requires exact confirmation.

Type: confirm create sandbox order
```

Do not let simple `ok`, `yes`, or `đồng ý` call create order.

---

## 7. Visual direction

### Overall feel

- Clean, practical, seller-first dashboard.
- White cards on muted sections.
- Strong orange only for primary actions: `Send`, `Đặt đơn`, `Create sandbox draft`.
- Avoid AI-purple gradients, glassmorphism, random neon, or playful effects.
- Use soft shadows only for elevated cards/panels.

### Component hierarchy

1. Header market controls.
2. Chat message stream.
3. Suggested question chips.
4. SKU recommendation cards.
5. Right order panel.
6. History sidebar.

### Motion

Use subtle transitions only:

- Chat message appears with small fade/translate.
- Suggested chips hover with token shadow/raised border.
- Order panel slides in on mobile.
- Loading state shows spinner in button.

Respect reduced-motion preferences.

---

## 8. Responsive behavior

### Desktop

```text
History sidebar | Chat workspace | Order panel
```

### Tablet

```text
Chat workspace | Order panel
History moves to collapsible drawer
```

### Recommendation table responsive rule

For viewport width `< 1024px`, never keep the SKU recommendation result as a wide row/table. Convert it into stacked product cards using the same structure as the product suggestion card in Section 5.

Desktop `>= 1024px`:

```text
SKU | Product | Supplier | Base | Ship | Total | Delivery | Carrier | SLA | Action
```

Tablet/mobile `< 1024px`:

```text
┌──────────────────────────────────────────────┐
│ [Image] Comfort Colors 1717                  │
│ SKU: USEXMCC1717UL-Black-M                   │
│ Supplier: Helia                              │
│ Base: $8.50 · Ship: $0.50 · Total: $9.00     │
│ Delivery: 2-7 business days · USPS · SLA ... │
│ [View details] [Đặt đơn]                     │
└──────────────────────────────────────────────┘
```

Rules:

- Do not shrink text below readable sizes to force table columns into tablet width.
- Do not hide critical commerce fields: SKU, supplier, total cost, delivery and action must remain visible.
- Horizontal scroll is acceptable only for developer/debug raw tables, not the seller-facing recommendation cards.
- Keep long product names ellipsized to one line in the card header.

### Mobile

```text
Header
Chat workspace
Product suggestion carousel
Chat input sticky bottom
Order panel opens as bottom sheet after tapping Đặt đơn
History opens as drawer
```

### Mobile product suggestion card

```text
[Image]  Comfort Colors 1717
         SKU: ...Black-M
         Total: $9.00 · Delivery: 2-7 days
         [Đặt đơn]
```

---

## 9. Real API integration

Use the existing backend API directly. Do not mock these flows in the frontend except for local UI skeleton/loading states.

### Base URL

```text
Development: http://127.0.0.1:8010
Production: set by frontend env, e.g. VITE_API_BASE_URL or NEXT_PUBLIC_API_BASE_URL
```

Frontend should centralize this as:

```text
apiBaseUrl = process.env.NEXT_PUBLIC_API_BASE_URL || process.env.VITE_API_BASE_URL || "http://127.0.0.1:8010"
```

### Endpoint map

| UI action | API |
|---|---|
| Health/status badge | `GET /health` |
| Load market/month chips | `GET /agent/suggestions?country=US&month=6` |
| Click suggested question | `POST /agent/chat` with suggestion as `message` |
| Send chat message | `POST /agent/chat` |
| Follow-up country chip | `POST /agent/chat` with `US`, `CA`, etc. |
| Click `Đặt đơn` | Local UI selects SKU, then sends `tạo sandbox order` to `/agent/chat` when user starts draft |
| Fill draft fields | `POST /agent/chat` with key-value fields |
| Final create | `POST /agent/chat` with exact `confirm create sandbox order` |
| Raw core debug screen only | `POST /text-to-api` |

---

## 10. API contracts for FE

### 10.1 Health

```http
GET /health
```

Response:

```json
{
  "status": "ok"
}
```

UI usage:

- Header status dot.
- If unavailable, disable send/order buttons and show `API offline`.

### 10.2 Suggested questions

```http
GET /agent/suggestions?country=US&month=6
```

Query params:

| Param | Type | Required | Notes |
|---|---|---:|---|
| `country` | string | no | Defaults to `US`, supports market codes like `US`, `CA`, `UK`, `AU`, `VN`, `EU` |
| `month` | number | no | `1-12`, defaults to current backend month |

Response:

```json
{
  "country": "US",
  "month": 6,
  "season": "summer",
  "weather_context": "hot weather, outdoor activities, and vacation themes",
  "events": ["Father's Day", "summer", "July 4 prep"],
  "product_types": ["T-shirt", "Tank top", "Lightweight apparel"],
  "suggestions": [
    "Mùa summer ở US nên bán sản phẩm POD nào?",
    "Gợi ý niche T-shirt cho US tháng này",
    "Sắp tới ở US có event nào nên làm design?",
    "Gợi ý design cho Father's Day ở US",
    "Tìm SKU T-shirt phù hợp bán ở US mùa summer"
  ]
}
```

UI usage:

- Render `suggestions` as chips near onboarding/chat input.
- Render `events` and `product_types` as small context badges if there is space.
- Clicking a suggestion sends that exact text to `/agent/chat`.

### 10.3 Chat agent

```http
POST /agent/chat
Content-Type: application/json
```

Request:

```json
{
  "session_id": "country-smoke-1",
  "message": "Find Black size M T-shirt highest profit",
  "history": []
}
```

Fields:

| Field | Type | Required | Notes |
|---|---|---:|---|
| `message` | string | yes | User text or clicked suggestion |
| `history` | array | no | Can send `[]`; backend state is keyed by `session_id` |
| `session_id` | string | no | Reuse same ID per chat; backend returns one if omitted |

Common response shape:

```json
{
  "answer": "...seller-facing answer...",
  "intent": "search_order_items",
  "tool_calls": [],
  "api": null,
  "params": {},
  "data": {},
  "notes": [],
  "session_id": "country-smoke-1"
}
```

FE should treat `answer` as the chat text, then use `intent`, `params`, and `data` to render richer cards.

### 10.4 Missing-country response

When seller asks recommendation without destination market:

```json
{
  "intent": "search_order_items",
  "api": null,
  "params": {"sort_by": "profit"},
  "data": {
    "source": "clarification",
    "clarification_required": true,
    "missing_field": "country",
    "question": "Bạn muốn ship/fulfill tới nước nào? Ví dụ: US, CA, UK, AU, VN."
  },
  "answer": "Mình cần biết đơn này ship/fulfill tới nước nào...",
  "session_id": "country-smoke-1"
}
```

UI behavior:

- Show assistant bubble.
- Show market chips: `US`, `CA`, `UK`, `AU`, `VN`.
- Do not show product cards.
- Do not show `Đặt đơn` CTA.
- Clicking `US` sends:

```json
{
  "session_id": "country-smoke-1",
  "message": "US",
  "history": []
}
```

### 10.5 SKU recommendation response

After country is known, backend returns ranked SKU data:

```json
{
  "intent": "search_order_items",
  "api": {"method": "GET", "path": "/catalogsV2/list"},
  "params": {"country": "US", "quantity": 1},
  "data": {
    "source": "catalog_api",
    "match_type": "exact",
    "items": [
      {
        "source": "catalog_api",
        "sku": "USEXMCC1717UL-Black-M",
        "product_name": "Unisex T-Shirt | Comfort Colors 1717",
        "color": "Black",
        "size": "M",
        "partner_name": "Helia",
        "base_cost": 8.5,
        "second_item_price": 3.0,
        "first_item_shipping": 0.5,
        "additional_item_shipping": 0.25,
        "shipping_fee": 0.5,
        "total_cost": 9.0,
        "quantity": 1,
        "delivery_time": "2-7 business days",
        "carrier": ["USPS"],
        "sla": "67.24",
        "mockup_url": "https://...",
        "image_url": "https://...",
        "profit": 12.0,
        "margin_percent": 48.0
      }
    ]
  },
  "answer": "...\n\nBạn có muốn tạo sandbox order draft từ SKU này không? Nếu có, hãy nhắn: tạo sandbox order."
}
```

UI behavior:

- Render `data.items` as product suggestion cards under chat.
- Use `answer` for text summary.
- Use `params.country` for order panel country prefill.
- Show `Đặt đơn` for each item.
- If `data.match_type = nearest_alternatives`, show a small warning badge and render `filter_excess` details.

### 10.6 Start order draft

When user clicks `Đặt đơn`, frontend should:

1. Select the clicked item locally and prefill the right panel immediately.
2. Send this message to backend using same `session_id`:

```json
{
  "session_id": "country-smoke-1",
  "message": "tạo sandbox order",
  "history": []
}
```

Backend response asks for missing fields:

```json
{
  "intent": "create_order",
  "params": {
    "catalog_sku": "USEXMCC1717UL-Black-M",
    "quantity": 1,
    "missing_fields": [
      "shipping_name",
      "shipping_address1",
      "shipping_city",
      "shipping_zip",
      "reference_order_id",
      "shipping_state",
      "design_url_front"
    ]
  },
  "answer": "Tôi có thể tạo sandbox order draft, nhưng còn thiếu..."
}
```

UI behavior:

- Keep right panel filled from selected local item.
- Highlight missing backend fields.
- User enters fields in the right panel form.
- On submit, convert form to key-value message.

### 10.7 Submit order draft fields

Request example:

```json
{
  "session_id": "country-smoke-1",
  "message": "shipping_name: Jane Doe\nshipping_address1: 123 Main St\nshipping_city: Austin\nshipping_state: TX\nshipping_zip: 78701\nshipping_country: US\nreference_order_id: TEST-1001\ndesign_url_front: https://example.com/design.png",
  "history": []
}
```

Backend response when enough fields are collected:

```json
{
  "intent": "create_order",
  "confirmation_required": true,
  "answer": "...Type: confirm create sandbox order...",
  "params": {
    "catalog_sku": "USEXMCC1717UL-Black-M",
    "quantity": 1
  }
}
```

UI behavior:

- Show confirmation card in the right panel.
- Disable final create button until user explicitly clicks a confirmation action or types exact phrase.
- Never treat `ok`, `yes`, `đồng ý` as final create.

### 10.8 Final sandbox create

Request:

```json
{
  "session_id": "country-smoke-1",
  "message": "confirm create sandbox order",
  "history": []
}
```

Possible disabled response if env is off:

```json
{
  "intent": "create_order",
  "data": {"sandbox": true, "status": "disabled"},
  "answer": "Sandbox order draft đã sẵn sàng, nhưng live sandbox POST đang bị tắt..."
}
```

Possible success response if env is enabled:

```json
{
  "intent": "create_order",
  "data": {
    "sandbox": true,
    "items_count": 1,
    "catalog_sku": "USEXMCC1717UL-Black-M",
    "quantity": 1,
    "id": "sandbox-order-1",
    "status": "created"
  },
  "tool_calls": [{"name": "create_order_tool", "params": {}}]
}
```

UI behavior:

- If disabled: keep draft visible and show env-disabled warning.
- If success: show created order state and lock fields.
- Never display raw PII in history if backend returns masked/sanitized data.

### 10.9 Raw core endpoint

Use only for developer/debug views, not the main seller chat:

```http
POST /text-to-api
Content-Type: application/json
```

Request:

```json
{"text": "Tìm SKU T-shirt ship Mỹ"}
```

Response is raw core result with `result` instead of agent `data`.

---

## 11. Frontend API client shape

Suggested client functions:

```ts
export async function getSuggestions(country: string, month?: number) {}
export async function sendChatMessage(input: { sessionId?: string; message: string; history?: unknown[] }) {}
export async function checkHealth() {}
```

State needed by the UI:

```ts
type ChatState = {
  sessionId: string | null;
  market: "US" | "CA" | "UK" | "AU" | "VN" | "EU";
  month: number;
  messages: ChatMessage[];
  suggestions: string[];
  recommendedItems: RecommendedItem[];
  selectedItem: RecommendedItem | null;
  orderDraftStatus: "empty" | "selected" | "collecting" | "confirming" | "disabled" | "created";
};
```

Important state rules:

- Reuse `sessionId` returned by `/agent/chat` for all subsequent messages in the same conversation.
- Keep `selectedItem` locally when user clicks `Đặt đơn`; backend draft response may not include image fields again.
- Render `data.items` as product cards only when `intent = search_order_items` and `data.items.length > 0`.
- Render country chips only when `data.clarification_required = true` and `data.missing_field = country`.

---

## 12. Implementation acceptance checklist

- [ ] Uses `docs/skill_FE/design.md` tokens, not random colors/spacing.
- [ ] Has left history sidebar on desktop.
- [ ] Has central chat stream with suggested question chips.
- [ ] Has product suggestion cards below recommendation results.
- [ ] Has right order panel with empty and filled states.
- [ ] `Đặt đơn` fills selected product image/SKU/color/size/quantity/country/cost summary.
- [ ] Missing-country clarification shows market chips and no order CTA.
- [ ] Product card supports long text with ellipsis.
- [ ] Recommendation loading state shows skeleton/pulse for image, price, shipping, delivery and SLA fields.
- [ ] Changing Header market while order panel is dirty shows confirmation dialog before clearing draft.
- [ ] Recommendation table converts to stacked product cards below 1024px.
- [ ] Mobile layout moves order panel to bottom sheet/drawer.
- [ ] Keyboard focus is visible on all buttons, chips, inputs, and history rows.
