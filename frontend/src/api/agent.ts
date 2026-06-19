const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || "http://127.0.0.1:8000";

export type SuggestedQuestions = {
  country: string;
  month: number;
  season: string;
  weather_context: string;
  events: string[];
  product_types: string[];
  suggestions: string[];
};

export type RecommendedItem = {
  sku?: string;
  product_name?: string;
  display_name?: string;
  color?: string;
  size?: string;
  partner_name?: string;
  location_name?: string;
  base_cost?: number;
  second_item_price?: number;
  addition_price?: number;
  clone_price?: number;
  shipping_fee?: number;
  tax_fee?: number;
  tax_rate?: number;
  tax_rate_pct?: string;
  tax_region?: string;
  tax_sub_region?: string;
  tax_type?: string;
  tax_amount?: number;
  seller_tax?: number;
  buyer_tax?: number;
  net_revenue?: number;
  tax_data_source?: string;
  tax_note?: string;
  tax_is_estimated?: boolean;
  amount?: number;
  sub_amount?: number;
  payment_processing_fee?: number;
  total_cost?: number;
  landed_cost?: number;
  selling_price?: number;
  quantity?: number;
  delivery_time?: string;
  carrier?: string[] | string;
  sla?: string | number | null;
  mockup_url?: string;
  image_url?: string;
  profit?: number;
  margin_percent?: number;
  print_sides?: "front" | "both" | "back";
  filter_excess?: Record<string, unknown>;
};

export type AgentResponse = {
  answer: string;
  intent?: string;
  tool_calls?: Array<{ name: string; params?: Record<string, unknown> }>;
  api?: { method?: string; path?: string } | null;
  params?: Record<string, unknown>;
  data?: {
    source?: string;
    match_type?: string;
    clarification_required?: boolean;
    missing_field?: string;
    question?: string;
    items?: RecommendedItem[];
    status?: string;
    sandbox?: boolean;
    id?: string;
  };
  notes?: string[];
  session_id: string;
  confirmation_required?: boolean;
};

export async function checkHealth() {
  const response = await fetch(`${API_BASE_URL}/health`);
  if (!response.ok) throw new Error("API health check failed");
  return response.json() as Promise<{ status: string }>;
}

export async function checkReady() {
  const response = await fetch(`${API_BASE_URL}/ready`);
  if (!response.ok) throw new Error("API readiness check failed");
  return response.json() as Promise<{ ready: boolean; warming: boolean; warmup_ms?: number | null; error?: string | null }>;
}

export async function getSuggestions(country: string, month: number) {
  const params = new URLSearchParams({ country, month: String(month) });
  const response = await fetch(`${API_BASE_URL}/agent/suggestions?${params}`);
  if (!response.ok) throw new Error("Could not load suggestions");
  return response.json() as Promise<SuggestedQuestions>;
}

export async function sendChatMessage(
  input: { sessionId?: string | null; message: string; history?: unknown[] },
  onChunk?: (chunk: any) => void
): Promise<AgentResponse> {
  const response = await fetch(`${API_BASE_URL}/agent/chat`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      session_id: input.sessionId || undefined,
      message: input.message,
      history: input.history || [],
    }),
  });
  if (!response.ok) throw new Error(await response.text());
  if (!response.body) throw new Error("Response body is null");

  const reader = response.body.getReader();
  const decoder = new TextDecoder("utf-8");
  let buffer = "";
  let finalPayload: AgentResponse | null = null;

  try {
    while (true) {
      const { value, done } = await reader.read();
      if (done) break;

      buffer += decoder.decode(value, { stream: true });
      const parts = buffer.split("\n\n");
      buffer = parts.pop() || "";

      for (const part of parts) {
        const line = part.trim();
        if (!line) continue;

        if (line.startsWith("data: ")) {
          try {
            const data = JSON.parse(line.slice(6));
            if (onChunk) {
              onChunk(data);
            }
            if (data && typeof data.session_id === "string") {
              finalPayload = data as AgentResponse;
            }
          } catch (e) {
            console.error("Error parsing stream chunk:", e);
          }
        }
      }
    }
  } finally {
    reader.releaseLock();
  }

  if (!finalPayload) {
    throw new Error("Stream closed without receiving final payload");
  }

  return finalPayload;
}
