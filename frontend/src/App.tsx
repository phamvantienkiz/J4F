import { FormEvent, useEffect, useRef, useState } from "react";
import { AgentResponse, RecommendedItem, SuggestedQuestions, checkHealth, checkReady, getSuggestions, sendChatMessage } from "./api/agent";

type ChatMessage = {
  id: string;
  role: "user" | "assistant";
  text: string;
  response?: AgentResponse;
  steps?: Array<{ step: string; message: string }>;
  isStreaming?: boolean;
};

type ChatSession = {
  id: string;
  title: string;
  sessionId: string | null;
  messages: ChatMessage[];
  language: Language;
};

type OrderForm = {
  shipping_name: string;
  shipping_address1: string;
  shipping_city: string;
  shipping_state: string;
  shipping_zip: string;
  shipping_country: string;
  reference_order_id: string;
  design_url_front: string;
  print_sides: "front" | "both";
};

type Language = "vi" | "en";

const copy = {
  vi: {
    nav: ["Catalog", "Dịch vụ", "Cách hoạt động", "Trợ giúp"],
    language: "Ngôn ngữ",
    market: "Thị trường",
    month: "Tháng",
    apiLive: "API Live",
    apiWarming: "API Warming",
    apiOffline: "API Offline",
    announcement: "Ra quyết định SKU nhanh · draft sandbox an toàn",
    heroPrefix: "Gợi ý POD đáng tin cậy cho seller bán tại",
    heroText: "So sánh xưởng, phí ship, thời gian giao, SLA và profit trước khi tạo BurgerPrints sandbox order draft.",
    skuChecks: "lượt kiểm SKU",
    history: "Lịch sử",
    newChat: "Mới",
    recent: "Gần đây",
    marketContext: "Bối cảnh thị trường",
    suggestedQuestions: "Câu hỏi gợi ý",
    assistantTitle: "Hỏi trợ lý fulfillment BurgerPrints",
    assistantDesc: "Bắt đầu bằng câu hỏi theo market hoặc hỏi về SKU, shipping, delivery và profit.",
    emptyTitle: "Sẵn sàng so sánh POD SKU",
    emptyDesc: "Thử: Tìm áo T-shirt Black size M profit cao nhất.",
    productSuggestions: "Gợi ý sản phẩm",
    options: "lựa chọn",
    placeholder: "Hỏi: Tìm T-shirt Black size M ship US profit cao nhất...",
    sending: "Đang gửi",
    send: "Gửi",
    orderTitle: "Tạo sandbox order",
    checkoutTab: "Checkout",
    ordersTab: "Lịch sử đơn",
    selectProduct: "Chọn sản phẩm được gợi ý",
    selectProductDesc: "SKU tốt nhất được chọn sẵn để xem nhanh. Checkout sẽ dùng dữ liệu thật từ API.",
    productInspector: "Product Inspector",
    shippingInfo: "Shipping Info",
    frontDesign: "Front Design",
    designUrlHint: "Dán URL hoặc chọn ảnh từ máy để preview mặt trước.",
    chooseLocalImage: "Chọn ảnh từ máy",
    localImagePreview: "Ảnh local đang đè preview; để đặt đơn cần dán URL public vào ô URL design mặt trước.",
    localImageNeedsUrl: "Ảnh local chỉ dùng để preview. BurgerPrints API yêu cầu URL http/https public, hãy dán URL design mặt trước rồi đặt đơn.",
    orderPanelNotice: "Trạng thái đơn",
    orderTotal: "Tổng tiền lưu đơn",
    billingSummary: "Billing Summary",
    backDesignPending: "Back design: pending, không tính phí.",
    orderHistoryEmpty: "Chưa có lịch sử đơn trong phiên này.",
    createdTitle: "Sandbox order đã tạo",
    createdDesc: "Bạn có thể tiếp tục kiểm tra SKU khác hoặc xem lại thông tin đơn trong BurgerPrints.",
    supplier: "Xưởng",
    total: "Landed Cost",
    sellPrice: "Giá bán",
    delivery: "Giao hàng",
    fullName: "Họ tên",
    address: "Địa chỉ dòng 1",
    city: "Thành phố",
    state: "Bang/Tỉnh",
    zip: "ZIP",
    country: "Quốc gia",
    referenceOrder: "Mã đơn tham chiếu",
    designUrl: "URL design mặt trước",
    createDraft: "Tạo sandbox draft",
    updateFields: "Cập nhật thông tin",
    confirmCreate: "Xác nhận tạo sandbox order",
    order: "Đặt đơn",
    skuOption: "Chọn SKU / màu / xưởng",
    color: "Màu",
    size: "Size",
    base: "Base Cost",
    printCost: "In mặt thứ hai",
    ship: "Ship",
    grossMargin: "Biên lợi nhuận gộp",
    marginMissing: "Cần giá bán",
    missingInfoTitle: "Bổ sung thông tin còn thiếu",
    missingInfoDesc: "Thêm các trường này để agent tính/so sánh chính xác hơn.",
    pricePrompt: "Thêm giá bán để tính margin",
    pricePromptExample: "giá bán là 15 đô",
    marketPrompt: "Thêm market ship",
    marketPromptExample: "ship US",
    productPrompt: "Thêm loại sản phẩm",
    productPromptExample: "tìm T-shirt ship US",
    deliveryMissing: "Cần market ship — ví dụ: giao hàng ở US",
    bestPick: "Lựa chọn tốt nhất",
    catalogRecommendation: "Gợi ý từ Catalog",
    viewCards: "Kiểm tra thông tin rồi bấm Đặt đơn trên card này hoặc panel bên phải khi muốn tạo sandbox draft.",
    apiError: "Không gọi được API. Hãy kiểm tra backend đang chạy rồi thử gửi lại.",
  },
  en: {
    nav: ["Catalog", "Services", "How it works", "Help Center"],
    language: "Language",
    market: "Market",
    month: "Month",
    apiLive: "API Live",
    apiWarming: "API Warming",
    apiOffline: "API Offline",
    announcement: "Faster SKU decisions · sandbox-safe order drafts",
    heroPrefix: "Reliable POD recommendations for sellers selling into",
    heroText: "Compare supplier, shipping fee, delivery, SLA and profit before creating a BurgerPrints sandbox order draft.",
    skuChecks: "SKU checks",
    history: "History",
    newChat: "New",
    recent: "Recent",
    marketContext: "Market context",
    suggestedQuestions: "Suggested questions",
    assistantTitle: "Ask your BurgerPrints fulfillment assistant",
    assistantDesc: "Start with market-aware questions or ask for SKU, shipping, delivery and profit recommendations.",
    emptyTitle: "Ready to compare POD SKUs",
    emptyDesc: "Try: Find Black size M T-shirt highest profit.",
    productSuggestions: "Product suggestions",
    options: "options",
    placeholder: "Ask: Find Black size M T-shirt ship US highest profit...",
    sending: "Sending",
    send: "Send",
    orderTitle: "Create sandbox order",
    checkoutTab: "Checkout",
    ordersTab: "Orders",
    selectProduct: "Select a recommended product",
    selectProductDesc: "The best SKU is preselected for review. Checkout uses real API data only.",
    productInspector: "Product Inspector",
    shippingInfo: "Shipping Info",
    frontDesign: "Front Design",
    designUrlHint: "Paste a URL or choose a local image to preview the front side.",
    chooseLocalImage: "Choose local image",
    localImagePreview: "Local image overrides the preview; paste a public front design URL to place the order.",
    localImageNeedsUrl: "Local image is preview-only. BurgerPrints API requires a public http/https URL, so paste the front design URL before ordering.",
    orderPanelNotice: "Order status",
    orderTotal: "Order total to save",
    billingSummary: "Billing Summary",
    backDesignPending: "Back design: pending, not charged.",
    orderHistoryEmpty: "No order history in this session yet.",
    createdTitle: "Sandbox order created",
    createdDesc: "You can keep reviewing SKUs or check the order details in BurgerPrints.",
    supplier: "Supplier",
    total: "Landed Cost",
    sellPrice: "Sell",
    delivery: "Delivery",
    fullName: "Full name",
    address: "Address line 1",
    city: "City",
    state: "State",
    zip: "ZIP",
    country: "Country",
    referenceOrder: "Reference order ID",
    designUrl: "Front design URL",
    createDraft: "Create sandbox draft",
    updateFields: "Update fields",
    confirmCreate: "Confirm create sandbox order",
    order: "Order",
    skuOption: "Choose SKU / color / supplier",
    color: "Color",
    size: "Size",
    base: "Base",
    printCost: "Print Cost",
    ship: "Ship",
    grossMargin: "Gross Profit Margin",
    marginMissing: "Need selling price",
    missingInfoTitle: "Add missing info",
    missingInfoDesc: "Add these fields so the agent can calculate and compare more accurately.",
    pricePrompt: "Add selling price to calculate margin",
    pricePromptExample: "selling price is 15 dollars",
    marketPrompt: "Add ship market",
    marketPromptExample: "ship US",
    productPrompt: "Add product type",
    productPromptExample: "find T-shirt ship US",
    deliveryMissing: "Need ship market — e.g. ship to US",
    bestPick: "Best pick",
    catalogRecommendation: "Catalog recommendation",
    viewCards: "Review the SKU, then click Order on this card or the right panel when you want to create a sandbox draft.",
    apiError: "Could not reach the API. Check that the backend is running, then try again.",
  },
} satisfies Record<Language, Record<string, string | string[]>>;

type CopyText = typeof copy.vi;

const markets = ["US", "CA", "UK", "AU", "VN", "EU"];
const months = [
  "January",
  "February",
  "March",
  "April",
  "May",
  "June",
  "July",
  "August",
  "September",
  "October",
  "November",
  "December",
];

const emptyOrderForm: OrderForm = {
  shipping_name: "",
  shipping_address1: "",
  shipping_city: "",
  shipping_state: "",
  shipping_zip: "",
  shipping_country: "US",
  reference_order_id: "",
  design_url_front: "",
  print_sides: "front",
};

function detectLanguage(text: string): Language {
  const normalized = text.toLowerCase();
  if (/[à-ỹđ]/i.test(text) || /\b(tìm|gợi|mùa|nên|bán|ship|đặt|đơn|xưởng|lãi|giá|vận chuyển)\b/.test(normalized)) {
    return "vi";
  }
  return "en";
}

function englishSuggestions(data: SuggestedQuestions | null) {
  if (!data) return [];
  const product = data.product_types?.[0] || "T-shirt";
  const event = data.events?.[0] || "current season";
  return [
    `Which POD products should I sell in ${data.country} this ${data.season}?`,
    `Suggest ${product} ideas for ${data.country} this month`,
    `Which ${data.country} events should I design for around ${event}?`,
    `Find ${product} SKUs for ${data.country} with good delivery time`,
  ];
}

function getDynamicSuggestions(
  latestResponse: AgentResponse | undefined,
  language: Language,
  defaultSuggestions: string[],
  orderStatus: string,
  selectedItem: RecommendedItem | null
): string[] {
  const isVi = language === "vi";

  // 1. Nếu Agent đang yêu cầu làm rõ trường thông tin cụ thể (clarification_required)
  if (latestResponse?.data?.clarification_required) {
    const missingField = latestResponse.data.missing_field;
    if (missingField === "product_type") {
      return isVi
        ? ["Tôi muốn tìm T-Shirt", "Tôi muốn tìm Hoodie", "Tôi muốn tìm Ceramic Mug", "Tôi muốn tìm Sweatshirt"]
        : ["I want to find T-Shirt", "I want to find Hoodie", "I want to find Ceramic Mug", "I want to find Sweatshirt"];
    }
    if (missingField === "country") {
      return isVi
        ? ["Giao hàng tại thị trường US", "Giao hàng tại thị trường VN", "Giao hàng tại thị trường DE", "Giao hàng tại thị trường UK"]
        : ["Ship to United States (US)", "Ship to Vietnam (VN)", "Ship to Germany (DE)", "Ship to United Kingdom (GB)"];
    }
  }

  // 2. Nếu thiếu giá bán để tính Margin
  const bestItem = latestResponse?.data?.items?.[0] || selectedItem;
  if (bestItem && typeof bestItem.selling_price !== "number") {
    return isVi
      ? ["Đặt giá bán lẻ là $15", "Đặt giá bán lẻ là $20", "Đặt giá bán lẻ là $25", "Tính margin với giá bán lẻ $30"]
      : ["Set selling price to $15", "Set selling price to $20", "Set selling price to $25", "Calculate margin with selling price $30"];
  }

  // 3. Nếu đang đặt đơn nhưng thiếu thông tin địa chỉ
  if (orderStatus === "collecting" || latestResponse?.intent === "create_order") {
    return isVi
      ? ["Tên người nhận: Nguyễn Văn A", "Địa chỉ: 123 Main St, New York", "Thành phố: New York, Zip: 10001", "Xác nhận tạo đơn hàng"]
      : ["Name: John Doe", "Address: 123 Main St, New York", "City: New York, Zip: 10001", "Confirm creating order"];
  }

  // 4. Nếu vừa tạo order thành công, gợi ý các câu tiếp theo
  if (latestResponse?.data?.status === "created") {
    return isVi
      ? ["Kiểm tra số dư tài khoản", "Tìm sản phẩm bán chạy tiếp theo", "So sánh giá ship sản phẩm khác"]
      : ["Check my account balance", "Find next best seller product", "Compare shipping fees for other products"];
  }

  // 5. Mặc định trả về gợi ý theo mùa
  return defaultSuggestions;
}

function formatMoney(value?: number) {
  return typeof value === "number" ? `$${value.toFixed(2)}` : "N/A";
}

function formatPercent(value?: number, missing = "N/A") {
  return typeof value === "number" ? `${value.toFixed(2)}%` : missing;
}

function formatDelivery(value: string | undefined, labels: CopyText) {
  return value || String(labels.deliveryMissing);
}

function formatSellingPrice(item: RecommendedItem, labels: CopyText) {
  return typeof item.selling_price === "number" ? formatMoney(item.selling_price) : String(labels.marginMissing);
}

function printCostValue(item: RecommendedItem) {
  return typeof item.second_item_price === "number" ? item.second_item_price : item.clone_price;
}

function formatPrintCost(item: RecommendedItem, printSides?: "front" | "both") {
  const sides = printSides || item.print_sides;
  return formatMoney(sides === "both" ? (printCostValue(item) || 0) : 0);
}

function formatLandedCost(item: RecommendedItem) {
  return formatMoney(typeof item.landed_cost === "number" ? item.landed_cost : item.total_cost);
}

function fullOrderTotalValue(item: RecommendedItem, printSides?: "front" | "both") {
  const printCost = printSides === "both" ? (printCostValue(item) || 0) : 0;
  return (item.base_cost || 0) + printCost + (item.shipping_fee || 0);
}

function formatFullOrderTotal(item: RecommendedItem, printSides?: "front" | "both") {
  return formatMoney(fullOrderTotalValue(item, printSides));
}

function missingRecommendationPrompts(item: RecommendedItem, labels: CopyText) {
  const prompts: Array<{ label: string; message: string }> = [];
  if (typeof item.selling_price !== "number") {
    prompts.push({ label: String(labels.pricePrompt), message: String(labels.pricePromptExample) });
  }
  if (formatDelivery(item.delivery_time, labels) === labels.deliveryMissing) {
    prompts.push({ label: String(labels.marketPrompt), message: String(labels.marketPromptExample) });
  }
  if (!item.product_name && !item.display_name) {
    prompts.push({ label: String(labels.productPrompt), message: String(labels.productPromptExample) });
  }
  return prompts;
}

function formatCarrier(value?: string[] | string) {
  if (Array.isArray(value)) return value.join(", ");
  return value || "N/A";
}

const colorHexByName: Record<string, string> = {
  ash: "#d6d6d1",
  azalea: "#dd6fa1",
  black: "#1f2428",
  blue: "#3b82f6",
  "blue jean": "#6d8fb3",
  cardinal: "#a30d35",
  carolina: "#7fb1df",
  charcoal: "#60636a",
  "coral silk": "#ff6384",
  "dark chocolate": "#2b211f",
  "dark heather": "#43515b",
  forest: "#17352b",
  gold: "#f2aa12",
  graphite: "#70716d",
  grey: "#9ca3af",
  "heather navy": "#344653",
  heliconia: "#dc3d79",
  "ice grey": "#d8d6d1",
  "irish green": "#00a34a",
  ivory: "#f3ebd8",
  kiwi: "#85a94b",
  "light blue": "#b7d4e5",
  "light pink": "#e6c4d6",
  maroon: "#6a2a45",
  moss: "#7c7a58",
  natural: "#e6d2bd",
  navy: "#1f2a44",
  orange: "#f76035",
  orchid: "#c7a0cb",
  pepper: "#605f5a",
  purple: "#4b3279",
  red: "#df0038",
  royal: "#214f92",
  sand: "#c8c0b2",
  sapphire: "#0b8abc",
  "sport grey": "#a7a9ac",
  tropical: "#0090a0",
  violet: "#7f8edd",
  white: "#ffffff",
  yellow: "#f5df9b",
  daisy: "#ffdf00",
};

function colorHex(color?: string) {
  const key = (color || "").toLowerCase().replace(/[-_]/g, " ").trim();
  if (colorHexByName[key]) return colorHexByName[key];

  // Fallback tìm kiếm tương đối (substring matching)
  for (const name in colorHexByName) {
    if (key.includes(name) || name.includes(key)) {
      return colorHexByName[name];
    }
  }
  return "#e2e8f0";
}

function productName(item: RecommendedItem) {
  return item.product_name || item.display_name || "Recommended product";
}

function imageUrl(item: RecommendedItem | null) {
  if (!item) return "";
  const url = item.mockup_url || item.image_url || "";
  if (!url || url.includes("api.burgerprints.com")) {
    const name = (item.product_name || item.display_name || "").toLowerCase();
    if (name.includes("hoodie")) {
      return "https://d1ud88wu9m1k4s.cloudfront.net/assets/base-mockups/burgerprints/062025/USG18500.png";
    }
    if (name.includes("sweatshirt") || name.includes("sweater")) {
      return "https://d1ud88wu9m1k4s.cloudfront.net/assets/base-mockups/burgerprints/062025/USG18000.png";
    }
    if (name.includes("mug") || name.includes("ceramic")) {
      return "https://d1ud88wu9m1k4s.cloudfront.net/assets/base-mockups/burgerprints/062025/US11OZ.png";
    }
    return "https://d1ud88wu9m1k4s.cloudfront.net/assets/base-mockups/burgerprints/062025/USG5000.png";
  }
  return url;
}

function hasTypedOrderFields(form: OrderForm) {
  return Object.entries(form).some(([key, value]) => key !== "shipping_country" && value.trim());
}

function defaultReferenceOrderId(item: RecommendedItem | null) {
  const sku = item?.sku || "SKU";
  return `SANDBOX-${sku}-${Date.now()}`;
}

function isOrderConfirmationPrompt(value?: string) {
  const text = (value || "").toLowerCase();
  return text.includes("confirm create sandbox order") || text.includes("xác nhận tạo sandbox order");
}

function isSandboxOrderCreated(response: AgentResponse) {
  const answer = (response.answer || "").toLowerCase();
  return response.data?.status === "created" || Boolean(response.data?.id) || answer.includes("sandbox order đã được tạo thành công") || answer.includes("sandbox order created");
}

function displayMessageText(message: ChatMessage) {
  return message.text;
}

function renderMarkdown(text: string) {
  if (!text) return "";

  // 1. Escape HTML for security (XSS prevention)
  let escaped = text
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#039;");

  // 2. Parse inline styling (bold, italic, inline code)
  escaped = escaped.replace(/\*\*(.*?)\*\*/g, "<strong>$1</strong>");
  escaped = escaped.replace(/\*(.*?)\*/g, "<em>$1</em>");
  escaped = escaped.replace(/`(.*?)`/g, "<code>$1</code>");

  // 3. Split into lines to process block elements
  const lines = escaped.split("\n");
  let html = "";
  let inList = false;
  let inBlockquote = false;
  let blockquoteContent: string[] = [];

  const closeList = () => {
    if (inList) {
      html += "</ul>";
      inList = false;
    }
  };

  const closeBlockquote = () => {
    if (inBlockquote) {
      html += `<blockquote>${blockquoteContent.join("<br />")}</blockquote>`;
      blockquoteContent = [];
      inBlockquote = false;
    }
  };

  for (let i = 0; i < lines.length; i++) {
    const line = lines[i];
    const trimmed = line.trim();

    // Check for Horizontal Rule
    if (trimmed === "---") {
      closeList();
      closeBlockquote();
      html += "<hr />";
      continue;
    }

    // Check for Blockquote
    // Note: '>' is escaped to '&gt;'
    if (trimmed.startsWith("&gt;")) {
      closeList();
      if (!inBlockquote) {
        inBlockquote = true;
      }
      let content = trimmed.slice(4);
      if (content.startsWith(" ")) {
        content = content.slice(1);
      }
      blockquoteContent.push(content);
      continue;
    }

    // Check for Bullet List Item
    if (trimmed.startsWith("- ")) {
      closeBlockquote();
      if (!inList) {
        html += '<ul style="margin: 0 0 12px 0; padding-left: 20px;">';
        inList = true;
      }
      html += `<li>${trimmed.slice(2)}</li>`;
      continue;
    }

    // Empty line separates paragraphs / blocks
    if (trimmed === "") {
      closeList();
      closeBlockquote();
      continue;
    }

    // Regular text line
    closeList();
    closeBlockquote();

    // Group consecutive regular text lines into one paragraph separated by <br />
    let paragraphLines = [trimmed];
    while (i + 1 < lines.length) {
      const nextTrimmed = lines[i + 1].trim();
      if (nextTrimmed === "" || nextTrimmed === "---" || nextTrimmed.startsWith("&gt;") || nextTrimmed.startsWith("- ")) {
        break;
      }
      paragraphLines.push(nextTrimmed);
      i++;
    }
    html += `<p style="margin: 0 0 12px 0;">${paragraphLines.join("<br />")}</p>`;
  }

  closeList();
  closeBlockquote();

  return html;
}

function ThoughtProcessContainer({
  steps,
  isStreaming,
  hasMessageText,
}: {
  steps: Array<{ step: string; message: string }>;
  isStreaming?: boolean;
  hasMessageText?: boolean;
}) {
  const [shouldRender, setShouldRender] = useState(isStreaming === true);
  const [isFadingOut, setIsFadingOut] = useState(false);

  useEffect(() => {
    if (isStreaming) {
      setShouldRender(true);
      setIsFadingOut(false);
    } else if (shouldRender) {
      setIsFadingOut(true);
      const timer = setTimeout(() => {
        setShouldRender(false);
        setIsFadingOut(false);
      }, 300); // Đợi hiệu ứng fade-out 300ms hoàn tất trước khi unmount
      return () => clearTimeout(timer);
    }
  }, [isStreaming, shouldRender]);

  useEffect(() => {
    if (hasMessageText && shouldRender) {
      setIsFadingOut(true);
      const timer = setTimeout(() => {
        setShouldRender(false);
        setIsFadingOut(false);
      }, 300);
      return () => clearTimeout(timer);
    }
  }, [hasMessageText, shouldRender]);

  if (!shouldRender || !steps || steps.length === 0) return null;

  const allStepsFired = steps.length >= 3;
  const showWaiting = isStreaming && !hasMessageText && allStepsFired;

  if (showWaiting) {
    return (
      <div className={`thought-process-block ${isFadingOut ? "fade-out" : ""}`}>
        <span className="thought-step-dot" />
        <span className="text-waiting-shimmer">Trợ lý đang xử lý câu trả lời</span>
        <span className="loading-dot">.</span>
        <span className="loading-dot">.</span>
        <span className="loading-dot">.</span>
      </div>
    );
  }

  const activeStep = steps[steps.length - 1];
  if (!activeStep) return null;

  return (
    <div className={`thought-process-block ${isFadingOut ? "fade-out" : ""}`}>
      <span className="thought-step-dot" />
      <span key={activeStep.message} className="step-text-animate">
        {activeStep.message}
      </span>
    </div>
  );
}

export default function App() {
  const [apiOnline, setApiOnline] = useState(false);
  const [apiWarming, setApiWarming] = useState(false);
  const [isAuthenticated, setIsAuthenticated] = useState(false);
  const [language, setLanguage] = useState<Language>("vi");
  const [market, setMarket] = useState("US");
  const [month, setMonth] = useState(new Date().getMonth() + 1);
  const [pendingMarket, setPendingMarket] = useState<string | null>(null);
  const [suggestions, setSuggestions] = useState<SuggestedQuestions | null>(null);
  const [activeChatId, setActiveChatId] = useState<string>(() => crypto.randomUUID());
  const [chatSessions, setChatSessions] = useState<ChatSession[]>([]);
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [recommendedItems, setRecommendedItems] = useState<RecommendedItem[]>([]);
  const [selectedItem, setSelectedItem] = useState<RecommendedItem | null>(null);
  const [orderForm, setOrderForm] = useState<OrderForm>(emptyOrderForm);
  const [frontDesignPreviewUrl, setFrontDesignPreviewUrl] = useState("");
  const [orderNotice, setOrderNotice] = useState("");
  const [showOrderSuccessCenter, setShowOrderSuccessCenter] = useState(false);
  const [createdOrderTotal, setCreatedOrderTotal] = useState("");
  const [orderStatus, setOrderStatus] = useState<"empty" | "selected" | "collecting" | "confirming" | "disabled" | "created">("empty");
  const [orderPanelTab, setOrderPanelTab] = useState<"checkout" | "orders">("checkout");
  const [pendingSuggestion, setPendingSuggestion] = useState<string | null>(null);
  const chatStreamRef = useRef<HTMLDivElement | null>(null);
  const suggestionTimerRef = useRef<number | null>(null);

  const t = copy[language];
  const latestResponse = [...messages].reverse().find((message) => message.response)?.response;
  const defaultSuggestions = language === "en" ? englishSuggestions(suggestions) : suggestions?.suggestions || [];
  const displayedSuggestions = getDynamicSuggestions(latestResponse, language, defaultSuggestions, orderStatus, selectedItem);
  const orderDirty = orderStatus !== "selected" && (Boolean(selectedItem) || hasTypedOrderFields(orderForm));
  const orderReadyToConfirm = orderStatus === "confirming" || isOrderConfirmationPrompt(orderNotice);
  const needsCountry = latestResponse?.data?.clarification_required && latestResponse.data.missing_field === "country";
  const showTopSuggestions = displayedSuggestions.length > 0 && !showOrderSuccessCenter && messages.length === 0;
  const showBottomSuggestions = displayedSuggestions.length > 0 && messages.length > 0;
  const isStreamingActive = messages.length > 0 && messages[messages.length - 1].role === "assistant" && messages[messages.length - 1].isStreaming === true;

  useEffect(() => {
    let cancelled = false;
    let timer: number | undefined;

    async function refreshReady() {
      try {
        await checkHealth();
        const ready = await checkReady();
        if (cancelled) return;
        setApiOnline(ready.ready);
        setApiWarming(!ready.ready && ready.warming);
        if (!ready.ready && ready.warming) {
          timer = window.setTimeout(refreshReady, 1000);
        }
      } catch {
        if (cancelled) return;
        setApiOnline(false);
        setApiWarming(false);
      }
    }

    refreshReady();
    return () => {
      cancelled = true;
      if (timer) window.clearTimeout(timer);
    };
  }, []);

  useEffect(() => {
    if (apiOnline && orderStatus === "disabled" && orderNotice === t.apiError) {
      setOrderStatus(selectedItem ? "selected" : "empty");
      setOrderNotice("");
    }
  }, [apiOnline, orderNotice, orderStatus, selectedItem, t.apiError]);

  useEffect(() => {
    getSuggestions(market, month)
      .then(setSuggestions)
      .catch(() => setSuggestions(null));
  }, [market, month]);

  useEffect(() => () => {
    if (suggestionTimerRef.current) window.clearTimeout(suggestionTimerRef.current);
  }, []);

  useEffect(() => {
    const stream = chatStreamRef.current;
    if (!stream) return;
    const frame = window.requestAnimationFrame(() => {
      stream.scrollTo({ top: stream.scrollHeight, behavior: "smooth" });
    });
    return () => window.cancelAnimationFrame(frame);
  }, [messages.length, loading]);

  function persistChatSession(nextMessages: ChatMessage[], nextSessionId: string | null, nextLanguage: Language) {
    const firstUserMessage = nextMessages.find((message) => message.role === "user");
    if (!firstUserMessage) return;

    const session: ChatSession = {
      id: activeChatId,
      title: firstUserMessage.text,
      sessionId: nextSessionId,
      messages: nextMessages,
      language: nextLanguage,
    };

    setChatSessions((current) => [session, ...current.filter((item) => item.id !== activeChatId)].slice(0, 8));
  }

  function resetDraftUi(nextMarket = market) {
    if (frontDesignPreviewUrl) URL.revokeObjectURL(frontDesignPreviewUrl);
    setFrontDesignPreviewUrl("");
    setOrderNotice("");
    setShowOrderSuccessCenter(false);
    setCreatedOrderTotal("");
    setRecommendedItems([]);
    setSelectedItem(null);
    setOrderForm({ ...emptyOrderForm, shipping_country: nextMarket });
    setOrderStatus("empty");
    setOrderPanelTab("checkout");
  }

  function startNewChat() {
    setActiveChatId(crypto.randomUUID());
    setSessionId(null);
    setMessages([]);
    setInput("");
    resetDraftUi();
  }

  function openChatSession(chat: ChatSession) {
    setActiveChatId(chat.id);
    setSessionId(chat.sessionId);
    setMessages(chat.messages);
    setLanguage(chat.language);
    setInput("");
    const latestItems = [...chat.messages].reverse().find((message) => message.response?.data?.items?.length)?.response?.data?.items || [];
    setRecommendedItems(latestItems);
    setSelectedItem(null);
    setOrderForm({ ...emptyOrderForm, shipping_country: market });
    setOrderStatus("empty");
  }

  function applyAgentResponse(response: AgentResponse) {
    setSessionId(response.session_id);

    // Đồng bộ các trường thông tin từ Backend slots (response.params)
    if (response.params) {
      if (response.params.country) {
        setMarket(String(response.params.country));
      } else if (response.params.target_market) {
        setMarket(String(response.params.target_market));
      }
      if (typeof response.params.month === "number") {
        setMonth(response.params.month);
      } else if (typeof response.params.month === "string") {
        const mVal = parseInt(response.params.month, 10);
        if (!isNaN(mVal)) setMonth(mVal);
      }

      setOrderForm((current) => {
        const next = { ...current };
        if (response.params?.country) {
          next.shipping_country = String(response.params.country);
        }
        if (response.params?.print_sides) {
          next.print_sides = response.params.print_sides as "front" | "both";
        }

        const addr = response.params?.shipping_address as Record<string, string> | undefined;
        if (addr) {
          if (addr.full_name) next.shipping_name = addr.full_name;
          if (addr.address1) next.shipping_address1 = addr.address1;
          if (addr.city) next.shipping_city = addr.city;
          if (addr.zip_code) next.shipping_zip = addr.zip_code;
          if (addr.country) next.shipping_country = addr.country;
        }
        return next;
      });

      // Đồng bộ trạng thái quy trình đặt đơn
      if (response.intent === "create_order") {
        setOrderPanelTab("checkout");
        if (response.confirmation_required) {
          setOrderStatus("confirming");
        } else if (response.data?.status === "created") {
          setOrderStatus("created");
        } else {
          setOrderStatus("collecting");
        }
      }
    }

    const items = response.data?.items || [];
    if (items.length) {
      setShowOrderSuccessCenter(false);
      setRecommendedItems(items);

      // Chọn item khớp với SKU từ slot backend nếu có
      const slotSku = response.params?.sku;
      const matchedItem = slotSku ? items.find((item) => item.sku === slotSku) : null;
      setSelectedItem(matchedItem || items[0]);

      // Chỉ đặt status là selected nếu không phải đang trong flow tạo đơn
      if (response.intent !== "create_order") {
        setOrderStatus("selected");
        setOrderPanelTab("checkout");
      }
    }

    if (response.confirmation_required) setOrderStatus("confirming");
    if (response.data?.status === "disabled") setOrderStatus("disabled");

    if (isSandboxOrderCreated(response)) {
      setCreatedOrderTotal(selectedItem ? formatFullOrderTotal(selectedItem, orderForm.print_sides) : "");
      if (frontDesignPreviewUrl) URL.revokeObjectURL(frontDesignPreviewUrl);
      setOrderStatus("created");
      setShowOrderSuccessCenter(true);
      setRecommendedItems([]);
      setSelectedItem(null);
      setOrderForm({ ...emptyOrderForm, shipping_country: market });
      setFrontDesignPreviewUrl("");
    }
  }

  async function sendSilentAgentCommand(messageText: string) {
    const trimmed = messageText.trim();
    if (!trimmed || loading) return null;

    setLoading(true);
    try {
      const response = await sendChatMessage(
        { sessionId, message: trimmed, history: [] },
        (chunk) => {
          if (chunk.step && chunk.message) {
            setOrderNotice(`*${chunk.message}*`);
          }
        }
      );
      applyAgentResponse(response);
      if (isOrderConfirmationPrompt(response.answer)) setOrderStatus("confirming");
      setOrderNotice(response.answer || "");
      return response;
    } catch {
      setOrderStatus("disabled");
      setOrderNotice(String(t.apiError));
      return null;
    } finally {
      setLoading(false);
    }
  }

  async function submitMessage(messageText: string) {
    const trimmed = messageText.trim();
    if (!trimmed || loading) return;

    const nextLanguage = language;
    setShowOrderSuccessCenter(false);
    const userMessage: ChatMessage = { id: crypto.randomUUID(), role: "user", text: trimmed };
    const assistantMessageId = crypto.randomUUID();
    const initialAssistantMessage: ChatMessage = {
      id: assistantMessageId,
      role: "assistant",
      text: "",
      steps: [],
      isStreaming: true,
    };

    const nextMessages = [...messages, userMessage, initialAssistantMessage];
    setMessages(nextMessages);
    persistChatSession(nextMessages, sessionId, nextLanguage);
    setInput("");
    setLoading(true);

    let currentAssistantText = "";
    let currentAssistantSteps: Array<{ step: string; message: string }> = [];
    let startedStreamingTokens = false;

    const onChunk = (chunk: any) => {
      if (chunk.step && chunk.message) {
        const exists = currentAssistantSteps.some((s) => s.step === chunk.step);
        if (!exists) {
          currentAssistantSteps = [...currentAssistantSteps, { step: chunk.step, message: chunk.message }];
          setMessages((prev) =>
            prev.map((msg) =>
              msg.id === assistantMessageId
                ? { ...msg, steps: currentAssistantSteps }
                : msg
            )
          );
        }
      } else if (chunk.token) {
        if (!startedStreamingTokens) {
          startedStreamingTokens = true;
        }
        currentAssistantText += chunk.token;
        setMessages((prev) =>
          prev.map((msg) =>
            msg.id === assistantMessageId
              ? { ...msg, text: currentAssistantText }
              : msg
          )
        );
      } else if (chunk.session_id && chunk.answer) {
        currentAssistantText = chunk.answer;
        setMessages((prev) =>
          prev.map((msg) =>
            msg.id === assistantMessageId
              ? {
                  ...msg,
                  text: currentAssistantText,
                  response: chunk,
                  isStreaming: false,
                }
              : msg
          )
        );
        applyAgentResponse(chunk);
      }
    };

    try {
      const response = await sendChatMessage(
        { sessionId, message: trimmed, history: [] },
        onChunk
      );
      setMessages((finalPrev) => {
        persistChatSession(finalPrev, response.session_id, nextLanguage);
        return finalPrev;
      });
    } catch {
      const errorText = String(copy[nextLanguage].apiError);
      setMessages((prev) =>
        prev.map((msg) =>
          msg.id === assistantMessageId
            ? { ...msg, text: errorText, isStreaming: false }
            : msg
        )
      );
      setMessages((finalPrev) => {
        persistChatSession(finalPrev, sessionId, nextLanguage);
        return finalPrev;
      });
    } finally {
      setLoading(false);
    }
  }

  function submitSuggestedMessage(suggestion: string) {
    if (loading) return;
    if (suggestionTimerRef.current) window.clearTimeout(suggestionTimerRef.current);
    setPendingSuggestion(suggestion);
    setInput(suggestion);
    suggestionTimerRef.current = window.setTimeout(() => {
      setPendingSuggestion(null);
      suggestionTimerRef.current = null;
      submitMessage(suggestion);
    }, 360);
  }

  function sendCurrentInput() {
    if (suggestionTimerRef.current) {
      window.clearTimeout(suggestionTimerRef.current);
      suggestionTimerRef.current = null;
    }
    setPendingSuggestion(null);
    submitMessage(input);
  }

  function onSubmit(event: FormEvent) {
    event.preventDefault();
    sendCurrentInput();
  }

  function requestMarketChange(nextMarket: string) {
    if (nextMarket === market) return;
    if (orderDirty) {
      setPendingMarket(nextMarket);
      return;
    }
    applyMarketChange(nextMarket);
  }

  function applyMarketChange(nextMarket: string) {
    setMarket(nextMarket);
    setPendingMarket(null);
    setActiveChatId(crypto.randomUUID());
    setSessionId(null);
    setMessages([]);
    setInput("");
    resetDraftUi(nextMarket);
  }

  function selectProduct(item: RecommendedItem) {
    setSelectedItem(item);
    setOrderStatus("selected");
    setOrderPanelTab("checkout");
    setOrderForm((current) => ({
      ...current,
      shipping_country: market,
    }));
  }

  function selectProductBySku(sku: string) {
    const item = recommendedItems.find((option) => option.sku === sku);
    if (item) selectProduct(item);
  }

  function updateFrontDesignUrl(value: string) {
    if (frontDesignPreviewUrl) URL.revokeObjectURL(frontDesignPreviewUrl);
    setFrontDesignPreviewUrl("");
    setOrderNotice("");
    setOrderForm((current) => ({ ...current, design_url_front: value }));
  }

  function chooseLocalFrontDesign(file: File | null) {
    if (frontDesignPreviewUrl) URL.revokeObjectURL(frontDesignPreviewUrl);
    setFrontDesignPreviewUrl(file ? URL.createObjectURL(file) : "");
    setOrderNotice(file ? String(t.localImageNeedsUrl) : "");
  }

  function frontDesignOverlayUrl() {
    return frontDesignPreviewUrl || orderForm.design_url_front.trim();
  }

  async function startOrder(item: RecommendedItem) {
    selectProduct(item);
    setOrderForm((current) => ({
      ...current,
      reference_order_id: current.reference_order_id || defaultReferenceOrderId(item),
    }));
    const skuText = item.sku ? ` SKU ${item.sku}` : "";
    const response = await sendSilentAgentCommand(language === "vi" ? `tạo sandbox order cho${skuText}` : `create sandbox order for${skuText}`);
    if (response && !response.confirmation_required && response.data?.status !== "disabled" && response.data?.status !== "created" && !response.data?.id) {
      setOrderStatus("collecting");
    }
  }

  function buildOrderFieldsMessage(item: RecommendedItem | null) {
    const fields = {
      ...orderForm,
      reference_order_id: orderForm.reference_order_id.trim() || defaultReferenceOrderId(item),
    };
    const lines = Object.entries(fields)
      .filter(([, value]) => value.trim())
      .map(([key, value]) => `${key}: ${value.trim()}`);
    if (item?.sku) lines.unshift(`quantity: ${item.quantity || 1}`);
    if (item?.sku) lines.unshift(`catalog_sku: ${item.sku}`);
    return lines.join("\n");
  }

  async function sendCurrentOrderFields(item: RecommendedItem | null) {
    if (frontDesignPreviewUrl && !orderForm.design_url_front.trim()) {
      setOrderNotice(String(t.localImageNeedsUrl));
      return null;
    }
    const message = buildOrderFieldsMessage(item);
    return message ? sendSilentAgentCommand(message) : null;
  }

  async function submitOrderFields(event: FormEvent) {
    event.preventDefault();
    await sendCurrentOrderFields(selectedItem);
  }

  async function confirmSandboxOrder(item: RecommendedItem) {
    const draftResponse = await sendCurrentOrderFields(item);
    if (!draftResponse) return;
    if (draftResponse.confirmation_required || isOrderConfirmationPrompt(draftResponse.answer)) {
      await sendSilentAgentCommand("confirm create sandbox order");
    }
  }

  if (!isAuthenticated) {
    return (
      <main className="login-shell">
        <section className="login-card" aria-label="Mock login">
          <div className="login-brand">
            <span className="brand-blue">BURGER</span><span className="brand-bolt">Agent</span>
          </div>
          <div>
            <span className="eyebrow">Contest demo</span>
            <h1>{language === "vi" ? "Đăng nhập seller" : "Seller sign in"}</h1>
            <p>{language === "vi" ? "Mock login để vào dashboard tạo sandbox order BurgerPrints." : "Mock login for the BurgerPrints sandbox order dashboard."}</p>
          </div>
          <form className="login-form" onSubmit={(event) => { event.preventDefault(); setIsAuthenticated(true); }}>
            <label>{language === "vi" ? "Email" : "Email"}<input type="email" defaultValue="seller@demo.test" required /></label>
            <label>{language === "vi" ? "Mật khẩu" : "Password"}<input type="password" defaultValue="demo1234" required /></label>
            <label>{t.language}<select value={language} onChange={(event) => setLanguage(event.target.value as Language)}><option value="vi">Tiếng Việt</option><option value="en">English</option></select></label>
            <button type="submit">{language === "vi" ? "Đăng nhập" : "Sign in"}</button>
          </form>
          <small>{language === "vi" ? "Đây là màn đăng nhập mock, không gọi API xác thực." : "This is a mock login screen; no auth API is called."}</small>
        </section>
      </main>
    );
  }

  return (
    <main className="app-shell">
      <header className="topbar">
        <div className="brand-lockup" aria-label="BURGER Agent">
          <img className="brand-mark" src="/img/logo (1).svg" alt="" aria-hidden="true" />
          <img className="brand-wordmark" src="/img/logoChu.svg" alt="BURGER Agent" />
        </div>
        <nav className="topnav" aria-label="Primary">
          {(t.nav as string[]).map((item) => <a key={item}>{item}</a>)}
        </nav>
        <div className="header-controls">
          <label className="control-pill">
            <span>{t.language}</span>
            <select value={language} onChange={(event) => setLanguage(event.target.value as Language)}>
              <option value="vi">Tiếng Việt</option>
              <option value="en">English</option>
            </select>
          </label>
          <span className={apiOnline ? "status-pill live" : "status-pill offline"}>{apiOnline ? t.apiLive : apiWarming ? t.apiWarming : t.apiOffline}</span>
          <button type="button" className="logout-button" onClick={() => setIsAuthenticated(false)}>Logout</button>
        </div>
      </header>

      <section className="hero-strip">
        <div>
          <span className="announcement">{t.announcement}</span>
          <h1>{t.heroPrefix} <span>{market}</span></h1>
          <p>{t.heroText}</p>
        </div>
        <div className="hero-card" aria-hidden="true">
          <span className="live-dot">Live</span>
          <strong>{recommendedItems.length || 247} SKU checks</strong>
          <p>{suggestions?.season || "season"} · {suggestions?.product_types?.[0] || "T-shirt"}</p>
        </div>
      </section>

      <div className="workspace-grid">
        <aside className="history-sidebar">
          <div className="section-heading">
            <span>{t.history}</span>
            <button type="button" onClick={startNewChat}>{t.newChat}</button>
          </div>
          <div className="history-group">
            <small>{t.recent}</small>
            {chatSessions.length === 0 ? (
              <p className="history-empty">{language === "vi" ? "Chưa có hộp chat nào." : "No chat boxes yet."}</p>
            ) : chatSessions.map((chat) => (
              <button key={chat.id} type="button" className={chat.id === activeChatId ? "history-item active" : "history-item"} onClick={() => openChatSession(chat)}>
                <span>{chat.title}</span>
                <small>{chat.messages.length} messages</small>
              </button>
            ))}
          </div>
          <div className="saved-prompts">
            <small>{t.marketContext}</small>
            <p>{suggestions?.weather_context || (language === "vi" ? "Đang tải bối cảnh market." : "Loading market context.")}</p>
          </div>
        </aside>

        <section className="chat-panel" aria-label="Chat workspace">
          <div className="chat-stream" ref={chatStreamRef}>
            {showTopSuggestions && (
              <div className="suggestion-bar suggestion-bar-top" aria-label={t.suggestedQuestions}>
                <span>{t.suggestedQuestions}</span>
                <div className="chips">
                  {displayedSuggestions.map((suggestion) => (
                    <button key={suggestion} type="button" className={pendingSuggestion === suggestion ? "preparing" : ""} onClick={() => submitSuggestedMessage(suggestion)} disabled={loading || Boolean(pendingSuggestion)}>{suggestion}</button>
                  ))}
                </div>
              </div>
            )}
            {messages.length === 0 && !showOrderSuccessCenter && (
              <div className="empty-chat">
                <h3>{t.emptyTitle}</h3>
                <p>{t.emptyDesc}</p>
              </div>
            )}
            {messages.map((message) => {
              const hasContent = displayMessageText(message) || message.response?.data?.items?.length || message.response?.data?.clarification_required;
              return (
                <article key={message.id} className={`message ${message.role}`}>
                  {message.role === "assistant" ? (
                    <>
                      {message.steps && (
                        <ThoughtProcessContainer
                          steps={message.steps}
                          isStreaming={message.isStreaming}
                          hasMessageText={Boolean(displayMessageText(message))}
                        />
                      )}
                      {hasContent && (
                        <div className="message-bubble">
                          {displayMessageText(message) && (
                            <div
                              className="assistant-prose"
                              dangerouslySetInnerHTML={{
                                __html: renderMarkdown(displayMessageText(message)),
                              }}
                            />
                          )}
                          {message.response?.data?.items?.length ? (
                            <RecommendationAnswerBox items={message.response.data.items} labels={t} onOrder={startOrder} onAskPrice={submitSuggestedMessage} />
                          ) : null}
                          {message.response?.data?.clarification_required && (
                            <div className="country-chips">
                              {markets.slice(0, 5).map((value) => <button key={value} type="button" onClick={() => submitMessage(value)}>{value}</button>)}
                            </div>
                          )}
                        </div>
                      )}
                    </>
                  ) : (
                    <div className="message-bubble">
                      <div style={{ whiteSpace: "pre-wrap", fontFamily: "inherit", fontSize: "14px", lineHeight: "1.6" }}>
                        {displayMessageText(message)}
                      </div>
                    </div>
                  )}
                </article>
              );
            })}
            {showOrderSuccessCenter && (
              <div className="order-created-center">
                <strong>{t.createdTitle}</strong>
                <p>{t.createdDesc}</p>
                <span>{t.orderTotal}: {createdOrderTotal || "N/A"}</span>
              </div>
            )}
            {loading && !isStreamingActive && <RecommendationSkeleton />}
          </div>

          {showBottomSuggestions && (
            <div className="suggestion-bar suggestion-bar-bottom" aria-label={t.suggestedQuestions}>
              <span>{t.suggestedQuestions}</span>
              <div className="chips">
                {displayedSuggestions.map((suggestion) => (
                  <button key={suggestion} type="button" className={pendingSuggestion === suggestion ? "preparing" : ""} onClick={() => submitSuggestedMessage(suggestion)} disabled={loading || Boolean(pendingSuggestion)}>{suggestion}</button>
                ))}
              </div>
            </div>
          )}

          <form className="chat-input" onSubmit={onSubmit}>
            <textarea
              value={input}
              onChange={(event) => setInput(event.target.value)}
              onKeyDown={(event) => {
                if (event.key === "Enter" && !event.shiftKey) {
                  event.preventDefault();
                  sendCurrentInput();
                }
              }}
              placeholder={t.placeholder}
            />
            <button type="submit" className="send-icon-button" disabled={loading || !apiOnline} aria-label={String(loading ? t.sending : t.send)} title={String(loading ? t.sending : t.send)}>
              <img src="/img/PaperPlaneTilt.svg" alt="" aria-hidden="true" />
              <span className="sr-only">{loading ? t.sending : t.send}</span>
            </button>
          </form>
        </section>

        <aside className="order-panel checkout-panel" aria-label="Create sandbox order draft">
          <div className="order-panel-header">
            <div>
              <span>{t.orderTitle}</span>
              <small>{orderStatus}</small>
            </div>
          </div>
          <div className="order-panel-tabs" role="tablist" aria-label="Sandbox order panel">
            <button type="button" className={orderPanelTab === "checkout" ? "active" : ""} onClick={() => setOrderPanelTab("checkout")}>{t.checkoutTab}</button>
            <button type="button" className={orderPanelTab === "orders" ? "active" : ""} onClick={() => setOrderPanelTab("orders")}>{t.ordersTab}</button>
          </div>
          {orderPanelTab === "orders" ? (
            <div className="orders-empty">
              <div className="placeholder-image">BP</div>
              <h2>{t.ordersTab}</h2>
              <p>{t.orderHistoryEmpty}</p>
            </div>
          ) : orderStatus === "created" ? (
            <div className="checkout-container">
              <section className="checkout-success-view">
                <strong>{t.createdTitle}</strong>
                <p>{t.createdDesc}</p>
                <span>{t.orderTotal}: {createdOrderTotal || "N/A"}</span>
              </section>
            </div>
          ) : !selectedItem ? (
            <div className="order-empty">
              <div className="placeholder-image">SKU</div>
              <h2>{t.selectProduct}</h2>
              <p>{t.selectProductDesc}</p>
            </div>
          ) : (
            <div className="checkout-container">
              <section className="checkout-section inspector-section">
                <div className="checkout-section-title">
                  <span>{t.productInspector}</span>
                  <small>{selectedItem.sku || "N/A"}</small>
                </div>
                <div className="checkout-product-card">
                  <div className="checkout-product-image">
                    {imageUrl(selectedItem) ? <img src={imageUrl(selectedItem)} alt={productName(selectedItem)} /> : <div className="placeholder-image">SKU</div>}
                  </div>
                  <div className="checkout-product-info">
                    <h2>{productName(selectedItem)}</h2>
                    <p>{selectedItem.partner_name || selectedItem.location_name || "N/A"}</p>
                    <div className="checkout-product-specs">
                      <ColorChip color={selectedItem.color} />
                      <span>{selectedItem.size || "N/A"}</span>
                      <span>{formatCarrier(selectedItem.carrier)}</span>
                    </div>
                  </div>
                </div>
                {(() => {
                  const partnerOptions = recommendedItems.filter(
                    (item) => (item.partner_name || "BurgerPrints") === (selectedItem?.partner_name || "BurgerPrints")
                  );
                  return partnerOptions.length > 1 && (
                    <div className="sku-option-select">
                      <span>{t.skuOption}</span>
                      <div className="sku-option-list">
                        {partnerOptions.map((item) => (
                          <button
                            key={item.sku}
                            type="button"
                            className={selectedItem?.sku === item.sku ? "sku-option active" : "sku-option"}
                            onClick={() => selectProductBySku(item.sku || "")}
                          >
                            <ColorChip color={item.color} />
                            <small>{item.size || "N/A"} - {item.partner_name || "N/A"}</small>
                            <strong>{formatLandedCost(item)}</strong>
                          </button>
                        ))}
                      </div>
                    </div>
                  );
                })()}
              </section>

              <form className="checkout-form" onSubmit={submitOrderFields}>
                <section className="checkout-section checkout-inputs">
                  <div className="checkout-section-title">
                    <span>{t.shippingInfo}</span>
                    <small>{orderForm.shipping_country || market}</small>
                  </div>
                  <label>{t.fullName}<input value={orderForm.shipping_name} onChange={(event) => setOrderForm({ ...orderForm, shipping_name: event.target.value })} /></label>
                  <label>{t.address}<input value={orderForm.shipping_address1} onChange={(event) => setOrderForm({ ...orderForm, shipping_address1: event.target.value })} /></label>
                  <div className="form-row">
                    <label>{t.city}<input value={orderForm.shipping_city} onChange={(event) => setOrderForm({ ...orderForm, shipping_city: event.target.value })} /></label>
                    <label>{t.state}<input value={orderForm.shipping_state} onChange={(event) => setOrderForm({ ...orderForm, shipping_state: event.target.value })} /></label>
                  </div>
                  <div className="form-row">
                    <label>{t.zip}<input value={orderForm.shipping_zip} onChange={(event) => setOrderForm({ ...orderForm, shipping_zip: event.target.value })} /></label>
                    <label>{t.country}<input value={orderForm.shipping_country} onChange={(event) => setOrderForm({ ...orderForm, shipping_country: event.target.value.toUpperCase() })} /></label>
                  </div>
                  <label>{t.referenceOrder}<input value={orderForm.reference_order_id} onChange={(event) => setOrderForm({ ...orderForm, reference_order_id: event.target.value })} /></label>
                </section>

                <section className="checkout-section front-design-section">
                  <div className="checkout-section-title">
                    <span>{t.frontDesign}</span>
                    <small>{t.backDesignPending}</small>
                  </div>
                  <div className="front-design-preview">
                    {imageUrl(selectedItem) ? <img className="front-base-image" src={imageUrl(selectedItem)} alt={productName(selectedItem)} /> : <div className="placeholder-image">URL_img</div>}
                    {frontDesignOverlayUrl() && <img className="front-overlay-image" src={frontDesignOverlayUrl()} alt={String(t.frontDesign)} />}
                  </div>
                  <label>{t.designUrl}<input value={orderForm.design_url_front} onChange={(event) => updateFrontDesignUrl(event.target.value)} placeholder="https://..." /></label>
                  <label className="local-image-picker">
                    <span>{t.chooseLocalImage}</span>
                    <input type="file" accept="image/*" onChange={(event) => chooseLocalFrontDesign(event.target.files?.[0] || null)} />
                  </label>
                  <p className="design-url-hint">{frontDesignPreviewUrl ? t.localImagePreview : t.designUrlHint}</p>
                </section>

                <section className="checkout-section print-options-section">
                  <div className="checkout-section-title">
                    <span>{language === "vi" ? "Tùy chọn in ấn" : "Print Options"}</span>
                  </div>
                  <div className="print-sides-options" style={{ display: "flex", gap: "16px", marginTop: "4px" }}>
                    <label style={{ display: "flex", alignItems: "center", gap: "6px", cursor: "pointer", fontWeight: "bold" }}>
                      <input
                        type="radio"
                        name="print_sides"
                        value="front"
                        checked={orderForm.print_sides === "front"}
                        onChange={() => setOrderForm({ ...orderForm, print_sides: "front" })}
                      />
                      <span>{language === "vi" ? "In 1 mặt (Front only)" : "Front side only"}</span>
                    </label>
                    <label style={{ display: "flex", alignItems: "center", gap: "6px", cursor: "pointer", fontWeight: "bold" }}>
                      <input
                        type="radio"
                        name="print_sides"
                        value="both"
                        checked={orderForm.print_sides === "both"}
                        onChange={() => setOrderForm({ ...orderForm, print_sides: "both" })}
                      />
                      <span>{language === "vi" ? "In 2 mặt (Front & Back)" : "Both sides (Front & Back)"}</span>
                    </label>
                  </div>
                </section>

                {orderNotice && (
                  <section className="checkout-section order-notice">
                    <strong>{t.orderPanelNotice}</strong>
                    <pre>{orderNotice}</pre>
                  </section>
                )}

                <section className="checkout-section billing-summary">
                  <div className="checkout-section-title">
                    <span>{t.billingSummary}</span>
                    <small>{t.orderTotal}: {formatFullOrderTotal(selectedItem, orderForm.print_sides)}</small>
                  </div>
                  <dl>
                    <div><dt>{t.base}</dt><dd>{formatMoney(selectedItem.base_cost)}</dd></div>
                    <div><dt>{t.printCost}</dt><dd>{formatPrintCost(selectedItem, orderForm.print_sides)}</dd></div>
                    <div><dt>{t.ship}</dt><dd>{formatMoney(selectedItem.shipping_fee)}</dd></div>
                    <div><dt>{t.orderTotal}</dt><dd>{formatFullOrderTotal(selectedItem, orderForm.print_sides)}</dd></div>
                    <div><dt>{t.grossMargin}</dt><dd>{formatPercent(selectedItem.margin_percent, t.marginMissing)}</dd></div>
                    <div><dt>{t.delivery}</dt><dd title={formatDelivery(selectedItem.delivery_time, t)}>{formatDelivery(selectedItem.delivery_time, t)}</dd></div>
                  </dl>
                </section>

                <div className="checkout-actions">
                  <div className="order-total-bar">
                    <span>{t.orderTotal}</span>
                    <strong>{formatFullOrderTotal(selectedItem, orderForm.print_sides)}</strong>
                  </div>
                  {orderStatus === "selected" && <button type="button" className="confirm-order-btn" onClick={() => startOrder(selectedItem)} disabled={loading}>{t.order}</button>}
                  {orderStatus !== "selected" && !orderReadyToConfirm && <button type="submit" className="confirm-order-btn" disabled={loading}>{t.createDraft}</button>}
                  {orderReadyToConfirm && <button type="button" className="confirm-order-btn" onClick={() => confirmSandboxOrder(selectedItem)} disabled={loading}>{t.confirmCreate}</button>}
                </div>
              </form>
            </div>
          )}
        </aside>
      </div>

      {pendingMarket && (
        <div className="dialog-backdrop" role="presentation">
          <div className="dialog" role="dialog" aria-modal="true" aria-labelledby="market-dialog-title">
            <h2 id="market-dialog-title">Thay đổi thị trường?</h2>
            <p>Thay đổi thị trường sẽ làm mới bản nháp đơn hàng hiện tại. Bạn có muốn tiếp tục?</p>
            <div className="dialog-actions">
              <button type="button" className="secondary-action" onClick={() => setPendingMarket(null)}>Giữ bản nháp</button>
              <button type="button" onClick={() => applyMarketChange(pendingMarket)}>Tiếp tục đổi market</button>
            </div>
          </div>
        </div>
      )}
    </main>
  );
}

function ColorChip({ color }: { color?: string }) {
  const label = color || "N/A";
  return (
    <span className="color-chip">
      <i style={{ background: colorHex(color) }} />
      <span>{label}</span>
    </span>
  );
}

function RecommendationAnswerBox({ items, labels, onOrder, onAskPrice }: { items: RecommendedItem[]; labels: CopyText; onOrder: (item: RecommendedItem) => void; onAskPrice: (message: string) => void }) {
  const best = items[0];
  const topItems = items;
  const missingPrompts = missingRecommendationPrompts(best, labels);

  return (
    <div className="result-box">
      <div className="result-box-header">
        <div>
          <span>{labels.catalogRecommendation}</span>
          <h3>{productName(best)}</h3>
        </div>
        <div className="result-box-metrics">
          <strong>{formatLandedCost(best)}</strong>
          <span>{labels.grossMargin}: {formatPercent(best.margin_percent, labels.marginMissing)}</span>
        </div>
      </div>
      <div className="best-pick-card">
        {imageUrl(best) ? <img src={imageUrl(best)} alt={productName(best)} /> : <div className="placeholder-image">SKU</div>}
        <div>
          <small>{labels.bestPick}</small>
          <p>{best.sku || "N/A"}</p>
          <div className="best-pick-meta">
            <div className="meta-field"><b>{labels.color}</b><ColorChip color={best.color} /></div>
            <div className="meta-field"><b>{labels.size}</b><span>{best.size || "N/A"}</span></div>
            <div className="meta-field"><b>{labels.supplier}</b><span>{best.partner_name || best.location_name || "N/A"}</span></div>
            <div className="meta-field"><b>{labels.base}</b><span>{formatMoney(best.base_cost)}</span></div>
            <div className="meta-field"><b>{labels.printCost}</b><span>{formatPrintCost(best)}</span></div>
            <div className="meta-field"><b>{labels.ship}</b><span>{formatMoney(best.shipping_fee)}</span></div>
            <div className="meta-field"><b>{labels.sellPrice}</b><span>{formatSellingPrice(best, labels)}</span></div>
          </div>
          <div className="best-pick-actions">
            <strong>{labels.grossMargin}: {formatPercent(best.margin_percent, labels.marginMissing)}</strong>
            <button type="button" className="order-cta" onClick={() => onOrder(best)}>{labels.order}<span aria-hidden="true" className="order-cta-icon">▣</span></button>
          </div>
        </div>
      </div>
      {missingPrompts.length > 0 && (
        <div className="missing-info-callout">
          <div>
            <strong>{labels.missingInfoTitle}</strong>
            <span>{labels.missingInfoDesc}</span>
          </div>
          <div className="missing-info-actions">
            {missingPrompts.map((prompt) => (
              <button key={prompt.message} type="button" onClick={() => onAskPrice(prompt.message)}>{prompt.label}</button>
            ))}
          </div>
        </div>
      )}
      <div className="mini-comparison" role="table" aria-label="Top recommended SKUs">
        <div className="mini-row mini-row-header" role="row">
          <span>{labels.color}</span>
          <span>{labels.size}</span>
          <span>{labels.supplier}</span>
          <span>{labels.base}</span>
          <span>{labels.printCost}</span>
          <span>{labels.ship}</span>
          <span>{labels.sellPrice}</span>
          <span>{labels.total}</span>
          <span>{labels.grossMargin}</span>
          <span>{labels.delivery}</span>
          <span>{labels.order}</span>
        </div>
        {topItems.map((item) => (
          <div key={item.sku} className="mini-row" role="row">
            <ColorChip color={item.color} />
            <span>{item.size || "N/A"}</span>
            <span>{item.partner_name || item.location_name || "N/A"}</span>
            <span>{formatMoney(item.base_cost)}</span>
            <span>{formatMoney(printCostValue(item))}</span>
            <span>{formatMoney(item.shipping_fee)}</span>
            <span>{formatSellingPrice(item, labels)}</span>
            <span>{formatLandedCost(item)}</span>
            <span>{formatPercent(item.margin_percent, labels.marginMissing)}</span>
            <span title={formatDelivery(item.delivery_time, labels)}>{formatDelivery(item.delivery_time, labels)}</span>
            <button type="button" className="order-cta mini" onClick={() => onOrder(item)}>{labels.order}<span aria-hidden="true" className="order-cta-icon">▣</span></button>
          </div>
        ))}
      </div>
      <p>{labels.viewCards}</p>
    </div>
  );
}

function ProductCard({
  item,
  rank,
  selected,
  labels,
  onSelect,
}: {
  item: RecommendedItem;
  rank: number;
  selected: boolean;
  labels: CopyText;
  onSelect: () => void;
}) {
  return (
    <article className={selected ? "product-card selected" : "product-card"} onClick={onSelect}>
      {imageUrl(item) ? <img src={imageUrl(item)} alt={productName(item)} /> : <div className="placeholder-image">SKU</div>}
      <div className="product-card-body">
        <div className="product-title-row">
          <h3>{productName(item)}</h3>
          <span>{item.sku}</span>
        </div>
        <div className="product-meta">
          <span>{rank === 1 ? labels.bestPick : `#${rank}`}</span>
          <ColorChip color={item.color} />
          <span>{item.size || "N/A"}</span>
          <span>{item.partner_name || item.location_name || "N/A"}</span>
        </div>
        <div className="commerce-grid">
          <div><small>{labels.base}</small><strong>{formatMoney(item.base_cost)}</strong></div>
          <div><small>{labels.printCost}</small><strong>{formatPrintCost(item)}</strong></div>
          <div><small>{labels.ship}</small><strong>{formatMoney(item.shipping_fee)}</strong></div>
          <div><small>{labels.total}</small><strong>{formatLandedCost(item)}</strong></div>
          <div><small>{labels.grossMargin}</small><strong>{formatPercent(item.margin_percent, labels.marginMissing)}</strong></div>
        </div>
        <div className="delivery-line">
          <span title={formatDelivery(item.delivery_time, labels)}>{formatDelivery(item.delivery_time, labels)}</span>
          <span>{formatCarrier(item.carrier)}</span>
          <span>SLA {item.sla || "N/A"}</span>
        </div>
      </div>
    </article>
  );
}

function RecommendationSkeleton() {
  return (
    <div className="recommendation-skeleton" aria-label="Loading recommendation">
      <div className="skeleton-image" />
      <div className="skeleton-lines">
        <span />
        <span />
        <div className="skeleton-row"><i /><i /><i /></div>
      </div>
    </div>
  );
}
