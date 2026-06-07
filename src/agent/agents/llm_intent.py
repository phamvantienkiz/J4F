import json

import requests

from src.core.config import settings


ALLOWED_INTENTS = {
    "get_balance",
    "get_order",
    "get_sku",
    "get_product",
    "search_order_items",
    "list_orders",
    "unknown",
}

ALLOWED_PARAM_KEYS = {
    "country",
    "platform",
    "selling_price",
    "max_base_cost",
    "max_shipping_fee",
    "max_delivery_days",
    "min_margin",
    "quantity",
    "color",
    "size",
    "sort_by",
    "limit",
    "sku",
    "short_code",
    "order_id",
}

SYSTEM_PROMPT = """You classify seller text into one safe BurgerPrints intent.
Return strict JSON only, with this shape:
{"name":"search_order_items","country":"US","color":"Black"}

Allowed intent names:
get_balance, get_order, get_sku, get_product, search_order_items, list_orders, unknown.

Allowed parameter keys:
country, platform, selling_price, max_base_cost, max_shipping_fee, max_delivery_days,
min_margin, quantity, color, size, sort_by, limit, sku, short_code, order_id.

Never return create_order or any action intent. If the user asks to create/place/confirm an order,
return {"name":"unknown"}; order creation is handled by a separate confirmation flow.
Do not include explanations or markdown."""


class LlmIntentClassifier:
    def __init__(self, client=None):
        self.client = client

    def classify(self, message):
        try:
            payload = self._classify(message)
        except Exception:
            return None
        return validate_intent(payload)

    def _classify(self, message):
        if self.client:
            return self._classify_with_openai_client(message, self.client)
        if settings.llm_provider == "openai":
            return self._classify_with_openai_client(message, self._default_client())
        return self._classify_with_anthropic_endpoint(message)

    def _classify_with_openai_client(self, message, client):
        response = client.chat.completions.create(
            model=settings.llm_model,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": message},
            ],
            max_tokens=256,
        )
        content = response.choices[0].message.content
        return json.loads(content)

    def _classify_with_anthropic_endpoint(self, message):
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
                "messages": [{"role": "user", "content": message}],
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


def validate_intent(payload):
    if not isinstance(payload, dict):
        return None
    name = payload.get("name")
    if name not in ALLOWED_INTENTS:
        return None

    result = {"name": name}
    for key, value in payload.items():
        if key == "name":
            continue
        if key not in ALLOWED_PARAM_KEYS:
            return None
        result[key] = value
    return result
