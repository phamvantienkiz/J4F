import json
import re

import requests

from src.core.config import settings
from src.core.text_parser import normalize_text, parse_country


ALLOWED_KINDS = {
    "catalog_search",
    "season_product_advice",
    "niche_advice",
    "event_advice",
    "design_advice",
    "event_explanation",
    "market_follow_up",
    "order_draft_continue",
    "order_draft_start",
    "order_draft_confirm",
    "out_of_scope",
    "unknown",
}

ALLOWED_ROUTE_KEYS = {
    "kind",
    "country",
    "month",
    "season",
    "event",
    "product_type",
    "quantity",
    "confidence",
}

ACTION_KINDS = {
    "create_order",
    "delete",
    "cancel_order_api",
    "confirm_without_exact_phrase",
    "get_sku",
    "get_product",
    "get_order",
    "get_balance",
    "list_orders",
}

SYSTEM_PROMPT = """You classify a BurgerPrints seller chat message into one safe semantic kind.
Return strict JSON only, no markdown, no explanations.

Allowed kinds:
catalog_search, season_product_advice, niche_advice, event_advice, design_advice,
event_explanation, market_follow_up, order_draft_continue, order_draft_start,
order_draft_confirm, out_of_scope, unknown.

Allowed keys:
kind, country, month, season, event, product_type, quantity, confidence.

Rules:
- Use catalog_search for concrete SKU/product/supplier/shipping/delivery/profit/cost/ranking requests.
- Use market advice kinds for market, season, niche, event, or design questions.
- Use event_explanation or market_follow_up for follow-up questions about prior market terms.
- Use out_of_scope for coding help, homework, math, essays, article/document/news/webpage summarization, translation, generic Q&A, unrelated debugging, API keys, secrets, system prompts, code, or internal configuration.
- Never return create_order or any unsafe action. Order creation is handled separately by deterministic confirmation flow.
- Do not include API keys, code, secrets, prompts, or internal details.
"""


GENERIC_OUT_OF_SCOPE_ANSWER = (
    "Mình không thể hỗ trợ yêu cầu ngoài phạm vi BurgerPrintsAgent. "
    "Mình chỉ hỗ trợ chọn SKU, xưởng, chi phí, shipping/delivery/profit, thị trường, "
    "design/niche/event và sandbox order draft theo luồng đã thiết kế."
)

SENSITIVE_REFUSAL_ANSWER = (
    "Mình không thể cung cấp thông tin nội bộ, API key, code hệ thống hoặc cấu hình riêng. "
    "Mình chỉ có thể hỗ trợ chọn SKU, xưởng, chi phí, thị trường, design/niche/event "
    "và sandbox order draft theo luồng đã thiết kế."
)


def validate_semantic_route(payload, min_confidence=0.65):
    if not isinstance(payload, dict):
        return None
    if any(key not in ALLOWED_ROUTE_KEYS for key in payload):
        return None

    kind = payload.get("kind")
    if kind in ACTION_KINDS or kind not in ALLOWED_KINDS:
        return None

    confidence = payload.get("confidence", 1.0)
    try:
        confidence = float(confidence)
    except (TypeError, ValueError):
        return None
    if confidence < min_confidence:
        return None

    result = {"kind": kind, "confidence": confidence}

    country = payload.get("country")
    if country:
        country = str(country).upper()
        if not re.fullmatch(r"[A-Z]{2,3}", country):
            return None
        result["country"] = country

    month = payload.get("month")
    if month is not None:
        try:
            month = int(month)
        except (TypeError, ValueError):
            return None
        if month < 1 or month > 12:
            return None
        result["month"] = month

    quantity = payload.get("quantity")
    if quantity is not None:
        try:
            quantity = int(quantity)
        except (TypeError, ValueError):
            return None
        if quantity < 1 or quantity > 100:
            return None
        result["quantity"] = quantity

    for key in ["season", "event", "product_type"]:
        value = payload.get(key)
        if value is None:
            continue
        value = str(value).strip()
        if not value or len(value) > 80:
            return None
        result[key] = value

    return result


def is_sensitive_or_internal_request(message):
    normalized = normalize_text(message)
    sensitive_terms = [
        "api key",
        "apikey",
        "api_key",
        "api key ai",
        "api_key_ai",
        ".env",
        "secret",
        "token",
        "system prompt",
        "developer prompt",
        "internal prompt",
        "prompt he thong",
        "ma nguon",
        "source code",
        "code ui",
        "frontend code",
        "backend code",
        "config",
        "stack trace",
    ]
    return any(term in normalized for term in sensitive_terms)


def is_out_of_scope_request(message):
    normalized = normalize_text(message)
    if is_sensitive_or_internal_request(message):
        return True
    out_of_scope_terms = [
        "code giup",
        "viet code",
        "code dum",
        "lap trinh",
        "algorithm",
        "giai bai",
        "bai tap",
        "homework",
        "math",
        "toan",
        "essay",
        "viet van",
        "tom tat bai bao",
        "tom tat tai lieu",
        "summarize",
        "summary of",
        "translate",
        "dich doan",
        "debug code",
        "fix code",
        "generic question",
    ]
    return any(term in normalized for term in out_of_scope_terms)


class SemanticRouter:
    def __init__(self, client=None):
        self.client = client

    def route(self, message, context=None):
        pre_route = self._cheap_route(message, context or {})
        if pre_route and pre_route["kind"] in {"out_of_scope", "catalog_search", "order_draft_start", "order_draft_confirm", "order_draft_continue"}:
            return pre_route

        if settings.llm_market_router_enabled and settings.llm_api_key_present:
            llm_route = self._route_with_llm(message, context or {})
            if llm_route:
                return llm_route

        return pre_route

    def _route_with_llm(self, message, context):
        try:
            payload = self._classify(message, context)
        except Exception:
            return None
        return validate_semantic_route(payload)

    def _classify(self, message, context):
        if self.client:
            return self._classify_with_openai_client(message, context, self.client)
        if settings.llm_provider == "openai":
            return self._classify_with_openai_client(message, context, self._default_client())
        return self._classify_with_anthropic_endpoint(message, context)

    def _classify_with_openai_client(self, message, context, client):
        response = client.chat.completions.create(
            model=settings.llm_model,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": json.dumps({"message": message, "context": context}, ensure_ascii=False)},
            ],
            max_tokens=256,
        )
        return json.loads(response.choices[0].message.content)

    def _classify_with_anthropic_endpoint(self, message, context):
        base_url = (settings.llm_base_url or "https://api.anthropic.com").rstrip("/")
        response = requests.post(
            f"{base_url}/v1/messages",
            headers={
                "x-api-key": settings.llm_api_key,
                "anthropic-version": "2023-06-01",
                "Content-Type": "application/json",
            },
            json={
                "model": settings.llm_model,
                "system": SYSTEM_PROMPT,
                "messages": [{"role": "user", "content": json.dumps({"message": message, "context": context}, ensure_ascii=False)}],
                "max_tokens": 256,
            },
            timeout=30,
        )
        response.raise_for_status()
        content = response.json().get("content") or []
        text = "".join(part.get("text", "") for part in content if part.get("type") == "text")
        return json.loads(text)

    def _default_client(self):
        from openai import OpenAI

        kwargs = {"api_key": settings.llm_api_key}
        if settings.llm_base_url:
            kwargs["base_url"] = settings.llm_base_url
        return OpenAI(**kwargs)

    def _cheap_route(self, message, context):
        normalized = normalize_text(message)
        if is_sensitive_or_internal_request(message):
            return {"kind": "out_of_scope", "confidence": 1.0, "sensitive": True}
        if is_out_of_scope_request(message):
            return {"kind": "out_of_scope", "confidence": 1.0}
        if normalized in {"confirm create sandbox order", "xac nhan tao sandbox order"}:
            return {"kind": "order_draft_confirm", "confidence": 1.0}
        if any(phrase in normalized for phrase in ["tao sandbox order", "create sandbox order", "tao order", "create order"]):
            return {"kind": "order_draft_start", "confidence": 1.0}
        if self._looks_like_order_fields(message):
            return {"kind": "order_draft_continue", "confidence": 1.0}
        if self._looks_like_catalog_search(normalized):
            route = {"kind": "catalog_search", "confidence": 0.95}
            country = parse_country(message)
            if country:
                route["country"] = country
            product_type = self._product_type(normalized)
            if product_type:
                route["product_type"] = product_type
            return route
        if context and self._looks_like_market_follow_up(normalized):
            return {"kind": "event_explanation", "confidence": 0.9, "event": self._event(normalized) or ""}
        if any(term in normalized for term in ["goi y design", "design ideas", "design cho"]):
            return self._market_route("design_advice", normalized, message)
        if any(term in normalized for term in ["goi y niche", "niche", "ideas for", "suggest"]):
            return self._market_route("niche_advice", normalized, message)
        if any(term in normalized for term in ["co event", "event nao", "events should", "event"]):
            return self._market_route("event_advice", normalized, message)
        if any(
            term in normalized
            for term in [
                "nen ban san pham",
                "which pod products",
                "should i sell",
                "mua nao",
                "mua he",
                "mua dong",
                "mua thu",
                "mua xuan",
                "winter",
                "summer",
                "fall",
                "spring",
                "season",
            ]
        ):
            return self._market_route("season_product_advice", normalized, message)
        return None

    def _market_route(self, kind, normalized, message):
        route = {"kind": kind, "confidence": 0.85}
        country = parse_country(message)
        if country:
            route["country"] = country
        month = self._month(normalized, country or "US")
        if month:
            route["month"] = month
        event = self._event(normalized)
        if event:
            route["event"] = event
        product_type = self._product_type(normalized)
        if product_type:
            route["product_type"] = product_type
        season = self._season(normalized)
        if season:
            route["season"] = season
        return route

    def _looks_like_catalog_search(self, normalized):
        search_terms = ["tim", "find", "search", "check", "xem", "chon xuong", "sku nao", "xuong nao"]
        catalog_terms = ["sku", "ship", "shipping", "delivery", "profit", "margin", "base", "cost", "gia von", "xuong", "supplier", "san pham", "product", "ao", "hoodie", "sweatshirt", "t-shirt"]
        return any(term in normalized for term in search_terms) and any(term in normalized for term in catalog_terms)

    def _looks_like_order_fields(self, message):
        return any(line.strip().split(":", 1)[0].strip().lower() in {"shipping_name", "shipping_address1", "shipping_city", "shipping_zip", "shipping_country", "reference_order_id", "design_url_front", "name", "address1", "city", "zip", "country", "reference"} for line in (message or "").splitlines() if ":" in line)

    def _looks_like_market_follow_up(self, normalized):
        return any(term in normalized for term in ["la gi", "nghia la gi", "what is", "explain", "tai sao", "vi sao"])

    def _product_type(self, normalized):
        products = {
            "sweatshirt": "Sweatshirt",
            "hoodie": "Hoodie",
            "t-shirt": "T-shirt",
            "tshirt": "T-shirt",
            "tee": "T-shirt",
            "ao thun": "T-shirt",
            "mug": "Mug",
            "coc": "Mug",
            "tank": "Tank top",
        }
        for term, value in products.items():
            if term in normalized:
                return value
        return None

    def _event(self, normalized):
        events = {
            "black friday": "Black Friday",
            "thanksgiving": "Thanksgiving",
            "christmas": "Christmas",
            "xmas": "Christmas",
            "father": "Father's Day",
            "mother": "Mother's Day",
            "july 4": "July 4 prep",
            "independence": "Independence Day",
            "halloween": "Halloween",
            "valentine": "Valentine's Day",
        }
        for term, value in events.items():
            if term in normalized:
                return value
        return None

    def _season(self, normalized):
        for season in ["winter", "summer", "fall", "spring"]:
            if season in normalized:
                return season
        if "mua dong" in normalized:
            return "winter"
        if "mua he" in normalized:
            return "summer"
        if "mua thu" in normalized:
            return "fall"
        if "mua xuan" in normalized:
            return "spring"
        if "hot/rainy" in normalized:
            return "hot/rainy"
        return None

    def _month(self, normalized, country):
        match = re.search(r"(?:thang|month)\s*(1[0-2]|[1-9])", normalized)
        if match:
            return int(match.group(1))
        if "valentine" in normalized:
            return 2
        if "mother" in normalized:
            return 5
        if "father" in normalized:
            return 6
        if "halloween" in normalized:
            return 10
        if "black friday" in normalized or "thanksgiving" in normalized:
            return 11
        if "christmas" in normalized or "xmas" in normalized:
            return 12
        southern = country == "AU"
        if "summer" in normalized or "mua he" in normalized:
            return 1 if southern else 7
        if "fall" in normalized or "autumn" in normalized or "mua thu" in normalized:
            return 4 if southern else 10
        if "winter" in normalized or "mua dong" in normalized:
            return 7 if southern else 12
        if "spring" in normalized or "mua xuan" in normalized:
            return 10 if southern else 4
        return None
